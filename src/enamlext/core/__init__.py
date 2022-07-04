from typing import Iterator, Callable

from enaml.widgets.main_window import MainWindow
from enaml.widgets.widget import Widget
from enaml.widgets.window import Window


def get_window(obj) -> Window:
    for parent in iter_parents(obj):
        if isinstance(parent, Window):
            return parent


def get_main_window(obj) -> MainWindow:
    for parent in iter_parents(obj):
        if isinstance(parent, MainWindow):
            return parent


def iter_parents(obj) -> Iterator[Widget]:
    while (parent := obj.parent) is not None:
        yield parent
        obj = parent


def iter_children(obj, type_=None):
    for child in getattr(obj, 'children', []):
        if type_ is None or isinstance(child, type_):
            yield child
        yield from iter_children(child, type_=type_)


def register_shortcut(obj, key_sequence: str, callback: Callable[[], None]):
    from qtpy.QtWidgets import QShortcut
    from qtpy.QtGui import QKeySequence

    widget = obj.proxy.widget

    shortcut = QShortcut(QKeySequence(key_sequence), widget)

    shortcuts = getattr(widget, '_shortcuts', [])
    shortcuts.append(shortcut)
    widget._shortcuts = shortcuts

    shortcut.activated.connect(callback)
    return shortcut


def register_widget_shortcut(obj, key_sequence, callback):
    from qtpy.QtCore import Qt

    shortcut = register_shortcut(obj, key_sequence, callback)
    shortcut.setContext(Qt.WidgetWithChildrenShortcut)
    return shortcut


def register_window_shortcut(obj, key_sequence, callback):
    from qtpy.QtCore import Qt

    shortcut = register_shortcut(get_window(obj), key_sequence, callback)
    shortcut.setContext(Qt.WindowShortcut)
    return shortcut


def register_application_shortcut(obj, key_sequence, callback):
    from qtpy.QtCore import Qt

    shortcut = register_shortcut(get_main_window(obj), key_sequence, callback)
    shortcut.setContext(Qt.ApplicationShortcut)
    return shortcut
