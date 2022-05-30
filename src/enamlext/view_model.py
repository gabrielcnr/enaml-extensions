from operator import attrgetter
from typing import Dict

from atom.api import Atom
from atom.atom import AtomMeta, observe
from atom.catom import Member
from atom.typing_utils import ChangeDict
from enaml.application import deferred_call


def _iter_atom_members(dct: Dict):
    for k, v in dct.items():
        if issubclass(type(v), Member):
            yield k, v


def _create_refresh_method(name: str, bind: str):
    first_part, _ = bind.split('.')
    def _refresh(self, change: ChangeDict) -> None:
        if attrgetter(first_part)(self) is not None:
            deferred_call(setattr, self, name, attrgetter(bind)(self))
    _refresh.__name__ = f'_refresh_{name}'
    return observe(bind, first_part)(_refresh)


class ViewModelMeta(AtomMeta):
    def __new__(metacls, name, bases, dct):
        for name, value in _iter_atom_members(dct.copy()):
            if value.metadata and (bind := value.metadata.get('bind')):
                refresh_func = _create_refresh_method(name, bind)
                dct[f'_refresh_{name}'] = refresh_func

        return super().__new__(metacls, name, bases, dct)


class ViewModel(Atom, metaclass=ViewModelMeta):
    """
    Base class for models that are directly bound to an Enaml view.

    An example:

    Suppose you have a Controller with some business logic like:

    class Controller(Atom):
        orders = List()

    and you have a view model like:

    class Model(Atom):
        controller = Typed(Controller)
        orders = List()

        @observe('controller.orders')
        def _refresh_orders(self, change):
            deferred_call(setattr, self, 'orders', self.controller.orders)

    and then in your enaml UI you have:

    enamldef OrdersWidget(Container):
        Table:
            items << model.orders

    So, basically, for every member like 'orders' above you would have to write
    its own wrapper method ensuring that the refresh of the UI is taken care via
    deferred calls. That's a lot of boilerplate.

    Now compare with:

    class Controller(Atom):
        orders = List()

    class Model(ViewModel):
        controller = Typed(Controller)
        orders = List().tag(bind='controller.orders')


    Job done! The @observe methods will be automatically generated on class initialization,
    and they will ensure that anything that gets set and is bound to a control in the UI
    will be set using deferred_call.
    """
