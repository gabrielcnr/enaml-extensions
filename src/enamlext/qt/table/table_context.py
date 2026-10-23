from typing import TYPE_CHECKING, Any

from qtpy.QtCore import QModelIndex

if TYPE_CHECKING:
    from enamlext.qt.qtable import QTableModel
    from enamlext.qt.table.column import Column


def default_convert(item):
    return item


_UNSET: Any = object()


class TableContext:
    """
    Lazy evaluation of properties relative to the data request context.
    The Qt MVC calls the data() in table model, passing the roles...
    Depending on the role, we will call callbacks in the column to retrieve things like
    cell style, font style, tooltip, etc...
    We pass the object of TableContext to the callback, and everything there is
    calculated on demand... which hopefully makes it more efficient
    """

    def __init__(
        self,
        model: 'QTableModel',
        index: QModelIndex,
        role: int,
        column_index: int,
        column: 'Column',
        convert=default_convert,
    ):
        self.__model = model
        self.index = index
        self.role = role
        self.column_index = column_index
        self.column = column
        self.convert = convert
        # Plain lazy properties, not cached_property: a context is built per styled cell per paint and
        # cached_property's descriptor lookup made reading a value twice as slow. The setters keep the values
        # assignable, as they were with cached_property.
        self.__row_index = self.__item = self.__raw_item = self.__raw_value = self.__value = _UNSET

    @property
    def row_index(self) -> int:
        if self.__row_index is _UNSET:
            self.__row_index = self.index.row()
        return self.__row_index

    @row_index.setter
    def row_index(self, row_index: int) -> None:
        self.__row_index = row_index

    @property
    def item(self) -> Any:
        if self.__item is _UNSET:
            self.__item = self.convert(self._raw_item)
        return self.__item

    @item.setter
    def item(self, item: Any) -> None:
        self.__item = item

    @property
    def _raw_item(self) -> Any:
        if self.__raw_item is _UNSET:
            self.__raw_item = self.__model.get_item_by_index(self.row_index)
        return self.__raw_item

    @_raw_item.setter
    def _raw_item(self, raw_item: Any) -> None:
        self.__raw_item = raw_item

    @property
    def raw_value(self) -> Any:
        if self.__raw_value is _UNSET:
            self.__raw_value = self.column.get_value(self._raw_item)
        return self.__raw_value

    @raw_value.setter
    def raw_value(self, raw_value: Any) -> None:
        self.__raw_value = raw_value

    @property
    def value(self) -> str:
        """Returns the displayed value."""
        if self.__value is _UNSET:
            self.__value = self.column.get_displayed_value(self._raw_item)
        return self.__value

    @value.setter
    def value(self, value: str) -> None:
        self.__value = value
