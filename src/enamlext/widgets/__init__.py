try:
    import qtpy  # noqa: F401
except ImportError as exc:  # qtpy.QtBindingsNotFoundError subclasses ImportError
    # No binding is a hard dependency (as with enaml itself), so say how to pick one.
    raise ImportError(
        'enaml-extensions needs a Qt binding. Install one with an extra, e.g. '
        'pip install "enaml-extensions[pyqt6]" (or [pyside6], [pyqt5]).'
    ) from exc

import enaml
from enaml.qt.qt_factories import QT_FACTORIES

from enamlext.qt.table.column import Alignment, Column

from ._shortcuts import ask_text, ask_yes_no
from .field import Field
from .star import StarRating
from .table import Table

with enaml.imports():
    from enamlext.widgets.ipython_console import IPythonConsole

__all__ = ['Alignment', 'Column', 'Field', 'IPythonConsole', 'StarRating', 'Table', 'ask_text', 'ask_yes_no']


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
