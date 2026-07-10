import pytest
from PySide6.QtWidgets import QApplication

from ui.video import VideoPreviewWindow


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def app():
    return _app()


def test_video_preview_opens_without_video(app):
    window = VideoPreviewWindow(
        None,
        [{"s": 1.0, "e": 2.0, "char": "Hero", "text": "Line"}],
        "1",
    )

    assert window.media_player is None
    assert window.line_table.rowCount() == 1
    assert "Видео" in window.no_video_label.text()


def test_video_preview_does_not_seek_when_sync_disabled(app):
    window = VideoPreviewWindow(
        None,
        [{"s": 1.0, "e": 2.0, "char": "Hero", "text": "Line"}],
        "1",
    )

    class FakePlayer:
        def __init__(self):
            self.positions = []
            self.played = False

        def setPosition(self, position):
            self.positions.append(position)

        def play(self):
            self.played = True

    fake_player = FakePlayer()
    window.media_player = fake_player
    window.video_sync_enabled = False

    window.seek_to_line(0, 0)

    assert fake_player.positions == []
    assert fake_player.played is False


def test_video_preview_seeks_when_sync_enabled(app):
    window = VideoPreviewWindow(
        None,
        [{"s": 1.25, "e": 2.0, "char": "Hero", "text": "Line"}],
        "1",
    )

    class FakePlayer:
        def __init__(self):
            self.positions = []
            self.played = False

        def setPosition(self, position):
            self.positions.append(position)

        def play(self):
            self.played = True

    fake_player = FakePlayer()
    window.media_player = fake_player
    window.video_sync_enabled = True

    window.seek_to_line(0, 0)

    assert fake_player.positions == [1250]
    assert fake_player.played is True
