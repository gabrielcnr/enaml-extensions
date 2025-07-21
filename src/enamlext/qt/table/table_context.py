from functools import cached_property
from typing import Any

from qtpy.QtCore import QModelIndex

def default_convert(item):
    return item

class TableContext:
    """
    Lazy evaluation of properties relative to the data request context.
    The Qt MVC calls the data() in table model, passing the roles...
    Depending on the role, we will call callbacks in the column to retrieve things like
    cell style, font style, tooltip, etc...
    We pass the object of TableContext to the callback, and everything there is
    calculated on demand... which hopefully makes it more efficient
    """

    def __init__(self,
                 model: "QTableModel",
                 index: QModelIndex,
                 role: int,
                 column_index: int,
                 column: "Column",
                 convert = default_convert,
                 ):
        self.__model = model
        self.index = index
        self.role = role
        self.column_index = column_index
        self.column = column
        self.convert = convert

    @cached_property
    def row_index(self) -> int:
        return self.index.row()

    @cached_property
    def item(self) -> Any:
        return self.convert(self._raw_item)

    @cached_property
    def _raw_item(self) -> Any:
        return self.__model.get_item_by_index(self.row_index)

    @cached_property
    def raw_value(self) -> Any:
        return self.column.get_value(self._raw_item)

    @cached_property
    def value(self) -> str:
        """ Returns the displayed value. """
        return self.column.get_displayed_value(self._raw_item)