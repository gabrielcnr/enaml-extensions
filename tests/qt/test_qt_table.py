from collections import Counter
from dataclasses import dataclass
from typing import Any

import pytest
from qtpy.QtGui import QColor

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
        Person(name="John", age=33),
        Person(name="Pam", age=22),
    ]

    columns = [
        Column("name", title="Name"),
        Column("age", align=Alignment.RIGHT),
    ]

    with table.updating_internals():
        table.columns = columns
        table.items = items

    assert table.text(1, 0) == "Pam"


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
