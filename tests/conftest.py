import os

import pytest
from enaml.qt.qt_application import QtApplication
from enaml.widgets.api import Container, Window
from qtpy.QtCore import QCoreApplication, QEvent

# Run headless by default; CI and developers can still point Qt at a real display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture
def enaml_app(qapp):
    return QtApplication.instance() or QtApplication()


@pytest.fixture
def drain(enaml_app, qapp):
    return qapp.processEvents


@pytest.fixture
def show_in_window(enaml_app, qtbot):
    windows = []

    def show(make_widget):
        window = Window()
        windows.append(window)
        widget = make_widget(Container(parent=window))
        window.initialize()
        window.activate_proxy()
        window.show()
        qtbot.waitExposed(window.proxy.widget)
        return widget

    yield show
    for window in windows:
        if not window.is_destroyed:
            window.destroy()
    # enaml deletes the Qt window with deleteLater(); flush it so no window outlives the test.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
