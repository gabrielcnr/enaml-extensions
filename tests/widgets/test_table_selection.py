import gc
from dataclasses import dataclass

import pytest
from atom.api import List, atomref
from enaml.core.enaml_compiler import EnamlCompiler
from enaml.core.parser import parse
from qtpy.QtCore import QCoreApplication, QEvent, QItemSelectionModel

from enamlext.qt.table.column import Column
from enamlext.widgets import Table

PEOPLE = [{'name': f'p{i}', 'age': i} for i in range(5)]


@dataclass(frozen=True)  # checkable tables keep checked items in a set
class Fruit:
    name: str


def make_table(parent, **kwargs):
    columns = [Column('name', use_getitem=True), Column('age', use_getitem=True)]
    return Table(parent=parent, columns=columns, **{'items': PEOPLE, **kwargs})


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
        names = [item['name'] for item in items]
        self.conversions.append(len(names))
        return names


class TableThatConvertsWhenRead(Table):
    converted = List()

    def convert_items(self, items):
        for item in items:
            self.converted.append(item['name'])
            yield item['name']


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


def publications(table):
    contexts = []
    table.observe('selection_changed', lambda change: contexts.append(change['value']))
    return contexts


def test_selected_rows_are_converted_when_selected_items_is_first_read(show_in_window, qtbot):
    table = show_in_window(
        lambda parent: TableThatConvertsWhenRead(
            parent=parent, columns=[Column('name', use_getitem=True)], items=PEOPLE, selection_mode='rows'
        )
    )
    published = publications(table)

    table.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(published), timeout=2000)

    assert table.converted == []
    selected_items = table.selected_items
    assert selected_items == ['p0', 'p1', 'p2', 'p3', 'p4']
    assert isinstance(selected_items, list)
    assert table.selected_items is selected_items
    assert table.converted == ['p0', 'p1', 'p2', 'p3', 'p4']


def test_observer_of_selected_items_is_told_without_anything_reading_them(show_in_window, qtbot):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))
    seen = []
    table.observe('selected_items', lambda change: seen.append(change['value']))

    table.proxy.widget.selectRow(3)

    qtbot.waitUntil(lambda: seen == [[PEOPLE[3]]], timeout=2000)


VIEW = """
from enaml.widgets.api import Container, Label
from enamlext.qt.table.column import Column
from enamlext.widgets import Table

enamldef People(Table):
    columns = [Column('name', use_getitem=True)]
    items = [{'name': 'p0'}, {'name': 'p1'}]
    selection_mode = 'rows'

enamldef Wrapped(Container):
    alias selected_items: people.selected_items
    People: people:
        pass
"""

CONVERTING_VIEW = """
enamldef Copies(People):
    func convert_item(item):
        return dict(item)
"""

WATCHING_VIEWS = {
    'operator': """
enamldef View(Container):
    attr seen = []
    People:
        selected_items :: seen.append(len(change['value']))
""",
    'notification': """
enamldef View(Container):
    attr picked = []
    attr seen << [len(picked)]
    People:
        selected_items >> parent.picked
""",
    'delegation': """
enamldef View(Container):
    attr picked = []
    attr seen = []
    picked :: seen.append(len(change['value']))
    People:
        selected_items := parent.picked
""",
    'expression of another widget': """
enamldef View(Container):
    attr seen = []
    Label:
        text << str(len(people.selected_items))
        text :: seen.append(int(change['value']))
    People: people:
        pass
""",
    'expression reading an alias': """
enamldef View(Container):
    attr seen = []
    Label:
        text << str(len(wrapped.selected_items))
        text :: seen.append(int(change['value']))
    Wrapped: wrapped:
        pass
""",
    'operator on an alias': """
enamldef View(Container):
    attr seen = []
    Wrapped:
        selected_items :: seen.append(len(change['value']))
""",
}


@pytest.mark.parametrize('watching', WATCHING_VIEWS)
def test_enaml_code_watching_selected_items_is_told_without_anything_reading_them(watching, show_in_window, qtbot):
    namespace = {}
    exec(EnamlCompiler.compile(parse(VIEW + WATCHING_VIEWS[watching]), '<view>'), namespace)
    view = show_in_window(lambda parent: namespace['View'](parent=parent))
    (table,) = (child for child in view.traverse() if isinstance(child, Table))

    table.proxy.widget.selectAll()

    qtbot.waitUntil(lambda: view.seen == [2], timeout=2000)


def test_destroyed_table_with_a_selection_nothing_has_read_is_freed(show_in_window, qtbot):
    namespace = {}
    exec(EnamlCompiler.compile(parse(VIEW + CONVERTING_VIEW), '<view>'), namespace)
    # enaml < 0.20 hides a bound func from the garbage collector when it reuses a freed one: make the table's one reused.
    spare = namespace['Copies']()
    freed_funcs = [spare.convert_item for _ in range(8)]
    del freed_funcs
    table = show_in_window(lambda parent: namespace['Copies'](parent=parent))
    published = publications(table)
    table.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(published), timeout=2000)
    published.clear()
    table_ref = atomref(table)

    table.root_object().destroy()
    # On PySide6 the Qt window keeps the widget alive until Qt deletes it.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del table
    gc.collect()

    assert table_ref() is None


class TableObservingItsSelection(Table):
    seen = List()

    def _observe_selected_items(self, change):
        self.seen.append(change['value'])


class TableWithItsOwnProxyUpdate(Table):
    seen = List()

    def _update_proxy(self, change):
        if change['name'] == 'selected_items':
            self.seen.append(change['value'])
        super()._update_proxy(change)


@pytest.mark.parametrize('table_class', [TableObservingItsSelection, TableWithItsOwnProxyUpdate])
def test_subclass_watching_selected_items_is_told_without_anything_reading_them(table_class, show_in_window, qtbot):
    table = show_in_window(
        lambda parent: table_class(
            parent=parent, columns=[Column('name', use_getitem=True)], items=PEOPLE, selection_mode='rows'
        )
    )

    table.proxy.widget.selectRow(3)

    qtbot.waitUntil(lambda: [PEOPLE[3]] in table.seen, timeout=2000)


@pytest.mark.parametrize('wanted', [[PEOPLE[1]], []])
def test_setting_selected_items_replaces_a_selection_nothing_has_read(wanted, show_in_window, qtbot):
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows'))
    published = publications(table)
    table.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(published), timeout=2000)

    table.selected_items = wanted

    assert selected_rows(table) == [PEOPLE.index(person) for person in wanted]
    assert table.selected_items == wanted


def test_selected_items_read_late_are_those_that_were_selected(show_in_window, qtbot):
    people = list(PEOPLE)
    table = show_in_window(lambda parent: make_table(parent, selection_mode='rows', items=people))
    published = publications(table)
    table.proxy.widget.selectRow(1)
    qtbot.waitUntil(lambda: bool(published), timeout=2000)

    people.insert(0, {'name': 'new', 'age': 99})
    table.refresh()

    assert table.selected_items == [PEOPLE[1]]
