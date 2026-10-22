from atom.api import Bool, ForwardTyped, Int, Typed, observe, set_default
from enaml.core.declarative import d_
from enaml.qt.qt_factories import QT_FACTORIES
from enaml.widgets.control import Control, ProxyControl


class ProxyStarRating(ProxyControl):
    declaration = ForwardTyped(lambda: StarRating)

    def set_stars(self, stars: int) -> None:
        raise NotImplementedError

    def set_rating(self, rating: int) -> None:
        raise NotImplementedError

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError


class StarRating(Control):
    """A row of clickable stars; ``rating`` is always kept within ``0..stars``."""

    stars = d_(Int(5))
    rating = d_(Int())
    read_only = d_(Bool(False))

    hug_width = set_default('strong')
    hug_height = set_default('strong')

    proxy = Typed(ProxyStarRating)

    def _post_validate_stars(self, old: int, new: int) -> int:
        return max(new, 0)

    def _post_validate_rating(self, old: int, new: int) -> int:
        return min(max(new, 0), self.stars)

    def _observe_stars(self, change: dict) -> None:
        if self.rating > self.stars:
            self.rating = self.stars

    @observe('stars', 'rating', 'read_only')
    def _update_proxy(self, change: dict) -> None:
        super()._update_proxy(change)


def star_rating_factory() -> type[ProxyStarRating]:
    from enamlext.qt.qt_star import QtStarRating

    return QtStarRating


QT_FACTORIES['StarRating'] = star_rating_factory
