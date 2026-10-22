import pytest
from enaml.widgets.api import Container, Window
from qtpy.QtCore import QCoreApplication, QEvent

from enamlext.widgets import StarRating, Table
from enamlext.widgets.traffic_light import TrafficLight


@pytest.mark.parametrize('declaration_cls', [Table, StarRating, TrafficLight])
def test_widget_can_be_destroyed_before_its_window_is_shown(enaml_app, declaration_cls):
    # e.g. a Conditional flipping off before the window ever activates its proxies
    window = Window()
    declaration = declaration_cls(parent=Container(parent=window))
    window.initialize()

    window.destroy()

    assert declaration.is_destroyed


@pytest.mark.parametrize('declaration_cls', [Table, StarRating, TrafficLight])
def test_widget_can_be_destroyed_after_its_window_is_shown(enaml_app, qtbot, declaration_cls):
    window = Window()
    declaration = declaration_cls(parent=Container(parent=window))
    window.initialize()
    window.activate_proxy()
    window.show()
    qtbot.waitExposed(window.proxy.widget)

    window.destroy()
    # enaml deletes the Qt window with deleteLater(); flush it so no window outlives this test.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    assert declaration.is_destroyed
