from dataclasses import dataclass

from atom.api import List
from qtpy.QtCore import QItemSelectionModel

from enamlext.qt.table.column import Column
from enamlext.widgets import Table

PEOPLE = [{'name': f'p{i}', 'age': i} for i in range(5)]


@dataclass(frozen=True)  # checkable tables keep checked items in a set
class Fruit:
    name: str


def make_table(parent, **kwargs):
    columns = [Column('name', use_getitem=True), Column('age', use_getitem=True)]
    return Table(parent=parent, columns=columns, items=PEOPLE, **kwargs)


def selected_cells(table):
    return sorted((index.row(), index.column()) for index in table.proxy.widget.selectionModel().selectedIndexes())


def selected_rows(table):
    return sorted({row for row, _ in selected_cells(table)})


def test_setting_selected_items_selects_their_rows(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))

    table.selected_items = [PEOPLE[3], PEOPLE[1]]

    assert selected_rows(table) == [1, 3]


def test_setting_selected_items_replaces_the_selection(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))
    table.selected_items = [PEOPLE[3]]

    table.selected_items = [PEOPLE[0]]
    assert selected_rows(table) == [0]

    table.selected_items = []
    assert selected_rows(table) == []


def test_selected_items_given_up_front_are_selected(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows', selected_items=[PEOPLE[2]]))

    assert selected_rows(table) == [2]


def test_selected_items_are_selected_on_the_rows_showing_them(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))
    model = table.proxy.widget.model()
    model.set_filter(model.columns[1], '> 1')

    table.selected_items = [PEOPLE[0], PEOPLE[3]]

    assert [model.data(model.index(row, 0)) for row in selected_rows(table)] == ['p3']


def test_cells_selected_by_hand_stay_selected_when_selected_items_follows(show_in_window, qtbot):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='cells'))
    widget = table.proxy.widget

    widget.selectionModel().select(widget.model().index(2, 0), QItemSelectionModel.SelectionFlag.ClearAndSelect)
    qtbot.waitUntil(lambda: table.selected_items == [PEOPLE[2]], timeout=2000)

    assert selected_cells(table) == [(2, 0)]


def test_selected_items_given_up_front_fire_selection_changed(show_in_window, qtbot):
    contexts = []

    def make(parent):
        table = make_table(parent, selection_mode='rows', selected_items=[PEOPLE[2]])
        table.observe('selection_changed', lambda change: contexts.append(change['value']))
        return table

    show_in_window(make)

    qtbot.waitUntil(lambda: bool(contexts), timeout=2000)
    assert contexts[-1].selected_items == [PEOPLE[2]]


def test_single_cell_mode_selects_one_cell_of_the_first_row_showing_an_item(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='cell'))

    table.selected_items = [PEOPLE[3], PEOPLE[1]]

    assert selected_cells(table) == [(1, 0)]


def test_checkbox_column_is_left_out_of_the_selection(show_in_window):
    fruits = [Fruit('apple'), Fruit('melon')]
    table = show_in_window(
        lambda parent: Table(
            parent=parent, columns=[Column('name')], items=fruits, selection_mode='rows', checkable=True
        )
    )

    table.selected_items = [fruits[1]]

    assert selected_cells(table) == [(1, 1)]


def test_selected_items_of_another_type_than_the_rows_select_nothing(show_in_window):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))

    table.selected_items = ['p1']

    assert selected_cells(table) == []


class TableThatConvertsInOneCall(Table):
    conversions = List()

    def convert_items(self, items):
        self.conversions.append(len(items))
        return [item['name'] for item in items]


def test_selected_rows_are_converted_in_one_call_when_the_table_offers_it(show_in_window, qtbot):
    table = show_in_window(
        lambda parent: TableThatConvertsInOneCall(
            parent=parent, columns=[Column('name', use_getitem=True)], items=PEOPLE, selection_mode='rows'
        )
    )

    table.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(table.selected_items), timeout=2000)

    assert table.selected_items == ['p0', 'p1', 'p2', 'p3', 'p4']
    assert table.conversions == [5]
