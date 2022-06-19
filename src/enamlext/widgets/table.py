from typing import Any, Dict

from atom.api import Typed, ForwardTyped, List, Bool, observe, Event, Value, Enum
from atom.api import Dict as AtomDict
from atom.atom import set_default
from enaml.core.declarative import d_, d_func
from enaml.widgets.control import Control, ProxyControl

from enamlext.qt.qtable import DoubleClickContext, SelectionContext  # TODO: weak design (leaking Qt details)
from enamlext.qt.table.summary import TableSelectionSummary


ColumnID = str
ColumnKwarg = str
ColumnHint = Dict[ColumnKwarg, Any]
ColumnHints = Dict[ColumnID, ColumnHint]


class ProxyTable(ProxyControl):
    """ The abstract definition of a proxy Table object.
    """
    #: A reference to the Table declaration.
    declaration = ForwardTyped(lambda: Table)

    def set_columns(self, columns):
        raise NotImplementedError

    def set_items(self, items):
        raise NotImplementedError

    def set_selected_items(self, selected_items):
        raise NotImplementedError

    def set_context_menu(self, context_menu):
        raise NotImplementedError

    def set_checkable(self, checkable: bool) -> None:
        raise NotImplementedError

    def refresh_summary(self) -> None:
        raise NotImplementedError

    def set_hints(self, hints: ColumnHints) -> None:
        raise NotImplementedError

    def set_selection_mode(self, selection_mode: str) -> None:
        raise NotImplementedError


class Table(Control):
    """ A tabular grid/table, column-oriented, where individual items are
    displayed in individual rows, and should have the same type.
    """
    #: The columns for the table (horizontal axis/headers)
    columns = d_(List())

    #: The items to be displayed in individual rows of the table
    # items = d_(Instance((Sequence, np.ndarray), factory=list))
    items = d_(Value(factory=list))

    #: Dict of column hints to get passed to Column objects
    # in the case of they are being auto-generated
    hints = d_(AtomDict())

    #: The items that are currently selected on the table # TODO: how to distinguish when mode=cell
    selected_items = d_(List())

    #: Event fired whenever the user double clicks in a cell
    #: The payload will be a DoubleClickContext
    double_clicked = d_(Event(DoubleClickContext), writable=False)

    #: Event fired whenever the selection in the table changes
    selection_changed = d_(Event(SelectionContext), writable=False)

    #: A reference to the ProxyTable object.
    proxy = Typed(ProxyTable)

    # Tables expand freely in height and width by default.
    hug_width = set_default('ignore')
    hug_height = set_default('ignore')

    # Context Menu
    context_menu = d_(List())

    # Flag controlling if the user can check/tick items on the table
    checkable = d_(Bool())

    # Flag controlling if the table will have a summary label displayed at the bottom/footer
    show_summary = d_(Bool())

    # Only calculate summary when show_summary is True
    summary = d_(Typed(TableSelectionSummary))

    # Selection mode and behaviour
    selection_mode = d_(Enum('cell', 'cells', 'row', 'rows'))

    # Observers

    @observe("columns",
             "items",
             "selected_items",
             "context_menu",
             "checkable",
             "show_summary",
             "hints",
             "selection_mode",
             )
    def _update_proxy(self, change: Dict):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super()._update_proxy(change)

    @d_func
    def refresh(self) -> None:
        if self.initialized:
            self.proxy.widget.refresh()