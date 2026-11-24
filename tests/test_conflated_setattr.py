import os
import subprocess
import sys
import threading

from atom.api import Atom, Int, List, observe

import enamlext.atom
from enamlext.atom import conflated_setattr


class Model(Atom):
    x = Int()
    y = Int()
    changes = List()

    @observe('x', 'y')
    def _record(self, change):
        self.changes.append((change['name'], change['value']))


def _set_on_worker(obj, name, values):
    def burst():
        for value in values:
            conflated_setattr(obj, name, value)

    thread = threading.Thread(target=burst)
    thread.start()
    thread.join()


def test_burst_from_a_worker_is_applied_once_with_the_last_value(drain):
    model = Model()

    _set_on_worker(model, 'x', range(1, 1001))
    assert model.changes == []

    drain()
    assert model.changes == [('x', 1000)]


def test_burst_queues_a_single_call_on_the_main_thread(drain, monkeypatch):
    model = Model()
    apply_pending = enamlext.atom._apply_pending
    calls = []

    def counting_apply(key):
        calls.append(key)
        apply_pending(key)

    monkeypatch.setattr(enamlext.atom, '_apply_pending', counting_apply)

    _set_on_worker(model, 'x', range(1, 1001))
    drain()

    assert len(calls) == 1


def test_members_and_objects_are_conflated_independently(drain):
    first, second = Model(), Model()

    _set_on_worker(first, 'x', range(1, 11))
    _set_on_worker(first, 'y', range(-1, -11, -1))
    _set_on_worker(second, 'x', range(101, 111))
    drain()

    assert first.changes == [('x', 10), ('y', -10)]
    assert second.changes == [('x', 110)]


def test_a_burst_after_a_drain_is_applied(drain):
    model = Model()

    _set_on_worker(model, 'x', range(1, 6))
    drain()
    _set_on_worker(model, 'x', range(6, 11))
    drain()

    assert model.changes == [('x', 5), ('x', 10)]


def _run_in_fresh_interpreter(code, timeout=30):
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    return subprocess.run(
        [sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False, timeout=timeout
    )


_FRESH_INTERPRETER_PREAMBLE = """
import gc
import sys
import threading

from atom.api import Atom, Int, Value
from enaml.qt.qt_application import QtApplication
from qtpy.QtWidgets import QApplication

from enamlext.atom import conflated_setattr


class Model(Atom):
    x = Int()
    value = Value()


def drain():
    QApplication.instance().processEvents()
"""


def test_set_is_applied_when_enaml_drops_the_deferred_calls_of_a_racing_first_caller():
    # enaml creates the receiver of its deferred calls on first use, without a lock. When two
    # threads make the first calls, the receiver of one is replaced and its calls never run.
    # This forces that interleaving, with the conflated set on the losing side.
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
import enaml.qt.q_deferred_caller as q_deferred_caller
from enaml.application import deferred_call

other_thread_is_creating = threading.Event()
set_was_queued = threading.Event()


class ReplacesTheReceiverOfTheSet(q_deferred_caller.DeferredCaller):
    def __init__(self):
        if threading.current_thread() is other_thread:
            other_thread_is_creating.set()
            set_was_queued.wait()
        super().__init__()


q_deferred_caller.DeferredCaller = ReplacesTheReceiverOfTheSet

app = QtApplication()
model = Model()
other_thread = threading.Thread(target=deferred_call, args=(int,))
other_thread.start()
other_thread_is_creating.wait()


def set_from_a_worker():
    conflated_setattr(model, 'x', 1)
    set_was_queued.set()


setting_thread = threading.Thread(target=set_from_a_worker)
setting_thread.start()
setting_thread.join()
other_thread.join()
drain()

assert model.x == 1, model.x
"""
    )
    assert result.returncode == 0, result.stderr


def test_a_set_before_the_application_exists_does_not_block_later_sets():
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
model = Model()
try:
    conflated_setattr(model, 'x', 1)
except RuntimeError:
    pass
else:
    raise AssertionError('expected a RuntimeError without an application')

app = QtApplication()
conflated_setattr(model, 'x', 2)
drain()

assert model.x == 2, model.x
"""
    )
    assert result.returncode == 0, result.stderr


def test_replaced_value_whose_finalizer_sets_again_does_not_deadlock():
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
app = QtApplication()
model = Model()


class SetsOnFinalize:
    def __del__(self):
        conflated_setattr(model, 'x', 99)


conflated_setattr(model, 'value', SetsOnFinalize())
conflated_setattr(model, 'value', None)
drain()

assert model.x == 99, model.x
""",
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_finalizer_run_by_the_garbage_collector_mid_set_does_not_deadlock():
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
app = QtApplication()
model = Model()


class CyclicGarbage:
    def __init__(self):
        self.me = self

    def __del__(self):
        conflated_setattr(model, 'x', 7)


gc.set_threshold(1, 1, 1)
for i in range(300):
    CyclicGarbage()
    conflated_setattr(Model(), 'value', i)
gc.set_threshold(0)
gc.collect()
drain()

assert model.x == 7, model.x
""",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_set_made_while_the_first_set_is_still_preparing_its_receiver_is_applied():
    # A finalizer can run at any point of the first set, including halfway through the import
    # of the receiver's module. This forces a set at that point.
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
from qtpy.QtCore import QEvent

app = QtApplication()
model = Model()
register_event_type = QEvent.registerEventType


def set_then_register(*args):
    conflated_setattr(model, 'x', 7)
    return register_event_type(*args)


assert 'enamlext.qt.qt_main_thread' not in sys.modules
QEvent.registerEventType = set_then_register
conflated_setattr(model, 'value', 1)
QEvent.registerEventType = register_event_type
drain()

assert (model.x, model.value) == (7, 1), (model.x, model.value)
"""
    )
    assert result.returncode == 0, result.stderr


def test_sets_from_finalizers_running_at_any_point_of_other_sets_are_all_applied():
    # 300 rounds only: on Python 3.11, PySide6 6.12 drops a reference to None in every postEvent
    # and processEvents call, and the interpreter aborts once None has none left.
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
app = QtApplication()
model = Model()
finalized = 0


class CyclicGarbage:
    def __init__(self):
        self.me = self

    def __del__(self):
        global finalized
        finalized += 1
        conflated_setattr(model, 'x', finalized)


gc.set_threshold(1, 1, 1)
for i in range(300):
    CyclicGarbage()
    other = Model()
    conflated_setattr(other, 'value', i)
    drain()
    assert other.value == i, (other.value, i)
gc.set_threshold(0)
gc.collect()
drain()

assert model.x == finalized, (model.x, finalized)
""",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_a_set_left_queued_by_a_destroyed_application_does_not_block_the_next_one():
    result = _run_in_fresh_interpreter(
        _FRESH_INTERPRETER_PREAMBLE
        + """
model = Model()
app = QtApplication()
conflated_setattr(model, 'x', 1)

qapp = QApplication.instance()
app.destroy()
if hasattr(qapp, 'shutdown'):
    qapp.shutdown()
del app, qapp
gc.collect()
assert QApplication.instance() is None

app = QtApplication()
conflated_setattr(model, 'x', 2)
drain()

assert model.x == 2, model.x
"""
    )
    assert result.returncode == 0, result.stderr


def test_atom_module_imports_and_sets_without_a_qt_binding():
    # Models are also used headless, so enamlext.atom must not need Qt until a set is queued.
    result = _run_in_fresh_interpreter(
        """
import sys

for name in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy'):
    sys.modules[name] = None

from atom.api import Int

from enamlext.atom import Atom


class Model(Atom):
    x = Int().tag(conflate=True)


model = Model(x=1)
model.x = 2
assert model.x == 2, model.x
"""
    )
    assert result.returncode == 0, result.stderr
