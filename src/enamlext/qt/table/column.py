import datetime
from enum import Enum
from functools import partial
from numbers import Number
from operator import itemgetter
from typing import Union, Callable, Optional, Any, Sequence, Mapping, List, Dict, Container

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

from enamlext.qt.qt_dataframe import DataFrameProxy
from enamlext.qt.table.defs import CellStyle, ColumnSize
from enamlext.qt.table.table_context import TableContext


class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


AUTO_ALIGN = object()  # sentinel


class Column:
    def __init__(self,
                 key: Union[str, Callable],
                 title: Optional[str] = None,
                 align: Alignment = AUTO_ALIGN,
                 tooltip: Optional[Union[str, Callable]] = None,
                 # TODO: how to specify the types for the signature of the callback here?
                 cell_style: Optional[Callable] = None,
                 use_getitem: bool = False,
                 fmt: str = '',
                 size: Union[ColumnSize, int] = ColumnSize.AUTO,
                 ):
        self.key = key
        self._link_get_value_method(key, use_getitem)
        if title is None and isinstance(key, str):
            title = key.title()
        self.title = title
        self.align = align
        self.tooltip = tooltip
        self.cell_style = cell_style
        self.fmt = fmt
        self.size = size  # TODO: should we also support callable?

    def _link_get_value_method(self, key, use_getitem):
        if callable(key):
            self.get_value = key  # we re-wire the get_value() here
        elif use_getitem:
            self.get_value = self.get_value_by_getitem_lookup
        else:
            self.get_value = self.get_value_by_attribute_lookup

    def get_value(self, item: Any) -> Any:
        raise RuntimeError('get_value() not dynamic linked during initialization')

    def get_value_by_attribute_lookup(self, item: Any) -> Any:
        return getattr(item, self.key)

    def get_value_by_getitem_lookup(self, item: Any) -> Any:
        return item[self.key]

    def get_displayed_value(self, item: Any) -> str:
        value = self.get_value(item)
        if callable(self.fmt):
            return self.fmt(value)
        else:
            return format(value, self.fmt)

    def get_tooltip(self, table_context: "TableContext") -> str:
        if self.tooltip is not None:
            if callable(self.tooltip):
                return str(self.tooltip(table_context))  # TODO: is it a good practice to enforce str() here?
            else:
                return self.tooltip  # str
        else:
            return repr(table_context.raw_value)

    def get_cell_style(self, table_context: "TableContext") -> Optional[CellStyle]:
        if self.cell_style is not None:
            return self.cell_style(table_context) or CellStyle()

    def get_align(self, item: Any) -> Alignment:
        if self.align is AUTO_ALIGN:
            # TODO: consider shortcircuiting this - maybe
            #       maybe this should only be done once, for the first time - then shortcircuit
            #       or maybe the user wants to have mixed alignments on the same column, so it can provide a callback
            value = self.get_value(item)
            align = self.resolve_column_alignment_based_on_value(value)
            return align
        else:
            return self.align

    def resolve_column_alignment_based_on_value(self, value: Any) -> Alignment:
        if isinstance(value, Number):
            return Alignment.RIGHT
        elif isinstance(value, (datetime.datetime, datetime.date)):
            return Alignment.CENTER
        elif isinstance(value, str):
            return Alignment.LEFT
        else:
            return Alignment.LEFT


# Auto-Generation of Columns

def make_title(title: str):
    return title.replace('_', ' ').title()


def is_namedtuple(obj):
    return isinstance(obj, tuple) and hasattr((T := type(obj)), '_fields') and hasattr(T, '_asdict')


RED = QColor(Qt.red)
NEGATIVE_NUMBER_CELL_STYLE = CellStyle(color=RED)


def get_cell_style_for_negative_numbers(table_context: TableContext) -> CellStyle:
    if table_context.raw_value < 0:
        return NEGATIVE_NUMBER_CELL_STYLE


def generate_columns(items: Sequence, *, hints: Optional[Dict] = None,
                     exclude: Optional[Container[str]] = None) -> List[Column]:
    """
    hints: only make sense with named keys?
           hints are a dict of column id -> kwargs dict that will
           get passed to the Column object
    """
    if hints is None:
        hints = {}
    if exclude is None:
        exclude = set()
    if not len(items):
        return []
    first_row = items[0]
    columns = []
    if isinstance(first_row, tuple):
        if is_namedtuple(first_row):
            fields = type(first_row)._fields
        else:
            fields = None
        for i, value in enumerate(first_row):
            if i in exclude:
                continue
            if fields is not None:
                title = make_title(fields[i])
            else:
                title = str(i)
            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            hint = hints.get(i, {})
            kwargs.update(hint)
            column = Column(itemgetter(i), **kwargs)
            columns.append(column)

    elif isinstance(first_row, Mapping):
        for key, value in first_row.items():
            if key in exclude:
                continue
            if isinstance(key, str):
                title = make_title(key)
            else:
                title = str(key)

            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            hint = hints.get(key, {})
            kwargs.update(hint)
            column = Column(itemgetter(key), **kwargs)
            columns.append(column)

    elif hasattr(type(first_row), '__dataclass_fields__'):
        fields = type(first_row).__dataclass_fields__
        for field in fields:
            if field in exclude:
                continue
            value = getattr(first_row, field)
            title = make_title(field)
            kwargs = {'title': title}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            hint = hints.get(field, {})
            kwargs.update(hint)

            column = Column(field, **kwargs)
            columns.append(column)

    elif isinstance(items, DataFrameProxy):
        import pandas as pd
        import numpy as np
        df = items.df
        for i, (name, dtype) in enumerate(df.dtypes.items()):
            if not isinstance(dtype, pd.core.dtypes.dtypes.CategoricalDtype) and np.issubdtype(dtype, np.number):
                align = Alignment.RIGHT
                style = get_cell_style_for_negative_numbers
            else:
                align = Alignment.LEFT
                style = None

            def extract_value_by_index(series: pd.Series, index: int) -> Any:
                return series.iloc[index]

            key = partial(extract_value_by_index, index=i)

            kwargs = {'title': name, 'align': align, 'cell_style': style}

            hint = hints.get(name, {})
            kwargs.update(hint)

            column = Column(key, **kwargs)
            columns.append(column)

    return columns
