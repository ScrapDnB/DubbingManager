"""Regression checks for focused QML feature dialogs and panels."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_montage_exposes_character_only_highlight_setting():
    preview = (
        ROOT / "qml" / "components" / "MontagePreviewDialog.qml"
    ).read_text(encoding="utf-8")
    defaults = (
        ROOT / "qml" / "components" / "MontageSettingsPane.qml"
    ).read_text(encoding="utf-8")

    for source in (preview, defaults):
        assert 'qsTr("Цвета и подсветка")' in source
        assert 'qsTr("Выделять только персонажа")' in source
        assert '"highlight_character_only"' in source
        assert 'qsTr("Смягчать цвета")' in source

    for source in (preview, defaults):
        assert 'qsTr("Скрывать нули")' in source
        assert '"hide_leading_timecode_zeros"' in source
    for source in (preview, defaults):
        assert '"color_softening_level"' in source
        assert 'qsTr("Шрифт")' in source
        assert '"font_family"' in source
        assert 'Qt.fontFamilies()' in source
        assert 'from: -2' in source
        assert 'to: 2' in source
        assert 'softeningLabel' not in source
        for key in ("bold_time", "bold_char", "bold_actor", "bold_text"):
            assert f'"{key}"' in source
        assert 'qsTr("Жирный")' in source

    assert 'title: qsTr("Элементы")' in preview
    assert 'title: qsTr("Колонки")' not in preview
    assert 'layout_profiles' in defaults


def test_quick_converter_line_mode_uses_one_shared_backend_property():
    panel = (
        ROOT / "qml" / "components" / "QuickConverterPanel.qml"
    ).read_text(encoding="utf-8")
    preview = (
        ROOT / "qml" / "components" / "QuickConverterPreviewDialog.qml"
    ).read_text(encoding="utf-8")

    for source in (panel, preview):
        assert "backend.lineByLine" in source
        assert "backend.setLineByLine(checked)" in source


def test_import_settings_expose_parallel_replica_merge_option():
    source = (
        ROOT / "qml" / "components" / "ImportSettingsPane.qml"
    ).read_text(encoding="utf-8")

    assert 'id: mergeParallelCheck' in source
    assert '"merge_parallel_replicas"' in source
    assert "Не разрывать объединение параллельными строками" in source
    assert 'id: respectExistingSeparatorsCheck' in source
    assert '"respect_existing_separators"' in source
    assert "Учитывать уже имеющиеся разделители" in source


def test_project_files_exposes_guarded_legacy_format_conversion():
    source = (
        ROOT / "qml" / "components" / "ProjectFilesDialog.qml"
    ).read_text(encoding="utf-8")

    assert 'text: qsTr("Конвертировать в новый формат")' in source
    assert "dialog.projectFilesBackend.legacyMergedProject" in source
    assert "dialog.projectFilesBackend.canConvertToNewFormat" in source
    assert "dialog.projectFilesBackend.convertToNewFormat()" in source
