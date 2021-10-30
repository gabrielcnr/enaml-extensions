from atom.api import Int, Typed
from enaml.qt.qt_control import QtControl

from enamlext.qt.qtable import QTable
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
        # self.widget.currentIndexChanged.connect(self.on_index_changed)

    # Signal Handlers
    ...

    # ProxyTable API
    def set_items(self, items):
        """ Set the items (rows) of the QTable.
        """
        self.widget.items = items

    def set_columns(self, columns):
        """ Set the columns of the QTable.
        """
        self.widget.columns = columns
