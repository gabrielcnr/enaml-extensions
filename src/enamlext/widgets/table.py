from typing import Dict

from atom.api import Typed, ForwardTyped, List, observe, Event
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl

from enamlext.qt.qtable import DoubleClickContext  # TODO: weak design (leaking Qt details)


class ProxyTable(ProxyControl):
    """ The abstract definition of a proxy Table object.
    """
    #: A reference to the Table declaration.
    declaration = ForwardTyped(lambda: Table)

    def set_columns(self, columns):
        raise NotImplementedError

    def set_items(self, items):
        raise NotImplementedError



class Table(Control):
    """ A tabular grid/table, column-oriented, where individual items are
    displayed in individual rows, and should have the same type.
    """
    #: The columns for the table (horizontal axis/headers)
    columns = d_(List())

    #: The items to be displayed in individual rows of the table
    items = d_(List())

    #: Event fired whenever the user double clicks in a cell
    #: The payload will be a DoubleClickContext
    double_clicked = d_(Event(DoubleClickContext), writable=False)

    #: A reference to the ProxyTable object.
    proxy = Typed(ProxyTable)


    # Observers

    @observe('columns', 'items')
    def _update_proxy(self, change: Dict):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super()._update_proxy(change)
