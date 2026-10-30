import threading

import pytest
from atom.api import Atom, Int, List, observe

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


@pytest.fixture
def drain(enaml_app, qapp):
    return qapp.processEvents


def test_burst_from_a_worker_is_applied_once_with_the_last_value(drain):
    model = Model()

    _set_on_worker(model, 'x', range(1, 1001))
    assert model.changes == []

    drain()
    assert model.changes == [('x', 1000)]


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
