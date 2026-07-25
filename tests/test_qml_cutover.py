"""Regression checks for the QML-only application cutover."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_widgets_entry_points_are_absent():
    legacy_paths = [
        ROOT / "main.py",
        ROOT / "ui" / "main_window.py",
        ROOT / "ui" / "main_window_ui.py",
        ROOT / "ui" / "controllers",
        ROOT / "ui" / "dialogs",
        ROOT / "ui" / "models",
        ROOT / "ui" / "widgets",
        ROOT / "ui" / "preview.py",
        ROOT / "ui" / "teleprompter.py",
        ROOT / "ui" / "video.py",
        ROOT / "utils" / "web_bridge.py",
    ]

    assert not [path for path in legacy_paths if path.exists()]


def test_production_python_does_not_import_qt_widgets():
    source_roots = [
        ROOT / "application",
        ROOT / "core",
        ROOT / "services",
        ROOT / "ui",
        ROOT / "utils",
    ]
    offenders = []
    for source_root in source_roots:
        for path in source_root.rglob("*.py"):
            if "PySide6.QtWidgets" in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(ROOT))

    assert offenders == []


def test_packaging_uses_only_the_qml_entry_point():
    spec = (ROOT / "dubbing_manager.spec").read_text(encoding="utf-8")

    assert "entry_point = 'qml_main.py'" in spec
    assert "'PySide6.QtWidgets'" not in spec
    assert "'ui.main_window'" not in spec
    assert "'ui.dialogs'" not in spec
