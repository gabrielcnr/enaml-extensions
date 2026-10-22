#############################################################################
##
## Copyright (C) 2010 Hans-Peter Jansen <hpj@urpla.net>.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is derived from the Star Delegate example of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################
import math

from atom.api import Typed
from enaml.qt.qt_control import QtControl
from qtpy.QtCore import QPointF, QSize, Qt, Signal
from qtpy.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPolygonF
from qtpy.QtWidgets import QSizePolicy, QWidget

from enamlext.widgets.star import ProxyStarRating

STAR_SIZE = 20
DEFAULT_COLOR = QColor('#daa520')
DEFAULT_EMPTY_COLOR = QColor('#d0d0d0')


def _make_star_polygon() -> QPolygonF:
    # A unit-square five-pointed star: each step jumps 144 degrees (0.8 * pi)
    # so the outline crosses itself, and WindingFill paints the centre solid.
    points = [
        QPointF(0.5 + 0.5 * math.cos(0.8 * i * math.pi), 0.5 + 0.5 * math.sin(0.8 * i * math.pi)) for i in range(5)
    ]
    return QPolygonF(points)


STAR_POLYGON = _make_star_polygon()


class StarRatingWidget(QWidget):
    ratingChanged = Signal(int)

    def __init__(self, stars: int = 5, rating: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stars = max(stars, 0)
        self._rating = 0
        self._hover_rating: int | None = None
        self._read_only = False
        self._color = QColor(DEFAULT_COLOR)
        self._empty_color = QColor(DEFAULT_EMPTY_COLOR)
        self.setRating(rating)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def stars(self) -> int:
        return self._stars

    def setStars(self, stars: int) -> None:
        self._stars = max(stars, 0)
        self.updateGeometry()
        self.setRating(self._rating)
        self.update()

    def rating(self) -> int:
        return self._rating

    def setRating(self, rating: int) -> None:
        rating = min(max(rating, 0), self._stars)
        if rating != self._rating:
            self._rating = rating
            self.update()
            self.ratingChanged.emit(rating)

    def hoverRating(self) -> int | None:
        return self._hover_rating

    def isReadOnly(self) -> bool:
        return self._read_only

    def setReadOnly(self, read_only: bool) -> None:
        self._read_only = read_only
        self.setFocusPolicy(Qt.NoFocus if read_only else Qt.StrongFocus)
        self._set_hover_rating(None)

    def color(self) -> QColor:
        return QColor(self._color)

    def setColor(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def emptyColor(self) -> QColor:
        return QColor(self._empty_color)

    def setEmptyColor(self, color: QColor) -> None:
        self._empty_color = QColor(color)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(self._stars * STAR_SIZE, STAR_SIZE)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event: QPaintEvent) -> None:
        shown = self._rating if self._hover_rating is None else self._hover_rating
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.translate(self._x_offset(), (self.height() - STAR_SIZE) / 2)
        painter.scale(STAR_SIZE, STAR_SIZE)
        for i in range(self._stars):
            painter.setBrush(self._color if i < shown else self._empty_color)
            painter.drawPolygon(STAR_POLYGON, Qt.WindingFill)
            painter.translate(1.0, 0.0)
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._read_only:
            self._set_hover_rating(self._rating_at(event.position().x()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._read_only or event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        clicked = self._rating_at(event.position().x())
        self.setRating(0 if clicked == self._rating else clicked)
        self._set_hover_rating(None)

    def leaveEvent(self, event) -> None:
        self._set_hover_rating(None)
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._read_only:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in (Qt.Key_Right, Qt.Key_Up, Qt.Key_Plus):
            self.setRating(self._rating + 1)
        elif key in (Qt.Key_Left, Qt.Key_Down, Qt.Key_Minus):
            self.setRating(self._rating - 1)
        elif key == Qt.Key_Home:
            self.setRating(0)
        elif key == Qt.Key_End:
            self.setRating(self._stars)
        elif Qt.Key_0 <= key <= Qt.Key_9:
            self.setRating(key - Qt.Key_0)
        else:
            super().keyPressEvent(event)

    def _x_offset(self) -> float:
        return max(self.width() - self._stars * STAR_SIZE, 0) / 2

    def _rating_at(self, x: float) -> int:
        return min(max(math.ceil((x - self._x_offset()) / STAR_SIZE), 1), self._stars)

    def _set_hover_rating(self, rating: int | None) -> None:
        if rating != self._hover_rating:
            self._hover_rating = rating
            self.update()


class QtStarRating(QtControl, ProxyStarRating):
    widget = Typed(StarRatingWidget)

    def create_widget(self) -> None:
        self.widget = StarRatingWidget(parent=self.parent_widget())

    def init_widget(self) -> None:
        super().init_widget()
        d = self.declaration
        self.set_stars(d.stars)
        self.set_rating(d.rating)
        self.set_read_only(d.read_only)
        self.widget.ratingChanged.connect(self._on_rating_changed)

    def _on_rating_changed(self, rating: int) -> None:
        self.declaration.rating = rating

    def set_stars(self, stars: int) -> None:
        with self.geometry_guard():
            self.widget.setStars(stars)

    def set_rating(self, rating: int) -> None:
        self.widget.setRating(rating)

    def set_read_only(self, read_only: bool) -> None:
        self.widget.setReadOnly(read_only)
