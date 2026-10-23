from dataclasses import dataclass

import pytest
from enaml.widgets.api import Container, Window
from qtpy.QtCore import QItemSelectionModel, QPoint
from qtpy.QtTest import QTest

import enamlext.qt.qtable
from enamlext.qt.qtable import Qt, QTable
from enamlext.qt.table.column import Column
from enamlext.widgets import Table

ASCENDING = Qt.SortOrder.AscendingOrder
DESCENDING = Qt.SortOrder.DescendingOrder


@dataclass(frozen=True)  # checkable tables keep checked items in a set
class Person:
    name: str
    age: int


PEOPLE = [Person('Cid', 30), Person('Ann', 10), Person('Bob', 20)]


def make_table(qtbot, items=PEOPLE, **kwargs):
    table = QTable([Column('name'), Column('age')], list(items), **kwargs)
    qtbot.addWidget(table)
    return table


def names(table):
    model = table.model()
    name_section = 1 if model.checkable else 0
    return [model.data(model.index(row, name_section)) for row in range(model.rowCount())]


def show(qtbot, table):
    table.show()
    qtbot.waitExposed(table)


def click_header(qtbot, table, section):
    show(qtbot, table)
    header = table.horizontalHeader()
    pos = QPoint(header.sectionViewportPosition(section) + 5, header.height() // 2)
    QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=pos)


@pytest.fixture
def sorts(monkeypatch):
    calls = []
    sort_order = enamlext.qt.qtable._sort_order

    def counted(*args, **kwargs):
        calls.append(args)
        return sort_order(*args, **kwargs)

    monkeypatch.setattr(enamlext.qt.qtable, '_sort_order', counted)
    return calls


def test_a_new_table_shows_the_items_in_the_given_order(qtbot):
    table = make_table(qtbot)

    assert names(table) == ['Cid', 'Ann', 'Bob']
    assert table.horizontalHeader().sortIndicatorSection() == -1


def test_a_new_enaml_table_shows_the_items_in_the_given_order(enaml_app):
    window = Window()
    table = Table(parent=Container(parent=window), columns=[Column('name'), Column('age')], items=list(PEOPLE))
    window.initialize()
    window.activate_proxy()

    assert names(table.proxy.widget) == ['Cid', 'Ann', 'Bob']
    window.destroy()


def test_constructing_a_table_does_not_sort(qtbot, sorts):
    make_table(qtbot)

    assert sorts == []


def test_header_clicks_cycle_ascending_then_descending_and_sort_once_each(qtbot, sorts):
    table = make_table(qtbot)

    click_header(qtbot, table, 0)
    assert names(table) == ['Ann', 'Bob', 'Cid']
    click_header(qtbot, table, 0)
    assert names(table) == ['Cid', 'Bob', 'Ann']
    click_header(qtbot, table, 0)
    assert names(table) == ['Ann', 'Bob', 'Cid']
    assert len(sorts) == 3


def test_sort_by_column_sorts_once(qtbot, sorts):
    table = make_table(qtbot)

    table.sortByColumn(1, ASCENDING)

    assert names(table) == ['Ann', 'Bob', 'Cid']
    assert len(sorts) == 1


def test_new_items_are_sorted_like_the_previous_ones(qtbot):
    table = make_table(qtbot)
    table.sortByColumn(1, DESCENDING)

    table.items = [Person('Dan', 5), Person('Eve', 50)]

    assert names(table) == ['Eve', 'Dan']


def test_filtering_keeps_the_rows_sorted(qtbot):
    table = make_table(qtbot, items=[*PEOPLE, Person('Dan', 40)])
    table.sortByColumn(1, ASCENDING)

    table.on_filter_changed(table.columns[1], '> 15')
    assert names(table) == ['Bob', 'Cid', 'Dan']

    table.clear_filters()
    assert names(table) == ['Ann', 'Bob', 'Cid', 'Dan']


def test_refresh_resorts_the_rows(qtbot):
    ages = {'Cid': 30, 'Ann': 10, 'Bob': 20}
    table = QTable([Column('name', use_getitem=True), Column(lambda row: ages[row['name']], title='Age')], [])
    qtbot.addWidget(table)
    table.items = [{'name': name} for name in ages]
    table.sortByColumn(1, ASCENDING)

    ages['Ann'] = 99
    table.refresh()

    assert names(table) == ['Bob', 'Cid', 'Ann']


def test_refresh_keeps_the_selection_on_its_row_when_the_rows_move(qtbot):
    ages = {'Cid': 30, 'Ann': 10, 'Bob': 20}
    table = QTable([Column('name', use_getitem=True), Column(lambda row: ages[row['name']], title='Age')], [])
    qtbot.addWidget(table)
    table.items = [{'name': name} for name in ages]
    table.sortByColumn(1, ASCENDING)
    model = table.model()
    table.selectionModel().select(model.index(0, 0), QItemSelectionModel.SelectionFlag.ClearAndSelect)  # Ann

    ages['Ann'] = 99
    table.refresh()

    assert [model.data(index) for index in table.selectionModel().selectedIndexes()] == ['Ann']


def test_refresh_of_an_unsorted_table_keeps_the_given_order(qtbot):
    table = make_table(qtbot)

    table.refresh()

    assert names(table) == ['Cid', 'Ann', 'Bob']


@pytest.mark.parametrize('unsort', ['sort_by_column', 'sort_indicator'])
def test_sorting_by_minus_one_returns_to_the_given_order(qtbot, unsort):
    table = make_table(qtbot)
    table.sortByColumn(1, ASCENDING)

    if unsort == 'sort_by_column':
        table.sortByColumn(-1, ASCENDING)
    else:
        table.horizontalHeader().setSortIndicator(-1, ASCENDING)

    assert names(table) == ['Cid', 'Ann', 'Bob']


def test_turning_sorting_off_returns_to_the_given_order_and_stops_sorting(qtbot):
    table = make_table(qtbot)
    table.sortByColumn(1, ASCENDING)

    table.sortable = False
    assert names(table) == ['Cid', 'Ann', 'Bob']

    table.items = [Person('Eve', 50), Person('Dan', 5)]
    assert names(table) == ['Eve', 'Dan']


def test_header_clicks_do_nothing_when_sorting_is_off(qtbot):
    table = make_table(qtbot, sortable=False)

    click_header(qtbot, table, 0)

    assert names(table) == ['Cid', 'Ann', 'Bob']


def test_replacing_the_sorted_column_drops_the_sort_and_its_arrow(qtbot):
    table = make_table(qtbot)
    table.sortByColumn(1, ASCENDING)

    table.columns = [Column('name'), Column('age', title='Years')]
    table.items = list(PEOPLE)

    assert names(table) == ['Cid', 'Ann', 'Bob']
    assert table.horizontalHeader().sortIndicatorSection() == -1


def test_a_checkable_table_sorts_by_the_clicked_column(qtbot):
    table = make_table(qtbot, items=[Person('Bob', 10), Person('Cid', 20), Person('Ann', 30)], checkable=True)

    click_header(qtbot, table, 1)  # "Name"; section 0 is the checkbox column

    assert names(table) == ['Ann', 'Bob', 'Cid']


def test_clicking_the_checkbox_column_does_not_sort(qtbot):
    table = make_table(qtbot, checkable=True)

    click_header(qtbot, table, 0)

    assert names(table) == ['Cid', 'Ann', 'Bob']


@pytest.mark.parametrize('sortable', [True, False])
def test_setting_columns_shows_them(qtbot, sortable):
    table = QTable([], [{'a': 1, 'b': 2}], sortable=sortable)
    qtbot.addWidget(table)

    table.columns = [Column('a', use_getitem=True), Column('b', use_getitem=True)]

    assert table.horizontalHeader().count() == 2


def test_updating_an_enaml_table_does_not_warn_about_model_resets(enaml_app, qtlog):
    window = Window()
    table = Table(parent=Container(parent=window), columns=[Column('name')], items=list(PEOPLE))
    window.initialize()
    window.activate_proxy()

    table.columns = [Column('name'), Column('age')]
    table.items = [Person('Dan', 5)]

    assert [r.message for r in qtlog.records if 'ResetModel' in r.message] == []
    window.destroy()


def test_refresh_does_not_warn_about_an_invalid_range(qtbot, qtlog):
    table = make_table(qtbot)
    show(qtbot, table)

    table.refresh()

    assert [r.message for r in qtlog.records if 'invalid index range' in r.message] == []
