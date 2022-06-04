from atom.api import Atom, List, Str, Typed
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

    mock_deferred_call.assert_has_calls([
        # set controller
        mocker.call(setattr, view_model, 'orders', []),
        # set controller.orders (blank)
        mocker.call(setattr, view_model, 'orders', []),
        # finally the set controller.orders with orders
        mocker.call(setattr, view_model, 'orders', ['Order1', 'Order2']),
   ])