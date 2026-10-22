import os

import pytest
from enaml.qt.qt_application import QtApplication

# Run headless by default; CI and developers can still point Qt at a real display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture
def enaml_app(qapp):
    return QtApplication.instance() or QtApplication()
