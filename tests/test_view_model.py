import threading

from atom.api import Atom, Int, List, Str, Typed

from enamlext.view_model import ViewModel


def test_view_model_subclassing(mocker):
    mock_deferred_call = mocker.patch('enamlext.view_model.deferred_call', autospec=True)

    class Controller(Atom):
        orders = List()
        other = Str()

    class OrderViewModel(ViewModel):
        controller = Typed(Controller)
        orders = List().tag(bind='controller.orders')  # bound to the view - set with deferred_call
        yet_another = Str()

    controller = Controller()
    view_model = OrderViewModel(controller=controller)

    controller.orders = ['Order1', 'Order2']
    controller.other = 'other'
    view_model.yet_another = 'yet_another'

    mock_deferred_call.assert_has_calls(
        [
            # set controller
            mocker.call(setattr, view_model, 'orders', []),
            # set controller.orders (blank)
            mocker.call(setattr, view_model, 'orders', []),
            # finally the set controller.orders with orders
            mocker.call(setattr, view_model, 'orders', ['Order1', 'Order2']),
        ]
    )


class Controller(Atom):
    x = Int()


class ConflatingViewModel(ViewModel):
    controller = Typed(Controller)
    x = Int().tag(bind='controller.x', conflate=True)
    applied = List()

    def _observe_x(self, change):
        self.applied.append(change['value'])


def _write_on_worker(controller, values):
    def burst():
        for value in values:
            controller.x = value

    thread = threading.Thread(target=burst)
    thread.start()
    thread.join()


def test_view_model_conflate_tag_applies_a_burst_once(enaml_app, qapp):
    controller = Controller()
    view_model = ConflatingViewModel(controller=controller)
    qapp.processEvents()
    view_model.applied = []

    _write_on_worker(controller, range(1, 1001))
    qapp.processEvents()

    assert view_model.applied == [1000]


def test_view_model_conflate_tag_skips_refresh_without_controller(enaml_app, qapp):
    view_model = ConflatingViewModel()
    view_model.controller = None
    qapp.processEvents()

    assert view_model.applied == []
