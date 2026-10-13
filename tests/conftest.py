"""Keep one GUI-capable Qt application for the entire test session."""

import os

import pytest
from PySide6.QtGui import QGuiApplication


@pytest.fixture(scope="session", autouse=True)
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance() or QGuiApplication([])
    assert isinstance(app, QGuiApplication)
    yield app
