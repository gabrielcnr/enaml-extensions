from typing import List, Any

from atom.api import Int, Typed
from enaml.qt.qt_control import QtControl

from enamlext.qt.qtable import QTable, DoubleClickContext, SelectionContext
from enamlext.qt.table.column import Column
from enamlext.qt.table.summary import TableSelectionSummary
from enamlext.widgets.table import ProxyTable

# cyclic notification guard flags
INDEX_GUARD = 0x1


class QtTable(QtControl, ProxyTable):
    """ A Qt implementation of an Enaml Table.
    """
    #: A reference to the widget created by the proxy.
    widget = Typed(QTable)

    #: Cyclic notification guard. This a bitfield of multiple guards.
    _guard = Int(0)

    # Initialization API
    def create_widget(self):
        """ Create the QTable widget.
        """
        self.widget = QTable([], parent=self.parent_widget())

    def init_widget(self):
        """ Create and initialize the underlying widget.

        """
        super().init_widget()
        d = self.declaration
        with self.widget.updating_internals():
            self.set_columns(d.columns)
            self.set_items(d.items)
            self.set_selected_items(d.selected_items)
            self.set_context_menu(d.context_menu)
            self.set_checkable(d.checkable)

        # double click action
        self.widget.on_double_click.connect(self._on_double_clicked)

        # single click selection
        self.widget.on_selection.connect(self._on_selection_changed)
        # self.widget.currentIndexChanged.connect(self.on_index_changed)

    # Signal Handlers
    def _on_double_clicked(self, context: DoubleClickContext):
        # TODO: DoubleClickContext has a lot of knowledge of Qt details - we don't want this to leak!
        self.declaration.double_clicked(context)

    def _on_selection_changed(self, context: SelectionContext):
        self.declaration.selected_items = context.selected_items
        self.declaration.selection_changed(context)

        if self.declaration.show_summary:
            self.declaration.summary = TableSelectionSummary.from_selection_context(context)

    # ProxyTable API
    def set_items(self, items: List[Any]):
        """ Set the items (rows) of the QTable.
        """
        with self.widget.updating_internals():
            self.widget.items = items

    def set_columns(self, columns: List[Column]):
        """ Set the columns of the QTable.
        """
        with self.widget.updating_internals():
            self.widget.columns = columns

    def set_selected_items(self, selected_items: List[Any]):
        pass

    def set_context_menu(self, context_menu: List):
        self.widget.context_menu = context_menu # TODO: make this a property of the QTable

    def set_checkable(self, checkable: bool) -> None:
        self.widget.checkable = checkable