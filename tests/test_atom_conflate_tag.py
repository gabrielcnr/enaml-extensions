import os
import pickle
import subprocess
import sys
import threading

from atom.api import Int, List, observe

import enamlext.atom
from enamlext.atom import Atom
from enamlext.view_model import ViewModel


class Model(Atom):
    x = Int().tag(conflate=True)
    plain = Int()
    changes = List()

    @observe('x', 'plain')
    def _record(self, change):
        self.changes.append((change['name'], change['value']))


def _on_worker(func):
    thread = threading.Thread(target=func)
    thread.start()
    thread.join()


def _assign_on_worker(obj, name, values):
    def burst():
        for value in values:
            setattr(obj, name, value)

    _on_worker(burst)


def test_assignments_from_a_worker_are_applied_once_with_the_last_value(drain):
    model = Model()

    _assign_on_worker(model, 'x', range(1, 1001))
    assert model.changes == []

    drain()
    assert model.changes == [('x', 1000)]


def test_assignment_on_the_main_thread_is_immediate(drain):
    model = Model()

    model.x = 5

    assert model.x == 5


def test_untagged_member_of_a_conflating_class_is_set_directly_from_a_worker(drain):
    model = Model()

    _assign_on_worker(model, 'plain', [1, 2, 3])

    assert model.changes == [('plain', 1), ('plain', 2), ('plain', 3)]


def test_main_thread_assignment_is_not_overwritten_by_an_older_worker_value(drain):
    model = Model()

    _assign_on_worker(model, 'x', [100])
    model.x = 200
    drain()

    assert model.x == 200


def test_worker_assignment_after_a_main_thread_one_wins(drain):
    model = Model()

    model.x = 200
    _assign_on_worker(model, 'x', [100])
    drain()

    assert model.x == 100


def test_safe_set_and_assignment_from_a_worker_keep_their_order(drain):
    model = Model()

    def write():
        model.safe_set('x', 1)
        model.x = 2

    _on_worker(write)
    drain()

    assert model.x == 2


class Child(Model):
    y = Int().tag(conflate=True)

    @observe('y')
    def _record_y(self, change):
        self.changes.append((change['name'], change['value']))


def test_subclass_conflates_inherited_and_own_members(drain):
    child = Child()

    _assign_on_worker(child, 'x', range(1, 11))
    _assign_on_worker(child, 'y', range(-1, -11, -1))
    drain()

    assert child.changes == [('x', 10), ('y', -10)]


class Untagged(Model):
    x = Int()


def test_subclass_redefining_a_member_without_the_tag_stops_conflating_it(drain):
    untagged = Untagged()

    _assign_on_worker(untagged, 'x', [1, 2])

    assert untagged.x == 2


class TaggedViewModel(ViewModel):
    x = Int().tag(conflate=True)


def test_view_model_member_tagged_without_bind_is_conflated(drain):
    view_model = TaggedViewModel()

    _assign_on_worker(view_model, 'x', range(1, 11))
    assert view_model.x == 0

    drain()
    assert view_model.x == 10


def test_view_model_subclass_keeps_its_class_name():
    assert TaggedViewModel.__name__ == 'TaggedViewModel'


def test_last_worker_assignment_is_applied_while_the_main_thread_keeps_draining():
    # Fresh interpreter: the tight thread switching must not leak into other tests.
    code = """
import sys
import threading

from atom.api import Int
from enaml.qt.qt_application import QtApplication
from qtpy.QtWidgets import QApplication

from enamlext.atom import Atom

sys.setswitchinterval(1e-6)


class Model(Atom):
    x = Int().tag(conflate=True)


app = QtApplication()
process_events = QApplication.instance().processEvents
model = Model()
last = 20_000


def write():
    for value in range(1, last + 1):
        model.x = value


worker = threading.Thread(target=write)
worker.start()
while worker.is_alive():
    process_events()
worker.join()
process_events()

assert model.x == last, model.x
"""
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run(
        [sys.executable, '-c', code], capture_output=True, text=True, env=env, check=False, timeout=60
    )
    assert result.returncode == 0, result.stderr


class Audited(Atom):
    x = Int().tag(conflate=True)
    audit = List()

    def __setattr__(self, name, value):
        if name == 'x':
            self.audit.append(value)
        super().__setattr__(name, value)


def test_custom_setattr_of_a_conflating_class_sees_only_the_applied_value(drain):
    audited = Audited()

    _assign_on_worker(audited, 'x', range(1, 11))
    drain()

    assert audited.audit == [10]


def test_constructor_arguments_on_a_worker_are_set_before_the_constructor_returns(drain):
    built = []

    _on_worker(lambda: built.append(Model(x=5).x))

    assert built == [5]


class SetsInInit(Atom):
    x = Int().tag(conflate=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.x = 7


def test_members_set_inside_init_on_a_worker_are_set_before_the_constructor_returns(drain):
    built = []

    _on_worker(lambda: built.append(SetsInInit().x))

    assert built == [7]


def test_unpickling_on_a_worker_restores_members_before_it_returns(drain):
    pickled = pickle.dumps(Model(x=5))
    restored = []

    _on_worker(lambda: restored.append(pickle.loads(pickled).x))

    assert restored == [5]


def test_observer_fired_while_building_on_a_worker_still_conflates_other_objects(drain):
    shared = Model()

    class Notifier(Atom):
        value = Int().tag(conflate=True)

        def _observe_value(self, change):
            shared.x = change['value']

    _on_worker(lambda: Notifier(value=3))
    assert shared.changes == []

    drain()
    assert shared.changes == [('x', 3)]


def test_value_assigned_by_a_worker_while_an_older_one_is_being_applied_is_kept(drain, monkeypatch):
    model = Model()
    _assign_on_worker(model, 'x', [1])

    # Forces the interleaving: the worker assigns after the main thread took the queued 1
    # and before it sets it.
    is_gui_thread = enamlext.atom._is_gui_thread
    interleaved = []

    def assign_from_a_worker_first(app):
        if not interleaved and threading.current_thread() is threading.main_thread():
            interleaved.append(True)
            _assign_on_worker(model, 'x', [2])
        return is_gui_thread(app)

    monkeypatch.setattr(enamlext.atom, '_is_gui_thread', assign_from_a_worker_first)
    drain()
    drain()

    assert interleaved
    assert model.x == 2
