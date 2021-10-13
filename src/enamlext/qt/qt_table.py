import contextlib
from dataclasses import dataclass
from typing import Optional, Any, Union, Callable

from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt
from qtpy.QtWidgets import QApplication, QTableView


class Column:
    def __init__(self, key: Union[str, Callable]):
        self.key = key

    def get_value(self, data: Any) -> Any:
        return getattr(data, self.key)


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


if __name__ == '__main__':
    # Making Ctrl+C work
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = QApplication([])

    columns = [
        Column("name"),
        Column("age")
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
    table.show()

    app.exec_()
