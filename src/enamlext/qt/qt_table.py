import contextlib
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any, Union, Callable

from PyQt5.QtCore import QObject
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import QApplication, QTableView


class SelectionMode(Enum):
    SINGLE_CELL = auto()
    MULTI_CELLS = auto()
    SINGLE_ROW = auto()
    MULTI_ROWS = auto()


class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


QT_ALIGNMENT_MAP = {
    Alignment.LEFT: int(Qt.AlignLeft | Qt.AlignVCenter),
    Alignment.CENTER: int(Qt.AlignCenter | Qt.AlignVCenter),
    Alignment.RIGHT: int(Qt.AlignRight | Qt.AlignVCenter),
}

QtAlignment = int
def to_qt_alignment(align: Alignment) -> QtAlignment:
    return QT_ALIGNMENT_MAP[align]


class TableContext:
    """
    Lazy evaluation of properties relative to the data request context.
    The Qt MVC calls the data() in table model, passing the roles...
    Depending on the role, we will call callbacks in the column to retrieve things like
    cell style, font style, tooltip, etc...
    We pass the object of TableContext to the callback, and everything there is
    calculated on demand... which hopefully makes it more efficient
    """
    def __init__(self, model, index, role):
        self.__model = model
        self.index = index
        self.role = role




class Column:
    def __init__(self,
                 key: Union[str, Callable],
                 title: Optional[str] = None,
                 align: Alignment = Alignment.LEFT,
                 tooltip: Optional[Union[str, Callable]] = None,  # TODO: how to specify the types for the signature of the callback here?
                 ):
        self.key = key
        self.title = title
        self.align = align

    def get_value(self, item: Any) -> Any:
        return getattr(item, self.key)

    def get_tooltip(self, item: Any) -> str:
        if self.tooltip is not None:
            if callable(self.tooltip):
                return self.tooltip()



    #
    # def get_align(self, item: Any) -> Alignment:
    #     return self.align



class QTableModel(QAbstractTableModel):
    def __init__(self, columns, items=None, *, checkable=False, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.items = items
        self.checkable = checkable

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.items)  # O(1)

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.columns) + int(self.checkable)  # O(1)

    def data(self, index: QModelIndex, role: int) -> Any:
        if role == Qt.DisplayRole:
            if self.checkable:
                offset = 1
            else:
                offset = 0
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                item = self.items[index.row()]  # O(1)
                return column.get_value(item)
        elif role == Qt.TextAlignmentRole:
            if self.checkable:
                offset = 1
            else:
                offset = 0
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                return to_qt_alignment(column.align)
        elif role == Qt.CheckStateRole and self.checkable and index.column() == 0:
            return Qt.Checked

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> str:
        if orientation == Qt.Horizontal:
            if self.checkable:
                offset = 1

                # TEMP
                if section == 0:
                    return
                # END OF TEMP
            else:
                offset = 0

            if role == Qt.DisplayRole:
                column = self.columns[section - offset]  # O(1)
                if column.title is not None:
                    return column.title
            elif role == Qt.TextAlignmentRole:
                column = self.columns[section - offset]  # O(1)
                return to_qt_alignment(column.align)

        return super().headerData(section, orientation, role)


class QTable(QTableView):
    """
    A table has basically columns and a collection of items.
    """

    def __init__(self,
                 columns,
                 items=None,
                 *,
                 checkable: bool = False,
                 parent: QObject = None):
        super().__init__(parent=parent)
        self.columns = columns
        self.items = items or []
        model = QTableModel(self.columns, items, checkable=checkable)
        self.setModel(model)

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        # refresh the model

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self._items = items
        # refresh the model

    @property
    def checkable(self) -> bool:
        return self.model().checkable

    @checkable.setter
    def checkable(self, checkable):
        self.model().checkable = checkable

    @contextlib.contextmanager
    def updating_internals(self):
        self.__updating = True
        try:
            yield
        finally:
            self.__updating = False
            self.refresh()

    def refresh(self):
        pass

    def set_selection_mode(self, selection_mode: SelectionMode):
        if selection_mode == SelectionMode.SINGLE_CELL:
            self.setSelectionMode(self.SingleSelection)
            self.setSelectionBehavior(self.SelectItems)
        elif selection_mode == SelectionMode.MULTI_CELLS:
            self.setSelectionMode(self.MultiSelection)
            self.setSelectionBehavior(self.SelectItems)
        elif selection_mode == SelectionMode.SINGLE_ROW:
            self.setSelectionMode(self.SingleSelection)
            self.setSelectionBehavior(self.SelectRows)
        elif selection_mode == SelectionMode.MULTI_ROWS:
            self.setSelectionMode(self.MultiSelection)
            self.setSelectionBehaviour(self.SelectRows)

    # Header visibility controls

    def show_vertical_header(self):
        self.verticalHeader().show()

    def hide_vertical_header(self):
        self.verticalHeader().hide()

    def set_vertical_header_visible(self, visible: bool):
        self.verticalHeader().setVisible(visible)

    def show_horizontal_header(self):
        self.horizontalHeader().show()

    def hide_horizontal_header(self):
        self.horizontalHeader().hide()

    def set_horizontal_header_visible(self, visible: bool):
        self.horizontalHeader().setVisible(visible)


if __name__ == '__main__':
    # Making Ctrl+C work
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = QApplication([])

    columns = [
        Column("name", title="Name"),
        Column("age", align=Alignment.RIGHT)
    ]


    @dataclass
    class Person:
        name: str
        age: int
        sex: str


    items = [
               Person(name="John", age=33, sex="M"),
               Person(name="Pam", age=22, sex="F"),
           ] * 10

    table = QTable(columns, items, checkable=True)
    # table.set_selection_mode(SelectionMode.MULTI_CELLS)
    table.set_selection_mode(SelectionMode.SINGLE_ROW)
    table.show()
    table.set_vertical_header_visible(False)
    table.show_horizontal_header()

    app.exec_()
