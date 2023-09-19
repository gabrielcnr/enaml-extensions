from atom.api import (
    Typed, ForwardTyped, Int, observe
)
from atom.typing_utils import ChangeDict

from enaml.core.declarative import d_

from enaml.widgets.control import Control, ProxyControl



class ProxyTrafficLight(ProxyControl):
    """ The abstract definition of a proxy TrafficLightWidget object.
    """
    #: A reference to the TrafficLight declaration.
    declaration = ForwardTyped(lambda: TrafficLight)

    def set_color(self, color: str) -> None:
        raise NotImplementedError

    def set_radius(self, radius: int) -> None:
        raise NotImplementedError


class TrafficLight(Control):
    """ Enaml declarative control for giving a TrafficLight widget.
    """
    color = d_(Typed(str))

    radius = d_(Int(default=20))

    #: A reference to the TrafficLight object.
    proxy = Typed(ProxyTrafficLight)

    @observe('color', 'radius')
    def _update_proxy(self, change: ChangeDict) -> None:
        super(TrafficLight, self)._update_proxy(change)


def traffic_light_factory():
    from enamlext.qt.qt_traffic_light import QtTrafficLight
    return QtTrafficLight


from enaml.qt.qt_factories import QT_FACTORIES
QT_FACTORIES['TrafficLight'] = traffic_light_factory