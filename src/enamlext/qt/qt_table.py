import contextlib
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any, Union, Callable

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


class Column:
    def __init__(self,
                 key: Union[str, Callable],
                 title: Optional[str] = None,
                 align: Alignment = Alignment.LEFT):
        self.key = key
        self.title = title
        self.align = align

    def get_value(self, data: Any) -> Any:
        return getattr(data, self.key)
    #
    # def get_align(self, data: Any) -> Alignment:
    #     return self.align



class QTableModel(QAbstractTableModel):
    def __init__(self, columns, data=None, *, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.data = data

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.data)  # O(1)

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.columns)  # O(1)

    def data(self, index: QModelIndex, role: int) -> Any:
        if role == Qt.DisplayRole:
            column = self.columns[index.column()]  # O(1)
            data = self.data[index.row()]  # O(1)
            return column.get_value(data)
        elif role == Qt.TextAlignmentRole:
            column = self.columns[index.column()]  # O(1)
            return to_qt_alignment(column.align)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> str:
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                column = self.columns[section]  # O(1)
                if column.title is not None:
                    return column.title
            elif role == Qt.TextAlignmentRole:
                column = self.columns[section]  # O(1)
                return to_qt_alignment(column.align)

        return super().headerData(section, orientation, role)


class QTable(QTableView):
    """
    A table has basically columns and data.
    """

    def __init__(self, columns, data=None, *, parent=None):
        super().__init__(parent=parent)
        self.columns = columns
        self.data = data or []

        model = QTableModel(self.columns, data)
        self.setModel(model)

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        # refresh the model

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        # refresh the model

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


    data = [
               Person(name="John", age=33, sex="M"),
               Person(name="Pam", age=22, sex="F"),
           ] * 10

    table = QTable(columns, data)
    # table.set_selection_mode(SelectionMode.MULTI_CELLS)
    table.set_selection_mode(SelectionMode.SINGLE_ROW)
    table.show()
    table.set_vertical_header_visible(False)
    table.show_horizontal_header()

    app.exec_()
