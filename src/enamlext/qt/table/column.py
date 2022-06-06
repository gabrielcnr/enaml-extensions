import datetime
from enum import Enum
from numbers import Number
from operator import itemgetter
from typing import Union, Callable, Optional, Any, Sequence, Mapping

from enamlext.qt.table.defs import CellStyle


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


def generate_columns(items: Sequence):
    first_row = items[0]
    columns = []
    if isinstance(first_row, tuple):
        if is_namedtuple(first_row):
            fields = type(first_row)._fields
        else:
            fields = None
        for i, value in enumerate(first_row):
            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT
            if fields is not None:
                title = make_title(fields[i])
            else:
                title = str(i)
            column = Column(itemgetter(i), title, **kwargs)
            columns.append(column)

    elif isinstance(first_row, Mapping):
        for key, value in first_row.items():
            if isinstance(key, str):
                title = make_title(key)
            else:
                title = str(key)

            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            column = Column(itemgetter(key), title, **kwargs)
            columns.append(column)

    elif hasattr(type(first_row), '__dataclass_fields__'):
        fields = type(first_row).__dataclass_fields__
        for field in fields:
            value = getattr(first_row, field)
            title = make_title(field)
            kwargs = {}
            if isinstance(value, Number):
                kwargs['align'] = Alignment.RIGHT

            column = Column(field, title, **kwargs)
            columns.append(column)

    return columns
