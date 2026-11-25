from collections.abc import Iterable
from typing import Any

from atom.api import Bool, Enum, Event, ForwardTyped, List, Typed, Value, observe
from atom.api import Dict as AtomDict
from atom.atom import set_default
from atom.typing_utils import ChangeDict
from enaml.core.declarative import d_, d_func
from enaml.widgets.control import Control, ProxyControl

from enamlext.qt.qtable import DoubleClickContext, SelectionContext  # TODO: weak design (leaking Qt details)
from enamlext.qt.table.summary import TableSelectionSummary

ColumnID = str
ColumnKwarg = str
ColumnHint = dict[ColumnKwarg, Any]
ColumnHints = dict[ColumnID, ColumnHint]


class ProxyTable(ProxyControl):
    """The abstract definition of a proxy Table object."""

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

    def set_sortable(self, sortable: bool) -> None:
        raise NotImplementedError

    def refresh_summary(self) -> None:
        raise NotImplementedError

    def set_hints(self, hints: ColumnHints) -> None:
        raise NotImplementedError

    def set_selection_mode(self, selection_mode: str) -> None:
        raise NotImplementedError


class _UnreadItems(list):
    """Stands in for the selected items until something reads them; a list, to be the old value of a change."""

    def __init__(self, items: Iterable[Any]):
        super().__init__()
        self._items: Iterable[Any] | None = items

    def read(self) -> None:
        items, self._items = self._items, None
        if items is not None:
            self[:] = items


def _feeds_an_enaml_operator(table: 'Table', name: str) -> bool:
    """Whether a `::`, `>>` or `:=` is bound to the member, on the table or on an alias of it."""
    try:
        engine = table._d_engine
        if engine is None:
            return False
        handlers = engine._handlers.get(name)
        return handlers is not None and bool(handlers.write_pairs)
    except AttributeError:  # an enaml that keeps its operators another way
        return True


class Table(Control):
    """A tabular grid/table, column-oriented, where individual items are
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

    # Flag controlling if the user can sort items by clicking on a column header on the table
    sortable = d_(Bool(default=True))

    # Flag controlling if the table will have a summary label displayed at the bottom/footer
    show_summary = d_(Bool())

    # Only calculate summary when show_summary is True
    summary = d_(Typed(TableSelectionSummary))

    # Selection mode and behaviour
    selection_mode = d_(Enum('cell', 'cells', 'row', 'rows'))

    # Observers

    @observe(
        'columns',
        'items',
        'selected_items',
        'context_menu',
        'checkable',
        'sortable',
        'show_summary',
        'hints',
        'selection_mode',
    )
    def _update_proxy(self, change: ChangeDict):
        """An observer which sends state change to the proxy."""
        # The superclass handler implementation is sufficient.
        super()._update_proxy(change)

    def _set_selected_items_from_view(self, items: Iterable[Any]) -> None:
        """Make `items`, which the view already shows as selected, the selected items."""
        if self._selected_items_are_watched():
            self.selected_items = list(items)
        else:
            # Nothing is to be told, and listing a big selection that nothing reads takes seconds: read them when asked.
            self.get_member('selected_items').set_slot(self, _UnreadItems(items))

    def _selected_items_are_watched(self) -> bool:
        return (
            # a subclass gave the member observers or hooks of its own
            self.get_member('selected_items') is not Table.selected_items
            or type(self)._update_proxy is not Table._update_proxy
            or self.has_observers('selected_items')
            or _feeds_an_enaml_operator(self, 'selected_items')
        )

    def _post_getattr_selected_items(self, value: list[Any]) -> list[Any]:
        if isinstance(value, _UnreadItems):
            value.read()
            member = self.get_member('selected_items')
            value = member.do_full_validate(self, None, value)
            member.set_slot(self, value)
        return value

    def _post_validate_selected_items(self, old: list[Any] | None, new: list[Any]) -> list[Any]:
        if isinstance(old, _UnreadItems):
            old.read()  # atom compares it with the new items to tell whether they changed
        return new

    @d_func
    def refresh(self) -> None:
        if self.initialized and self.proxy is not None:
            self.proxy.widget.refresh()
