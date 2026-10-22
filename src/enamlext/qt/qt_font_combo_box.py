from typing import TYPE_CHECKING

from atom.api import Int, Typed
from enaml.qt.qt_control import QtControl
from enaml.qt.QtGui import QFont
from enaml.qt.QtWidgets import QFontComboBox

from enamlext.widgets.font_combo_box import FontComboBox, ProxyFontComboBox

# cyclic notification guard flags
INDEX_GUARD = 0x1


class QtFontComboBox(QtControl, ProxyFontComboBox):
    """A Qt implementation of an Enaml FontComboBox."""

    #: A reference to the widget created by the proxy.
    if TYPE_CHECKING:
        # Narrowed for type checkers only; at runtime both stay optional because enaml
        # reads them while destroying proxies that were never activated.
        widget: QFontComboBox
        declaration: FontComboBox
    else:
        widget = Typed(QFontComboBox)

    # TODO: context manager
    #: Cyclic notification guard. This a bitfield of multiple guards.
    _guard = Int(0)

    # Initialization API
    def create_widget(self):
        """Create the QFontComboBox widget."""
        self.widget = QFontComboBox(self.parent_widget())

    def init_widget(self):
        """Create and initialize the underlying widget."""
        super().init_widget()
        self.widget.currentFontChanged.connect(self.on_font_changed)

    # Signal Handlers
    def on_font_changed(self, qfont: QFont):
        """The signal handler for the font changed signal."""
        if not self._guard & INDEX_GUARD:
            self.declaration.font = qfont.family()

    def set_font(self, font: str):
        self._guard |= INDEX_GUARD
        try:
            qfont = QFont()
            qfont.fromString(font)
            self.widget.setCurrentFont(qfont)
        finally:
            self._guard &= ~INDEX_GUARD
