import datetime
from collections.abc import Callable, Collection, Hashable, Mapping, Sequence
from enum import Enum
from numbers import Number
from operator import attrgetter, itemgetter
from typing import Any, NamedTuple, TypeGuard, cast

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from enamlext.qt.qt_dataframe import DataFrameProxy
from enamlext.qt.table.defs import CellStyle, ColumnSize
from enamlext.qt.table.table_context import TableContext


class Alignment(str, Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'


class _AutoAlign(Enum):
    # A one-member enum is the typed way to spell a sentinel: `align is AUTO_ALIGN` narrows for type checkers.
    AUTO_ALIGN = 'auto'


AUTO_ALIGN = _AutoAlign.AUTO_ALIGN


class Column:
    def __init__(
        self,
        key: str | Callable,
        title: str | None = None,
        align: Alignment | _AutoAlign = AUTO_ALIGN,
        tooltip: str | Callable | None = None,
        # TODO: how to specify the types for the signature of the callback here?
        cell_style: Callable | None = None,
        use_getitem: bool = False,
        fmt: str = '',
        size: ColumnSize | int = ColumnSize.AUTO,
        image: str | None = None,  # TODO: support callback
        collect_stats: bool = False,
        header_tooltip: str | None = None,
    ):
        self.key = key
        self._link_get_value_method(key, use_getitem)
        if title is None and isinstance(key, str):
            title = key.title()
        self.title = title
        self.align = align
        self.tooltip = tooltip
        self.header_tooltip = header_tooltip
        self.cell_style = cell_style
        self.fmt = fmt
        self.size = size  # TODO: should we also support callable?
        self.image = image
        if cell_style is not None:
            self.get_cell_style = cell_style  # type: ignore[method-assign]  # skip the wrapper per cell
        self.collect_stats = collect_stats
        self.stats: dict[int, dict[str, float]] = {}
        self.df_index: int | None = None  # set by generate_columns() for DataFrame columns
        # Cached AUTO_ALIGN resolution: filled in on the first non-None value
        # encountered, then reused for the column's lifetime so we stop running
        # an isinstance chain per cell per repaint.
        self._resolved_auto_align: Alignment | None = None

    def record_stats(self, role: int, elapsed: float):
        if role not in self.stats:
            self.stats[role] = {'n_calls': 0, 'cum_time': 0, 'avg_time': 0}

        stats_for_role = self.stats[role]
        stats_for_role['n_calls'] += 1
        stats_for_role['cum_time'] += elapsed
        stats_for_role['avg_time'] = stats_for_role['cum_time'] / stats_for_role['n_calls']

    def total_cost(self) -> float:
        return sum(stats['cum_time'] for stats in self.stats.values())

    def _link_get_value_method(self, key: str | Callable, use_getitem: bool) -> None:
        # Bind the right lookup once per column so the per-cell hot path never branches on the key type.
        # The C-level getters do the same lookup as the methods, so use them unless a subclass overrides the method;
        # attrgetter would follow a dotted key into nested attributes, which getattr does not.
        cls = type(self)
        if callable(key):
            self.get_value = key  # type: ignore[method-assign]
        elif use_getitem:
            if cls.get_value_by_getitem_lookup is Column.get_value_by_getitem_lookup:
                self.get_value = itemgetter(key)  # type: ignore[method-assign, assignment]
            else:
                self.get_value = self.get_value_by_getitem_lookup  # type: ignore[method-assign]
        elif cls.get_value_by_attribute_lookup is Column.get_value_by_attribute_lookup and '.' not in key:
            self.get_value = attrgetter(key)  # type: ignore[method-assign, assignment]
        else:
            self.get_value = self.get_value_by_attribute_lookup  # type: ignore[method-assign]

    def get_value(self, item: Any) -> Any:
        raise RuntimeError('get_value() not dynamic linked during initialization')

    def get_value_by_attribute_lookup(self, item: Any) -> Any:
        return getattr(item, cast('str', self.key))

    def get_value_by_getitem_lookup(self, item: Any) -> Any:
        return item[self.key]
        # TODO: dataframe will always need to be by index (not by name)

    def get_displayed_value(self, item: Any) -> str:
        value = self.get_value(item)
        if callable(self.fmt):
            return self.fmt(value)
        return format(value, self.fmt) if value is not None else ''

    def get_tooltip(self, table_context: 'TableContext') -> str:
        if self.tooltip is not None:
            if callable(self.tooltip):
                return str(self.tooltip(table_context))  # TODO: is it a good practice to enforce str() here?
            return self.tooltip  # str
        return repr(table_context.raw_value)

    def get_cell_style(self, table_context: 'TableContext') -> CellStyle | None:
        if self.cell_style is not None:
            return self.cell_style(table_context) or CellStyle()
        return None

    def get_align(self, item: Any) -> Alignment:
        if self.align is not AUTO_ALIGN:
            return self.align
        if (cached := self._resolved_auto_align) is not None:
            return cached
        value = self.get_value(item)
        if value is None:
            # Don't cache off a None — wait for the first row that has a real
            # type so we can resolve the column's alignment correctly.
            return Alignment.LEFT
        align = self.resolve_column_alignment_based_on_value(value)
        self._resolved_auto_align = align
        return align

    def get_align_quick(self) -> Alignment | None:
        """Return the column's alignment without needing an item, or None when
        the column is AUTO_ALIGN and hasn't been resolved yet. Lets callers
        skip fetching/converting the row item on every TextAlignmentRole call.
        """
        if self.align is not AUTO_ALIGN:
            return self.align
        return self._resolved_auto_align

    def resolve_column_alignment_based_on_value(self, value: Any) -> Alignment:
        if isinstance(value, Number):
            return Alignment.RIGHT
        if isinstance(value, (datetime.datetime, datetime.date)):
            return Alignment.CENTER
        if isinstance(value, str):
            return Alignment.LEFT
        return Alignment.LEFT

    def get_image(self, table_context: 'TableContext') -> str | None:  # TODO: should return Path?
        if self.image:
            return str(self.image)
        return None


# Auto-Generation of Columns


def make_title(title: object) -> str:
    return str(title).replace('_', ' ').title()


def is_namedtuple(obj: object) -> TypeGuard[NamedTuple]:
    return isinstance(obj, tuple) and hasattr(type(obj), '_fields') and hasattr(type(obj), '_asdict')


RED = QColor(Qt.GlobalColor.red)
NEGATIVE_NUMBER_CELL_STYLE = CellStyle(color=RED)


def get_cell_style_for_negative_numbers(table_context: TableContext) -> CellStyle | None:
    try:
        is_negative = bool(table_context.raw_value < 0)
    except TypeError:  # missing values: None can't be ordered and pd.NA has no truth value
        return None
    return NEGATIVE_NUMBER_CELL_STYLE if is_negative else None


def generate_columns(
    items: Sequence,
    *,
    hints: dict | None = None,
    include: Sequence[Hashable] | None = None,
    exclude: Collection[Hashable] | None = None,
) -> list[Column]:
    """
    hints: only make sense with named keys?
           hints are a dict of column id -> kwargs dict that will
           get passed to the Column object

    Args:
        include: list of column keys/ids that will be included. The order
            of the generated columns will be respected according to the
            include values. Use this to ensure the order of the columns.

        exclude: list of column keys/ids to be excluded. The order
            of the generated columns will be according to the order of
            appearance in the first item.

    Note: you cannot use include and exclude at the same time. An attempt
        to do so will result in raising a ValueError exception.
    """
    if hints is None:
        hints = {}
    if include and exclude:
        raise ValueError('Cannot use include and exclude simultaneously.')
    exclude_set: set[Hashable] = set(exclude) if exclude is not None else set()
    include_set: set[Hashable] = set(include) if include is not None else set()
    if not len(items):
        return []
    first_row = items[0]
    columns: dict[int, Column] = {}  # column_index -> Column
    kwargs: dict[str, Any]

    if isinstance(items, DataFrameProxy):
        import pandas as pd

        df = items.df
        for i, (name, dtype) in enumerate(df.dtypes.items()):
            if exclude is not None and name in exclude_set:
                continue
            if include is not None and name not in include_set:
                continue
            # pd.api.types.is_numeric_dtype handles pandas extension dtypes (StringDtype,
            # CategoricalDtype, Int64Dtype, ...) that np.issubdtype cannot interpret as
            # data types and would raise TypeError on.
            if pd.api.types.is_numeric_dtype(dtype):
                align = Alignment.RIGHT
                style = get_cell_style_for_negative_numbers
            else:
                align = Alignment.LEFT
                style = None

            kwargs = {'title': make_title(name), 'align': align, 'cell_style': style, 'use_getitem': True}

            hint = hints.get(name, {})
            kwargs.update(hint)

            column = Column(itemgetter(i), **kwargs)

            column_index = include.index(name) if include is not None else i

            column.df_index = i

            columns[column_index] = column

    elif isinstance(first_row, tuple):
        fields = first_row._fields if is_namedtuple(first_row) else None
        for i, value in enumerate(first_row):
            field_name = fields[i] if fields is not None else object()
            if exclude is not None and ({i, field_name} & exclude_set):
                continue
            if include is not None and not ({i, field_name} & include_set):
                continue
            title = make_title(fields[i]) if fields is not None else str(i)
            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            else:
                kwargs['align'] = Alignment.LEFT
            hint = hints.get(i, {})
            kwargs.update(hint)
            column = Column(itemgetter(i), **kwargs)
            if include is not None:
                # The include_set check above guarantees one of these is in `include`.
                column_index = next(include.index(v) for v in (i, field_name) if v in include_set)
            else:
                column_index = i
            columns[column_index] = column

    elif isinstance(first_row, Mapping):
        for i, (key, value) in enumerate(first_row.items()):
            if exclude is not None and key in exclude_set:
                continue
            if include is not None and key not in include_set:
                continue
            title = make_title(key) if isinstance(key, str) else str(key)

            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            else:
                kwargs['align'] = Alignment.LEFT

            hint = hints.get(key, {})
            kwargs.update(hint)
            column = Column(itemgetter(key), **kwargs)

            column_index = include.index(key) if include is not None else i
            columns[column_index] = column

    elif hasattr(type(first_row), '__dataclass_fields__'):
        fields = type(first_row).__dataclass_fields__
        for i, field in enumerate(fields):
            if exclude is not None and field in exclude_set:
                continue
            if include is not None and field not in include_set:
                continue
            value = getattr(first_row, field)
            title = make_title(field)
            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            else:
                kwargs['align'] = Alignment.LEFT

            hint = hints.get(field, {})
            kwargs.update(hint)

            column = Column(field, **kwargs)
            column_index = include.index(field) if include is not None else i
            columns[column_index] = column

    return [columns[c] for c in sorted(columns)]
