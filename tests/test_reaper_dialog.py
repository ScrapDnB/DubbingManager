import pytest
from PySide6.QtWidgets import QApplication

from ui.dialogs.reaper import ReaperExportDialog


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_reaper_dialog_updates_preview_when_region_option_changes(app, tmp_path):
    video_path = tmp_path / "episode.mov"
    video_path.write_text("video", encoding="utf-8")

    def preview_provider(use_video, use_regions):
        return {
            "regions": 2 if use_regions else 0,
            "tracks": 1,
            "actors": ["Actor One"],
            "video": use_video,
            "invalid_lines": 0,
            "sample_regions": ["Character: Line"] if use_regions else [],
        }

    dialog = ReaperExportDialog(
        str(video_path),
        preview_provider=preview_provider,
    )

    assert "Регионов: 2" in dialog._preview_label.text()
    assert "Видео: да" in dialog._preview_label.text()

    dialog._chk_regions.setChecked(False)

    assert "Регионов: 0" in dialog._preview_label.text()
    assert "Регионов не будет создано." in dialog._preview_label.text()
