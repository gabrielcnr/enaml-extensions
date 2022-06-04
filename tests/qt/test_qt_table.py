from dataclasses import dataclass
from typing import Any

import pytest

from enamlext.qt.qtable import QTable, Qt, QModelIndex
from enamlext.qt.table.column import Column, Alignment


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
