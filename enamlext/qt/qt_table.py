# TODO: import from Enaml's abstraction layer of Qt (so it works with PySide)
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from enaml.qt.qt_control import QtControl
from atom.api import Typed

from enamlext.widgets.table import ProxyTable

ALIGN = {
    'left': Qt.AlignLeft,
    'center': Qt.AlignCenter,
    'right': Qt.AlignRight,
}


class TableModel(QAbstractTableModel):
    def __init__(self, columns=None, rows=None, parent=None,
                 rowStyleCallback=None):
        super(TableModel, self).__init__(parent=parent)
        self.columns = columns or []
        self.rows = rows or []
        self.rowStyleCallback = rowStyleCallback

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, columns):
        self._columns = columns
        self.beginResetModel()
        self.endResetModel()

    @property
    def rows(self):
        return self._rows

    @rows.setter
    def rows(self, rows):
        self._rows = rows
        self.beginResetModel()
        self.endResetModel()


    @property
    def rowStyleCallback(self):
        return self._rowStyleCallback

    @rowStyleCallback.setter
    def rowStyleCallback(self, rowStyleCallback):
        self._rowStyleCallback = rowStyleCallback
        self.beginResetModel()
        self.endResetModel()


    def rowCount(self, parent=None):
        return len(self.rows)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role=None):
        if role == Qt.DisplayRole:
            value = self.get_value(index.row(), index.column())
            return value
        elif role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | ALIGN[self.get_column(
                index.column()).align]
        if role in [Qt.BackgroundRole, Qt.ForegroundRole]:
            if self.rowStyleCallback is not None:
                return self.rowStyleCallback(self.get_row(index.row()),
                                             index.row(), role=role)

    def headerData(self, section, orientation, role=None):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                column = self.get_column(section)
                return column.title

        return super(TableModel, self).headerData(section, orientation, role)

    def get_value(self, row_index, column_index):
        column = self.get_column(column_index)
        row = self.get_row(row_index)
        return column.get_value(row)

    def get_column(self, column_index):
        return self.columns[column_index]

    def get_row(self, row_index):
        return self.rows[row_index]


class QTable(QTableView):
    selected_rows_changed = pyqtSignal(list)

    def __init__(self, columns=None, rows=None, parent=None):
        super(QTable, self).__init__(parent=parent)
        model = TableModel(columns=columns, rows=rows, parent=self)
        self.setModel(model)

    def setColumns(self, columns):
        self.model().columns = columns

    def setRows(self, rows):
        self.model().rows = rows

    def selectionChanged(self, selected, deselected):
        row_indexes = sorted(set(i.row() for i in self.selectedIndexes()))
        rows = [self.model().get_row(row_index) for row_index in row_indexes]
        self.selected_rows_changed.emit(rows)
        return super(QTable, self).selectionChanged(selected, deselected)

    def setRowStyleCallback(self, rowStyleCallback):
        self.model().rowStyleCallback = rowStyleCallback


class QtTable(QtControl, ProxyTable):
    widget = Typed(QTable)

    def create_widget(self):
        self.widget = QTable(parent=self.parent_widget())

    def init_widget(self):
        super(QtTable, self).init_widget()
        d = self.declaration
        self.set_columns(d.columns)
        self.set_rows(d.rows)
        self.set_alternate_row_colors(d.alternate_row_colors)
        self.set_select_mode(d.select_mode)
        self.set_stretch_last_column(d.stretch_last_column)
        self.set_selected_rows(d.selected_rows)
        self.set_row_style_callback(d.row_style_callback)

        self.widget.selected_rows_changed.connect(
            self._on_selected_rows_changed)

    def set_columns(self, columns):
        self.widget.setColumns(columns)

    def set_rows(self, rows):
        self.widget.setRows(rows)

    def set_alternate_row_colors(self, alternate_row_colors):
        self.widget.setAlternatingRowColors(alternate_row_colors)

    def set_stretch_last_column(self, stretch_last_column):
        self.widget.horizontalHeader().setStretchLastSection(
            stretch_last_column)

    def set_select_mode(self, select_mode):
        if select_mode == 'single_row':
            self.widget.setSelectionBehavior(self.widget.SelectRows)
            self.widget.setSelectionMode(self.widget.SingleSelection)
        elif select_mode == 'multi_rows':
            self.widget.setSelectionBehavior(self.widget.SelectRows)
            self.widget.setSelectionMode(self.widget.ExtendedSelection)
        elif select_mode == 'single_cell':
            self.widget.setSelectionBehavior(self.widget.SelectItems)
            self.widget.setSelectionMode(self.widget.SingleSelection)
        elif select_mode == 'multi_cells':
            self.widget.setSelectionBehavior(self.widget.SelectItems)
            self.widget.setSelectionMode(self.widget.ExtendedSelection)
        elif select_mode == 'none':
            self.widget.setSelectionMode(self.widget.NoSelection)
        else:
            raise ValueError('Invalid select_mode: {!r}'.format(select_mode))

        self.widget.clearSelection()

    def set_selected_rows(self, rows):
        # TODO: implement this
        pass

    def _on_selected_rows_changed(self, rows):
        self.declaration.selected_rows = rows

    def set_row_style_callback(self, row_style_callback):
        self.widget.setRowStyleCallback(row_style_callback)
