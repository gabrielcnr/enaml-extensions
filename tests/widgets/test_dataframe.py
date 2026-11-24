import threading

import enaml
import pandas as pd
import pytest
from qtpy.QtCore import QItemSelectionModel

with enaml.imports():
    from enamlext.widgets.dataframe import DataFrame


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


def test_setting_selected_items_selects_the_rows_of_a_dataframe(show_in_window, frame):
    widget = show_in_window(lambda parent: DataFrame(parent=parent, df=frame, selection_mode='rows'))

    widget.selected_items = [{'k': 'c', 'v': 3.0}]

    assert [index.row() for index in widget.proxy.widget.selectionModel().selectedRows()] == [2]
