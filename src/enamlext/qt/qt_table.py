import contextlib

from qtpy.QtWidgets import QApplication, QTableView


class QTable(QTableView):
    """
    A table has basically columns and data.
    """
    def __init__(self, columns, data=None, *, parent=None):
        super().__init__(parent=parent)
        self.columns = columns
        self.data = data

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
    app = QApplication([])

    table = QTable(None, None)
    table.show()

    table.raise_()

    app.exec_()
