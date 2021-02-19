import threading
import time

from atom.api import Int
from enaml.qt.qt_application import QtApplication

from enamlext.atom import Atom, on_thread


def test_safe_set_without_application():
    class Model(Atom):
        value = Int()

    model = Model()
    model.safe_set("value", 12)

    assert 12 == model.value


def test_safe_set_with_application_from_main_ui_thread():
    class Model(Atom):
        value = Int()

    model = Model()

    app = QtApplication()

    model.safe_set("value", 15)
    assert 15 == model.value

    app.destroy()


def test_safe_set_with_application_from_another_thread(mocker):
    mock_deferred_call = mocker.patch("enamlext.atom.deferred_call", autospec=True)

    class Model(Atom):
        value = Int()

    model = Model()

    app = QtApplication()

    def worker(given_model):
        given_model.safe_set("value", 23)

    thread = threading.Thread(target=worker, args=(model,))
    thread.daemon = True
    thread.start()

    time.sleep(.2)

    mock_deferred_call.assert_called_once_with(
        setattr, model, "value", 23
    )

    app.destroy()


def test_on_thread(mocker):
    mock_deferred_call = mocker.patch("enamlext.atom.deferred_call", autospec=True)

    class Model(Atom):
        value = Int()

    model = Model()

    app = QtApplication()

    @on_thread
    def worker(given_model):
        given_model.safe_set("value", 19)

    worker(model)

    time.sleep(.2)

    mock_deferred_call.assert_called_once_with(
        setattr, model, "value", 19
    )

    app.destroy()
