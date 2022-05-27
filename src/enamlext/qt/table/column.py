import datetime
from enum import Enum
from numbers import Number
from typing import Union, Callable, Optional, Any

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
                 ):
        self.key = key
        self._link_get_value_method(key, use_getitem)
        if title is None and isinstance(key, str):
            title = key.title()
        self.title = title
        self.align = align
        self.tooltip = tooltip
        self.cell_style = cell_style

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

