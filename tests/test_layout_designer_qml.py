"""Regression checks for the layout designer QML interface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_layout_designer_opens_only_from_tools():
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    settings = (
        ROOT / "qml" / "components" / "GlobalSettingsDialog.qml"
    ).read_text(encoding="utf-8")
    montage = (
        ROOT / "qml" / "components" / "MontagePreviewDialog.qml"
    ).read_text(encoding="utf-8")
    teleprompter = (
        ROOT / "qml" / "components" / "TeleprompterWindow.qml"
    ).read_text(encoding="utf-8")

    assert 'text: qsTr("Конструктор макетов…")' in main
    assert main.index('text: qsTr("Быстрый конвертер")') < main.index(
        'text: qsTr("Конструктор макетов…")'
    )
    assert "Открыть конструктор макетов…" not in settings
    assert "Открыть конструктор макетов…" not in montage
    assert "Открыть конструктор макетов…" not in teleprompter


def test_layout_designer_toolbar_cannot_consume_canvas_height():
    designer = (
        ROOT / "qml" / "components" / "LayoutDesignerWindow.qml"
    ).read_text(encoding="utf-8")
    canvas = (
        ROOT / "qml" / "components" / "LayoutDesignerCanvas.qml"
    ).read_text(encoding="utf-8")

    assert "Layout.preferredHeight: 22" in designer
    assert "Layout.minimumHeight: 260" in designer
    assert "implicitHeight: 520" in canvas


def test_layout_designer_uses_an_adaptive_canvas_without_format_presets():
    designer = (
        ROOT / "qml" / "components" / "LayoutDesignerWindow.qml"
    ).read_text(encoding="utf-8")
    canvas = (
        ROOT / "qml" / "components" / "LayoutDesignerCanvas.qml"
    ).read_text(encoding="utf-8")

    source = designer + canvas
    assert "montageLandscape" not in source
    assert "wideTeleprompter" not in source
    assert "targetAspect" not in source
    assert "A4 книжный" not in source
    assert 'qsTr("16:9")' not in source


def test_layout_designer_left_panel_keeps_controls_inside_its_width():
    designer = (
        ROOT / "qml" / "components" / "LayoutDesignerWindow.qml"
    ).read_text(encoding="utf-8")

    assert "SplitView.preferredWidth: window.structureVisible ? 320 : 300" in designer
    assert "SplitView.minimumWidth: 270" in designer
    assert designer.count("Layout.minimumWidth: 0") >= 8
    assert designer.count("Layout.preferredWidth: 1") >= 8
