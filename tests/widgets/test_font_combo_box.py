import pytest
from qtpy.QtGui import QFont, QFontInfo

from enamlext.widgets.font_combo_box import FontComboBox


def families(widget):
    return [widget.itemText(index) for index in range(widget.count())]


def is_shown_under_its_own_name(family):
    # An alias such as 'Serif' is shown as the family it stands for.
    return QFontInfo(QFont(family)).family() == family


def family_not_shown(widget):
    others = [
        family for family in families(widget) if family != widget.currentText() and is_shown_under_its_own_name(family)
    ]
    if not others:
        pytest.skip('needs two font families')
    return others[-1]


def test_setting_the_font_selects_it_in_the_widget(show_in_window):
    combo = show_in_window(lambda parent: FontComboBox(parent=parent))
    widget = combo.proxy.widget
    family = family_not_shown(widget)

    combo.font = family

    assert widget.currentText() == family


def test_font_given_up_front_is_selected(show_in_window):
    probe = show_in_window(lambda parent: FontComboBox(parent=parent))
    family = family_not_shown(probe.proxy.widget)

    combo = show_in_window(lambda parent: FontComboBox(parent=parent, font=family))

    assert combo.proxy.widget.currentText() == family


def test_choosing_a_font_in_the_widget_sets_the_font(show_in_window):
    combo = show_in_window(lambda parent: FontComboBox(parent=parent))
    widget = combo.proxy.widget
    family = family_not_shown(widget)

    widget.setCurrentIndex(families(widget).index(family))

    assert combo.font == widget.currentFont().family()
    assert combo.font != ''
