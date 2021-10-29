from atom.api import Str, Typed, ForwardTyped, set_default
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl


class ProxyFontComboBox(ProxyControl):
    """ The abstract definition of a proxy FontComboBox object.

    """
    #: A reference to the FontComboBox declaration.
    declaration = ForwardTyped(lambda: FontComboBox)

    def set_font(self, font: str):
        raise NotImplementedError


class FontComboBox(Control):
    """ A drop-down list from which a font can be selected at a time.

    Fonts are pulled from the system.
    """
    #: The font family currently selected.
    font = d_(Str())

    #: A read only cached property which returns the list of fonts
    # fonts = d_(Property(cached=True), writable=False)

    #: A FontComboBox hugs its width weakly by default.
    hug_width = set_default('weak')

    #: A reference to the ProxyFontComboBox object.
    proxy = Typed(ProxyFontComboBox)
