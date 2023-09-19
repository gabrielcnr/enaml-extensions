from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication, QHBoxLayout, QLayout
from PyQt5.QtGui import QPixmap, QColor, QPainter, QBrush, QPen
from PyQt5.QtCore import Qt
from atom.api import Typed
from enaml.qt.qt_control import QtControl

from enamlext.widgets.traffic_light import ProxyTrafficLight


class TrafficLightWidget(QWidget):
    """
    A custom PyQt widget that represents a traffic light with red, yellow, and green lights.
    """

    def __init__(self, radius: int = 20, orientation: str = 'vertical', parent: QWidget | None = None):
        super().__init__(parent=parent)

        # Set the background color to black
        self.setStyleSheet("background-color: black;")

        # Set the radius of the circles
        self.radius = radius

        # Initialize the layout based on orientation
        if orientation == 'vertical':
            layout = QVBoxLayout()
            self.setFixedSize(self.radius * 2 + 20, self.radius * 6 + 20)
        else:
            layout = QHBoxLayout()
            self.setFixedSize(self.radius * 6 + 20, self.radius * 2 + 20)

        layout.setSpacing(0)  # Remove spacing between QLabel widgets

        # Create QLabel widgets for each light
        self.red_light = QLabel()
        self.yellow_light = QLabel()
        self.green_light = QLabel()

        # Set QLabel background to black
        for light in [self.red_light, self.yellow_light, self.green_light]:
            light.setStyleSheet("background-color: black;")

        # Add lights to layout
        layout.addWidget(self.red_light)
        layout.addWidget(self.yellow_light)
        layout.addWidget(self.green_light)

        # Set the layout
        self.setLayout(layout)

        # Turn off all lights initially
        self.set_light(None)

    def set_radius(self, new_radius: int) -> None:
        """
        Dynamically set the radius of the lights and redraw the widget.

        :param new_radius: The new radius for the lights.
        """
        self.radius = new_radius
        if isinstance(self.layout(), QVBoxLayout):
            self.setFixedSize(self.radius * 2 + 20, self.radius * 6 + 20)
        else:
            self.setFixedSize(self.radius * 6 + 20, self.radius * 2 + 20)
        self.set_light(None)  # Force a redraw with the new radius
        self.update()  # Force a repaint of the widget

    def set_light(self, color: str) -> None:
        """
        Set the light to the given color ('red', 'yellow', 'green') or turn off all lights (None).

        :param color: The color of the light to turn on, or None to turn off all lights.
        """
        # Define the off and on colors
        off_color = QColor(128, 128, 128)
        on_colors = {
            'red': QColor(255, 0, 0),
            'yellow': QColor(255, 255, 0),
            'green': QColor(0, 255, 0)
        }

        # Turn off all lights
        self._set_light_color(self.red_light, off_color)
        self._set_light_color(self.yellow_light, off_color)
        self._set_light_color(self.green_light, off_color)

        # Turn on the selected light
        if color in on_colors:
            selected_light = getattr(self, f"{color}_light")
            self._set_light_color(selected_light, on_colors[color])

    def _set_light_color(self, label: QLabel, color: QColor) -> None:
        """
        Set the background color of a QLabel to represent a light.

        :param label: The QLabel to modify.
        :param color: The QColor to set.
        """
        pixmap = QPixmap(self.radius * 2, self.radius * 2)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(0, 0, self.radius * 2, self.radius * 2)
        painter.end()

        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)


class QtTrafficLight(QtControl, ProxyTrafficLight):
    """ A Qt implementation of an Enaml ProxyTrafficLight.
    """
    #: A reference to the widget created by the proxy.
    widget = Typed(TrafficLightWidget)

    # --------------------------------------------------------------------------
    # Initialization API
    # --------------------------------------------------------------------------
    def create_widget(self):
        """ Create the underlying TrafficLightWidget object.
        """
        d = self.declaration
        self.widget = TrafficLightWidget(radius=d.radius, parent=self.parent_widget())

    def init_widget(self):
        """ Initialize the underlying widget.
        """
        super().init_widget()
        d = self.declaration
        self.set_color(d.color)

    # --------------------------------------------------------------------------
    # ProxyTrafficLight API
    # --------------------------------------------------------------------------
    def set_color(self, color: str | None) -> None:
        self.widget.set_light(color)

    def set_radius(self, radius: int) -> None:
        self.widget.set_radius(radius)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    main_widget = QWidget()
    main_layout = QVBoxLayout()

    widget = TrafficLightWidget(radius=10, orientation='horizontal')
    main_layout.addWidget(widget)

    button_layout = QHBoxLayout()

    for color in ['red', 'yellow', 'green', None]:
        button = QPushButton(f"Turn {color}" if color else "Turn off")
        button.clicked.connect(lambda checked, color=color: widget.set_light(color))
        button_layout.addWidget(button)

    main_layout.addLayout(button_layout)
    main_widget.setLayout(main_layout)
    main_widget.show()

    sys.exit(app.exec_())
