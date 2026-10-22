import pytest
from enaml.widgets.api import Container, Window
from qtpy.QtCore import QEvent, QPoint, QPointF, QSize, Qt
from qtpy.QtGui import QColor, QMouseEvent
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QApplication

from enamlext.qt.qt_star import STAR_SIZE, StarRatingWidget
from enamlext.widgets.star import StarRating


@pytest.fixture
def widget(qtbot):
    widget = StarRatingWidget(stars=5, rating=2)
    qtbot.addWidget(widget)
    widget.resize(widget.sizeHint())
    return widget


def star_centre(index: int) -> QPoint:
    return QPoint(index * STAR_SIZE + STAR_SIZE // 2, STAR_SIZE // 2)


def hover(widget: StarRatingWidget, pos: QPoint) -> None:
    # QTest.mouseMove only warps the OS cursor when no button is held, and whether that produces a
    # move event depends on the platform (it often doesn't on CI), so deliver the event directly.
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(pos),
        QPointF(widget.mapToGlobal(pos)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, event)


def test_size_hint_fits_all_stars(widget):
    assert widget.sizeHint() == QSize(5 * STAR_SIZE, STAR_SIZE)
    widget.setStars(8)
    assert widget.sizeHint() == QSize(8 * STAR_SIZE, STAR_SIZE)


@pytest.mark.parametrize(('rating', 'expected'), [(-1, 0), (0, 0), (3, 3), (5, 5), (9, 5)])
def test_rating_is_clamped_to_star_count(widget, rating, expected):
    widget.setRating(rating)
    assert widget.rating() == expected


def test_reducing_stars_clamps_the_rating(widget):
    widget.setRating(5)
    widget.setStars(3)
    assert widget.rating() == 3


def test_clicking_a_star_sets_the_rating(widget, qtbot):
    with qtbot.waitSignal(widget.ratingChanged) as blocker:
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=star_centre(3))
    assert widget.rating() == 4
    assert blocker.args == [4]


def test_clicking_the_current_rating_clears_it(widget):
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=star_centre(1))
    assert widget.rating() == 0


def test_hover_previews_without_changing_the_rating(widget):
    hover(widget, star_centre(4))
    assert widget.hoverRating() == 5
    assert widget.rating() == 2


def test_read_only_ignores_clicks_and_keys(widget, qtbot):
    widget.setReadOnly(True)
    with qtbot.assertNotEmitted(widget.ratingChanged):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=star_centre(4))
        QTest.keyClick(widget, Qt.Key.Key_Right)
    assert widget.rating() == 2


@pytest.mark.parametrize(
    ('key', 'expected'),
    [
        (Qt.Key.Key_Right, 3),
        (Qt.Key.Key_Up, 3),
        (Qt.Key.Key_Left, 1),
        (Qt.Key.Key_Down, 1),
        (Qt.Key.Key_Home, 0),
        (Qt.Key.Key_End, 5),
        (Qt.Key.Key_4, 4),
        (Qt.Key.Key_0, 0),
    ],
)
def test_keyboard_changes_the_rating(widget, key, expected):
    QTest.keyClick(widget, key)
    assert widget.rating() == expected


def test_setting_the_same_rating_does_not_emit(widget, qtbot):
    with qtbot.assertNotEmitted(widget.ratingChanged):
        widget.setRating(2)


def test_paints_filled_and_empty_stars(widget):
    widget.setColor(QColor('#ff0000'))
    widget.setEmptyColor(QColor('#0000ff'))
    image = widget.grab().toImage()

    assert image.pixelColor(star_centre(0)).name() == '#ff0000'
    assert image.pixelColor(star_centre(1)).name() == '#ff0000'
    assert image.pixelColor(star_centre(2)).name() == '#0000ff'
    assert image.pixelColor(star_centre(4)).name() == '#0000ff'


def make_window(**kwargs) -> tuple[Window, StarRating]:
    window = Window()
    rating = StarRating(parent=Container(parent=window), **kwargs)
    window.initialize()
    window.activate_proxy()
    return window, rating


def test_declaration_clamps_rating_without_a_proxy():
    rating = StarRating(stars=4)
    rating.rating = 7
    assert rating.rating == 4
    rating.rating = -2
    assert rating.rating == 0


def test_declaration_clamps_rating_when_stars_shrink():
    rating = StarRating(stars=5, rating=5)
    rating.stars = 2
    assert rating.rating == 2


def test_proxy_syncs_declaration_and_widget(enaml_app, qtbot):
    window, rating = make_window(stars=6, rating=1, read_only=True)
    widget = rating.proxy.widget
    qtbot.addWidget(window.proxy.widget)

    assert (widget.stars(), widget.rating(), widget.isReadOnly()) == (6, 1, True)

    rating.rating = 4
    rating.stars = 3
    rating.read_only = False
    assert (widget.stars(), widget.rating(), widget.isReadOnly()) == (3, 3, False)

    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=star_centre(0))
    assert rating.rating == 1

    window.destroy()


def test_stars_are_centred_when_the_widget_is_wider_than_needed(widget):
    widget.setColor(QColor('#ff0000'))
    widget.setRating(5)
    widget.resize(5 * STAR_SIZE + 100, STAR_SIZE)
    image = widget.grab().toImage()

    assert image.pixelColor(QPoint(25, STAR_SIZE // 2)).name() != '#ff0000'
    assert image.pixelColor(QPoint(50 + STAR_SIZE // 2, STAR_SIZE // 2)).name() == '#ff0000'
    assert image.pixelColor(QPoint(50 + 4 * STAR_SIZE + STAR_SIZE // 2, STAR_SIZE // 2)).name() == '#ff0000'


def test_clicks_account_for_centring(widget):
    widget.resize(5 * STAR_SIZE + 100, STAR_SIZE)
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=QPoint(50 + 3 * STAR_SIZE + STAR_SIZE // 2, STAR_SIZE // 2))
    assert widget.rating() == 4


def test_changing_stars_relayouts_the_widget(enaml_app, qtbot):
    window, rating = make_window(stars=8, rating=3)
    qtbot.addWidget(window.proxy.widget)
    widget = rating.proxy.widget
    window.show()
    qtbot.waitExposed(window.proxy.widget)
    assert widget.width() == 8 * STAR_SIZE

    rating.stars = 4
    qtbot.waitUntil(lambda: widget.width() == 4 * STAR_SIZE)

    window.destroy()
