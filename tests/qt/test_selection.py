from collections import deque
from dataclasses import dataclass

import pytest
from qtpy.QtCore import QItemSelection, QItemSelectionModel, QPoint, Qt

from enamlext.qt.qtable import Cell, QTable, QTableModel, SelectionContext, SelectionMode
from enamlext.qt.table.column import Column


@dataclass(frozen=True)
class Row:
    name: str
    age: int


ITEMS = [Row(f'n{i}', i) for i in range(6)]


@pytest.fixture
def make_table(qtbot):
    def make(items=ITEMS, **kwargs):
        table = QTable([Column('name'), Column('age')], items, sortable=False, **kwargs)
        qtbot.addWidget(table)
        contexts = []
        table.on_selection.connect(contexts.append)
        return table, contexts

    return make


def select(table, top, left, bottom, right, flag=QItemSelectionModel.SelectionFlag.ClearAndSelect):
    model = table.model()
    table.selectionModel().select(QItemSelection(model.index(top, left), model.index(bottom, right)), flag)


def click_header(qtbot, table, column, modifier=Qt.KeyboardModifier.NoModifier):
    header = table.horizontalHeader()
    middle = QPoint(header.sectionViewportPosition(column) + header.sectionSize(column) // 2, header.height() // 2)
    qtbot.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, modifier, middle)


def selected_columns(table):
    return sorted(index.column() for index in table.selectionModel().selectedColumns())


def test_removed_indexes_are_the_deselected_cells(make_table):
    table, contexts = make_table()
    select(table, 0, 0, 0, 1)

    select(table, 2, 0, 2, 0)

    assert sorted(contexts[-1].added_indexes) == [Cell(2, 0)]
    assert sorted(contexts[-1].removed_indexes) == [Cell(0, 0), Cell(0, 1)]


def test_selected_items_are_distinct_and_in_row_order_across_ranges(make_table):
    table, contexts = make_table()
    select(table, 4, 0, 5, 0)
    select(table, 1, 1, 4, 1, QItemSelectionModel.SelectionFlag.Select)

    assert contexts[-1].selected_items == [ITEMS[1], ITEMS[2], ITEMS[3], ITEMS[4], ITEMS[5]]


def test_selected_items_in_row_selection_mode(make_table):
    table, contexts = make_table()
    table.set_selection_mode(SelectionMode.MULTI_ROWS)

    table.selectRow(3)

    assert contexts[-1].selected_items == [ITEMS[3]]
    assert sorted(contexts[-1].selected_indexes) == [Cell(3, 0), Cell(3, 1)]


def test_selecting_only_the_checkbox_column_selects_no_items(make_table):
    table, contexts = make_table(checkable=True)

    select(table, 0, 0, 1, 0)

    assert contexts[-1].selected_items == []
    assert contexts[-1].selected_indexes == []


def test_select_all_in_a_checkable_table_selects_every_item_once(make_table):
    table, contexts = make_table(checkable=True)

    table.selectAll()

    assert contexts[-1].selected_items == ITEMS
    assert {index.column for index in contexts[-1].selected_indexes} == {1, 2}


def test_context_is_a_snapshot_of_the_selection_when_it_changed(make_table):
    table, contexts = make_table()
    select(table, 1, 0, 1, 1)
    context = contexts[-1]

    select(table, 4, 0, 4, 1)

    assert context.selected_items == [ITEMS[1]]
    assert sorted(context.selected_indexes) == [Cell(1, 0), Cell(1, 1)]


def test_selection_change_does_not_visit_every_selected_cell(make_table, monkeypatch):
    items = [Row(f'n{i}', i) for i in range(2000)]
    table, contexts = make_table(items=items)
    calls = 0
    original_flags = QTableModel.flags

    def counting_flags(self, index):
        nonlocal calls
        calls += 1
        return original_flags(self, index)

    monkeypatch.setattr(QTableModel, 'flags', counting_flags)

    table.selectAll()
    selected_items = contexts[-1].selected_items

    assert selected_items == items
    assert calls < len(items)  # expanding the selection would check all 4000 selected cells


def test_selected_values(make_table):
    table, contexts = make_table()

    select(table, 2, 1, 3, 1)

    assert sorted(contexts[-1].selected_values) == [(Cell(2, 1), 2), (Cell(3, 1), 3)]


def test_current_selection_context(make_table):
    table, _ = make_table()
    select(table, 1, 0, 2, 0)

    context = table.get_current_selection_context()

    assert context.selected_items == [ITEMS[1], ITEMS[2]]
    assert context.added_indexes is None
    assert context.removed_indexes is None


def test_context_built_from_index_lists_still_works(make_table):
    table, _ = make_table()
    model = table.model()
    indexes = [model.index(3, 0), model.index(1, 1)]

    context = SelectionContext(
        table=table, selected_indexes=indexes, current=model.index(3, 0), added=indexes, removed=None
    )

    assert context.selected_items == [ITEMS[1], ITEMS[3]]
    assert context.added_indexes == [Cell(3, 0), Cell(1, 1)]
    assert context.removed_indexes is None
    assert context.current_index == Cell(3, 0)


def test_painting_the_header_does_not_visit_every_selected_row(make_table, monkeypatch, qtbot):
    items = [Row(f'n{i}', i) for i in range(2000)]
    table, _ = make_table(items=items)
    table.show()
    qtbot.waitExposed(table)
    table.selectAll()
    calls = 0
    original_flags = QTableModel.flags

    def counting_flags(self, index):
        nonlocal calls
        calls += 1
        return original_flags(self, index)

    monkeypatch.setattr(QTableModel, 'flags', counting_flags)

    table.horizontalHeader().grab()

    assert calls < len(items)  # telling whether a whole column is selected checks each of its 2000 cells


def test_click_on_a_header_selects_its_column(make_table, qtbot):
    table, _ = make_table()
    table.show()
    qtbot.waitExposed(table)

    click_header(qtbot, table, 1)

    assert selected_columns(table) == [1]


def test_ctrl_click_on_headers_adds_and_removes_their_columns(make_table, qtbot):
    table, _ = make_table()
    table.show()
    qtbot.waitExposed(table)
    click_header(qtbot, table, 0)

    click_header(qtbot, table, 1, Qt.KeyboardModifier.ControlModifier)
    assert selected_columns(table) == [0, 1]

    click_header(qtbot, table, 0, Qt.KeyboardModifier.ControlModifier)
    assert selected_columns(table) == [1]


class RowsCountingSingleFetches(list):
    single_fetches = 0

    def __getitem__(self, index):
        if not isinstance(index, slice):
            self.single_fetches += 1
        return super().__getitem__(index)


def test_selected_items_are_not_fetched_one_by_one(make_table):
    items = RowsCountingSingleFetches(Row(f'n{i}', i) for i in range(2000))
    table, contexts = make_table(items=items)
    table.selectAll()
    items.single_fetches = 0

    assert contexts[-1].selected_items == items
    assert items.single_fetches == 0


def test_selected_items_of_rows_that_cannot_be_sliced(make_table):
    table, contexts = make_table(items=deque(ITEMS))

    select(table, 1, 0, 2, 1)

    assert contexts[-1].selected_items == [ITEMS[1], ITEMS[2]]


def test_iterating_the_selected_items_gives_those_selected_when_asked(make_table):
    items = list(ITEMS)
    table, contexts = make_table(items=items)
    select(table, 1, 0, 2, 1)

    selected = contexts[-1].iter_selected_items()
    items.insert(0, Row('new', 99))

    assert list(selected) == [ITEMS[1], ITEMS[2]]
