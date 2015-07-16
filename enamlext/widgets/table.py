from enaml.core.declarative import d_

from enaml.widgets.control import Control, ProxyControl

from atom.api import ForwardTyped, List, Typed, observe, Bool


class Column(object):
    """ A Column definition for the Table/grid.
    """

    def __init__(self, title, key):
        self.title = title
        self.key = key

    def get_value(self, row):
        """ A Column knows how to extract the value from a given row.
        """
        if isinstance(row, dict):
            return row[self.key]
        else:
            return getattr(row, self.key)


class ProxyTable(ProxyControl):
    """ The abstract definition of a proxy Table object.
    """
    #: A reference to the Table declaration.
    declaration = ForwardTyped(lambda: Table)

    def set_rows(self, rows):
        raise NotImplementedError

    def set_columns(self, columns):
        raise NotImplementedError

    def set_alternate_row_colors(self, alternate_row_colors):
        raise NotImplementedError


class Table(Control):
    """ Enaml declarative control for giving a Table grid widget.
    """

    rows = d_(List())
    columns = d_(List())
    alternate_row_colors = d_(Bool(default=True))

    #: A reference to the ProxyTable implementation.
    proxy = Typed(ProxyTable)

    hug_height = 'weak'
    hug_width = 'weak'

    # Observers ---------------------------------------------------------------
    @observe('rows', 'columns', 'alternate_row_colors')
    def _update_proxy(self, change):
        """ An observer which sends the state change to the proxy.
        """
        # The superclass implementation is sufficient.
        super(Table, self)._update_proxy(change)


def table_factory():
    from enamlext.qt.qt_table import QtTable

    return QtTable


from enaml.qt.qt_factories import QT_FACTORIES

QT_FACTORIES['Table'] = table_factory
