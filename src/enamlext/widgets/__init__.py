from .table import Table
from .star import StarRating
from .field import Field
from ._shortcuts import ask_yes_no, ask_text

import enaml
with enaml.imports():
    from enamlext.widgets.ipython_console import IPythonConsole


from enaml.qt.qt_factories import QT_FACTORIES

# Injecting the factories to be used by the ProxyResolver
# TODO: should this be here?
def table_factory():
    from enamlext.qt.qt_table import QtTable
    return QtTable


QT_FACTORIES.update(
    Table=table_factory,
)

del QT_FACTORIES
del table_factory