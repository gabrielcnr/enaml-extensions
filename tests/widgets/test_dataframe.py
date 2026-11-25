import gc
import threading

import enaml
import pandas as pd
import pytest
from atom.api import atomref
from enaml.core.enaml_compiler import EnamlCompiler
from enaml.core.parser import parse
from qtpy.QtCore import QCoreApplication, QEvent, QItemSelectionModel

with enaml.imports():
    from enamlext.widgets import dataframe as dataframe_module
    from enamlext.widgets.dataframe import DataFrame

VIEWS_OVERRIDING_CONVERT_ITEM = {
    'in a widget derived from DataFrame': """
from enaml.widgets.api import Container
from enamlext.widgets.dataframe import DataFrame

enamldef RowsAsTuples(DataFrame):
    convert_item => (item):
        return tuple(item)

enamldef View(Container):
    attr frame
    RowsAsTuples:
        df = frame
        selection_mode = 'rows'
""",
    'in the DataFrame of a view': """
from enaml.widgets.api import Container
from enamlext.widgets.dataframe import DataFrame

enamldef View(Container):
    attr frame
    DataFrame:
        df = frame
        selection_mode = 'rows'
        convert_item => (item):
            return tuple(item)
""",
}


@pytest.fixture
def frame():
    return pd.DataFrame({'k': ['a', 'b', 'c', 'd'], 'v': [1.0, 2.0, 3.0, 4.0]})


@pytest.fixture
def ticking(show_in_window, frame):
    return show_in_window(lambda parent: DataFrame(parent=parent, df=frame, tick_interval_ms=10))


def shown(widget):
    model = widget.proxy.widget.model()
    return [(model.data(model.index(row, 0)), model.data(model.index(row, 1))) for row in range(model.rowCount())]


def set_value(widget, frame, row, value):
    with widget.items.lock:
        frame.loc[row, 'v'] = value


def monitor_threads():
    return {thread for thread in threading.enumerate() if '_monitor_df_changes' in thread.name}


def test_filtered_ticking_dataframe_shows_a_changed_value(ticking, frame, qtbot):
    model = ticking.proxy.widget.model()
    model.set_filter(model.columns[1], '> 1')

    set_value(ticking, frame, 2, 300.0)

    qtbot.waitUntil(lambda: shown(ticking) == [('b', '2.0'), ('c', '300.0'), ('d', '4.0')], timeout=5000)


def test_filtered_ticking_dataframe_repaints_the_row_showing_the_changed_value(ticking, frame, qtbot):
    model = ticking.proxy.widget.model()
    model.set_filter(model.columns[1], '> 1')
    repainted = []
    model.dataChanged.connect(lambda top_left, bottom_right, *_: repainted.append((top_left, bottom_right)))

    set_value(ticking, frame, 2, 300.0)  # 'c', which the filter shows on the second row

    qtbot.waitUntil(lambda: bool(repainted), timeout=5000)
    ((top_left, bottom_right),) = repainted
    assert top_left.row() <= 1 <= bottom_right.row()
    assert top_left.column() <= 1 <= bottom_right.column()


def test_filtered_ticking_dataframe_keeps_the_selection_when_a_value_changes(ticking, frame, qtbot):
    widget = ticking.proxy.widget
    model = widget.model()
    model.set_filter(model.columns[1], '> 1')
    widget.selectionModel().select(model.index(2, 0), QItemSelectionModel.SelectionFlag.ClearAndSelect)  # 'd'

    set_value(ticking, frame, 2, 300.0)

    qtbot.waitUntil(lambda: ('c', '300.0') in shown(ticking), timeout=5000)
    assert [model.data(index) for index in widget.selectionModel().selectedIndexes()] == ['d']


def test_row_leaves_a_filtered_ticking_dataframe_when_its_value_stops_matching(ticking, frame, qtbot):
    widget = ticking.proxy.widget
    model = widget.model()
    model.set_filter(model.columns[1], '> 1')

    set_value(ticking, frame, 2, 0.5)

    qtbot.waitUntil(lambda: shown(ticking) == [('b', '2.0'), ('d', '4.0')], timeout=5000)
    assert widget.verticalHeader().count() == 2


def test_row_enters_a_filtered_ticking_dataframe_when_its_value_starts_matching(ticking, frame, qtbot):
    widget = ticking.proxy.widget
    model = widget.model()
    model.set_filter(model.columns[1], '> 1')

    set_value(ticking, frame, 0, 7.0)

    qtbot.waitUntil(lambda: shown(ticking) == [('a', '7.0'), ('b', '2.0'), ('c', '3.0'), ('d', '4.0')], timeout=5000)
    assert widget.verticalHeader().count() == 4


def test_destroying_a_ticking_dataframe_stops_its_monitor_thread(show_in_window, frame):
    running_before = monitor_threads()
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, tick_interval_ms=10))
    (monitor,) = monitor_threads() - running_before

    widget.root_object().destroy()

    monitor.join(timeout=5)
    assert not monitor.is_alive()


def test_destroyed_ticking_dataframe_is_freed(show_in_window, frame):
    # enaml < 0.20 hides a bound func from the garbage collector when it reuses a freed one: make the widget's one reused.
    spare = DataFrame(df=frame)
    freed_funcs = [spare._refresh_cells for _ in range(8)]
    del freed_funcs
    running_before = monitor_threads()
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, tick_interval_ms=10))
    (monitor,) = monitor_threads() - running_before
    widget_ref = atomref(widget)

    widget.root_object().destroy()
    monitor.join(timeout=5)
    # On PySide6 the Qt window keeps the widget alive until Qt deletes it.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del widget
    gc.collect()

    assert widget_ref() is None


def test_rows_selected_in_a_dataframe_become_dicts_when_selected_items_is_first_read(
    show_in_window, frame, qtbot, monkeypatch
):
    taken = []
    rows_as_dicts = dataframe_module.rows_as_dicts

    def noting_the_rows_taken(rows):
        for row in rows:
            taken.append(row)
            yield row

    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, selection_mode='rows'))
    published = []
    widget.observe('selection_changed', published.append)
    monkeypatch.setattr(
        dataframe_module, 'rows_as_dicts', lambda names, rows: rows_as_dicts(names, noting_the_rows_taken(rows))
    )

    widget.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(published), timeout=5000)

    assert taken == []
    assert widget.selected_items == frame.to_dict('records')
    assert len(taken) == 4


def test_destroyed_dataframe_with_a_selection_nothing_has_read_is_freed(show_in_window, frame, qtbot):
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, selection_mode='rows'))
    published = []
    widget.observe('selection_changed', published.append)
    widget.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(published), timeout=5000)
    published.clear()
    widget_ref = atomref(widget)

    widget.root_object().destroy()
    # On PySide6 the Qt window keeps the widget alive until Qt deletes it.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del widget
    gc.collect()

    assert widget_ref() is None


def test_setting_selected_items_selects_the_rows_of_a_dataframe(show_in_window, frame):
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, selection_mode='rows'))

    widget.selected_items = [{'k': 'c', 'v': 3.0}]

    assert [index.row() for index in widget.proxy.widget.selectionModel().selectedRows()] == [2]


def test_rows_selected_in_a_dataframe_are_published_as_dicts(show_in_window, frame, qtbot):
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, selection_mode='rows'))

    widget.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(widget.selected_items), timeout=5000)

    assert widget.selected_items == frame.to_dict('records')
    assert [type(key) for key in widget.selected_items[0]] == [str, str]


@pytest.mark.parametrize('overriding', VIEWS_OVERRIDING_CONVERT_ITEM)
def test_convert_item_overridden_on_a_dataframe_converts_its_selected_rows(overriding, show_in_window, frame, qtbot):
    namespace = {}
    exec(EnamlCompiler.compile(parse(VIEWS_OVERRIDING_CONVERT_ITEM[overriding]), '<view>'), namespace)
    view = show_in_window(lambda parent: namespace['View'](parent=parent, frame=frame))
    (widget,) = (child for child in view.traverse() if isinstance(child, DataFrame))

    widget.proxy.widget.selectAll()
    qtbot.waitUntil(lambda: bool(widget.selected_items), timeout=5000)

    assert widget.selected_items == [('a', 1.0), ('b', 2.0), ('c', 3.0), ('d', 4.0)]
