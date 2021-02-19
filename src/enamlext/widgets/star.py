from atom.api import (
    Typed, ForwardTyped, Int, observe
)

from enaml.core.declarative import d_

from enaml.widgets.control import Control, ProxyControl



class ProxyStarRating(ProxyControl):
    """ The abstract definition of a proxy StarRatingWidget object.

    """
    #: A reference to the StarRating declaration.
    declaration = ForwardTyped(lambda: StarRating)

    def set_stars(self, stars):
        raise NotImplementedError

    def set_rating(self, rating):
        raise NotImplementedError



class StarRating(Control):
    """ Enaml declarative control for giving a Star Rating widget.

    """
    stars = d_(Int(default=5))
    rating = d_(Int())

    #: A reference to the ProxyStarRating object.
    proxy = Typed(ProxyStarRating)

    #--------------------------------------------------------------------------
    # Observers
    #--------------------------------------------------------------------------
    @observe('stars', 'rating')
    def _update_proxy(self, change):
        """ An observer which sends the state change to the proxy.

        """
        # The superclass implementation is sufficient.
        super(StarRating, self)._update_proxy(change)


def star_rating_factory():
    from enamlext.qt.qt_star import QtStarRating
    return QtStarRating


from enaml.qt.qt_factories import QT_FACTORIES
QT_FACTORIES['StarRating'] = star_rating_factory