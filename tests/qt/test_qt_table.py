from collections import Counter
from dataclasses import dataclass
from typing import Any

import pytest
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QStyledItemDelegate

from enamlext.qt.qtable import QTable, Qt, QModelIndex
from enamlext.qt.table.column import Column, Alignment
from enamlext.qt.table.defs import CellStyle


class QTestTable(QTable):
    """
    A QTable with some funky testing capabilities.
    """

    def index(self, row_index: int, column_index: int) -> QModelIndex:
        return self.model().index(row_index, column_index)

    def data(self, row_index: int, column_index: int, role: int) -> Any:
        index = self.index(row_index, column_index)
        return self.model().data(index, role)

    def text(self, row_index: int, column_index: int) -> str:
        return self.data(row_index, column_index, Qt.DisplayRole)


@pytest.fixture
def table(qtbot):
    table = QTestTable(columns=[])
    qtbot.addWidget(table)
    yield table


def test_displayed_data_basic(table):
    @dataclass
    class Person:
        name: str
        age: int

    items = [
        Person(name='John', age=33),
        Person(name='Pam', age=22),
    ]

    columns = [
        Column('name', title='Name'),
        Column('age', align=Alignment.RIGHT),
    ]

    with table.updating_internals():
        table.columns = columns
        table.items = items

    assert table.text(1, 0) == 'Pam'


@dataclass
class Person:
    name: str
    age: int


def test_cell_style_is_served_for_font_foreground_and_background_roles(table):
    def cell_style(context):
        if context.raw_value < 30:
            return CellStyle(color=QColor('red'), background=QColor('yellow'), font='bold')

    with table.updating_internals():
        table.columns = [Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]

    assert table.data(1, 0, Qt.FontRole).bold()
    assert table.data(1, 0, Qt.ForegroundRole) == QColor('red')
    assert table.data(1, 0, Qt.BackgroundColorRole) == QColor('yellow')

    assert not table.data(0, 0, Qt.FontRole).bold()
    assert table.data(0, 0, Qt.ForegroundRole) is None
    assert table.data(0, 0, Qt.BackgroundColorRole) is None


def test_cell_style_callback_runs_once_per_cell_on_each_repaint(table):
    calls = Counter()

    def cell_style(context):
        calls[context.row_index, context.column_index] += 1
        return CellStyle(color=QColor('red'), background=QColor('yellow'), font='bold')

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style), Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    table.resize(400, 300)

    calls.clear()
    table.viewport().grab()
    assert calls == {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 1}

    table.viewport().grab()
    assert calls == {(0, 0): 2, (0, 1): 2, (1, 0): 2, (1, 1): 2}


def test_cell_style_reflects_current_item_after_a_repaint(table):
    def cell_style(context):
        if context.raw_value < 30:
            return CellStyle(font='bold')

    person = Person(name='John', age=33)
    with table.updating_internals():
        table.columns = [Column('age', cell_style=cell_style)]
        table.items = [person]
    table.resize(400, 300)

    table.viewport().grab()
    person.age = 22

    assert table.data(0, 0, Qt.FontRole).bold()


class StyleRecordingDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        self.painted = {}

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        self.painted[index.row(), index.column()] = (
            option.backgroundBrush.color().name(),
            option.palette.color(QPalette.Text).name(),
            option.font.bold(),
            option.font.italic(),
        )


def test_each_cell_is_painted_with_its_own_cell_style(table):
    styles = {
        (0, 0): CellStyle(color=QColor('#ff0000'), background=QColor('#ffff00'), font='bold'),
        (0, 1): CellStyle(color=QColor('#0000ff'), background=QColor('#00ff00'), font='italic'),
        (1, 0): CellStyle(color=QColor('#800080'), background=QColor('#00ffff'), font='bold italic'),
        (1, 1): CellStyle(color=QColor('#008000'), background=QColor('#ffc0cb')),
    }

    def cell_style(context):
        return styles[context.row_index, context.column_index]

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style), Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    table.resize(400, 300)
    delegate = StyleRecordingDelegate(parent=table)
    table.setItemDelegate(delegate)

    table.viewport().grab()

    assert delegate.painted == {
        (0, 0): ('#ffff00', '#ff0000', True, False),
        (0, 1): ('#00ff00', '#0000ff', False, True),
        (1, 0): ('#00ffff', '#800080', True, True),
        (1, 1): ('#ffc0cb', '#008000', False, False),
    }


def test_collect_stats_records_timings(table):
    column = Column('age', collect_stats=True)
    with table.updating_internals():
        table.columns = [column]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    column.stats.clear()  # populating the table already read every cell to size the columns

    assert table.text(0, 0) == '33'

    assert column.stats[Qt.DisplayRole]['n_calls'] == 1
    assert column.stats[Qt.DisplayRole]['cum_time'] >= 0


@pytest.mark.parametrize(
    ('order', 'expected'), [(Qt.AscendingOrder, ['22', '33', '41']), (Qt.DescendingOrder, ['41', '33', '22'])]
)
def test_sorting_by_a_column(qtbot, order, expected):
    table = QTestTable(columns=[Column('age')], items=[Person('John', 33), Person('Pam', 22), Person('Ann', 41)])
    qtbot.addWidget(table)

    table.sortByColumn(0, order)

    assert [table.text(row, 0) for row in range(3)] == expected
