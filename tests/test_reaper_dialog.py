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

    calls = []

    def preview_provider(
        use_video,
        use_regions,
        transliterate_actor_names,
        marker_mode
    ):
        calls.append((
            use_video,
            use_regions,
            transliterate_actor_names,
            marker_mode,
        ))
        return {
            "regions": 2 if use_regions else 0,
            "tracks": 1,
            "actors": ["Ivan Ivanov"] if transliterate_actor_names else ["Иван Иванов"],
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
    assert "Иван Иванов" in dialog._preview_label.text()
    assert dialog._preview_label.minimumHeight() == 145

    dialog._chk_regions.setChecked(False)

    assert "Регионов: 0" in dialog._preview_label.text()
    assert "Регионов не будет создано." in dialog._preview_label.text()
    assert dialog._preview_label.minimumHeight() == 145

    dialog._chk_transliterate.setChecked(True)

    assert calls[-1] == (True, False, True, "merged")
    assert "Ivan Ivanov" in dialog._preview_label.text()

    dialog._combo_marker_mode.setCurrentIndex(1)

    assert calls[-1] == (True, False, True, "source")


def test_reaper_dialog_disables_source_markers_when_unavailable(app):
    def preview_provider(
        use_video,
        use_regions,
        transliterate_actor_names,
        marker_mode
    ):
        return {
            "regions": 1,
            "tracks": 0,
            "actors": [],
            "video": False,
            "invalid_lines": 0,
            "sample_regions": [],
        }

    dialog = ReaperExportDialog(
        None,
        preview_provider=preview_provider,
        source_markers_available=False,
    )

    assert not dialog._combo_marker_mode.model().item(1).isEnabled()
    assert dialog._combo_marker_mode.currentData() == "merged"
