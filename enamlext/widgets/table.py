from builtins import str
from builtins import object
from enaml.core.declarative import d_

from enaml.widgets.control import Control, ProxyControl

from atom.api import ForwardTyped, List, Typed, observe, Bool, Enum, Value


class Column(object):
    """ A Column definition for the Table/grid.
    """

    def __init__(self, title, key, formatter=None, align='left'):
        self.title = title
        self.key = key
        self.formatter = formatter
        self.align = align

    def get_value(self, row):
        """ A Column knows how to extract the value from a given row.
        """
        raw_value = self.get_raw_value(row)
        return self.prepare(raw_value)

    def get_raw_value(self, row):
        """ A Column knows how to extract the value from a given row.
        """
        if callable(self.key):
            return self.key(row)
        else:
            if isinstance(row, (dict, list, tuple)):
                return row[self.key]
            else:
                return getattr(row, self.key)

    def prepare(self, raw_value):
        if self.formatter is not None:
            return self.formatter(raw_value)
        else:
            return str(raw_value)


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

    def set_select_mode(self, select_mode):
        raise NotImplementedError

    def set_stretch_last_column(self, stretch_last_column):
        raise NotImplementedError

    def set_selected_rows(self, rows):
        raise NotImplementedError

    def set_row_style_callback(self, row_style_callback):
        raise NotImplementedError


class Table(Control):
    """ Enaml declarative control for giving a Table grid widget.
    """

    rows = d_(List())
    columns = d_(List())
    selected_rows = d_(List())
    alternate_row_colors = d_(Bool(default=True))
    stretch_last_column = d_(Bool())
    select_mode = d_(
        Enum('single_row', 'multi_rows', 'single_cell', 'multi_cells', 'none'))

    row_style_callback = d_(Value())

    #: A reference to the ProxyTable implementation.
    proxy = Typed(ProxyTable)

    hug_height = 'weak'
    hug_width = 'weak'

    # Observers ---------------------------------------------------------------
    @observe('rows', 'columns', 'alternate_row_colors', 'select_mode',
             'stretch_last_column', 'selected_rows', 'row_style_callback')
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
