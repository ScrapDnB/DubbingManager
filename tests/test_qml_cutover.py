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


def test_teleprompter_transfers_the_current_text_selection():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "selectedReplicaText" in source
    assert "textEdit.selectionStart" in source
    assert "Передать выделенное" in source


def test_teleprompter_has_a_page_scroll_mode():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "Постраничный режим" in source
    assert "followCurrentReplicaByPage" in source
    assert "ListView.NoHighlightRange" in source
    assert "pageScrollAnimation" in source
    assert "pausePageFollowAtVisibleBoundary" in source
    assert "resumePageFollowWhenBoundaryEnds" in source


def test_macos_main_window_waits_for_native_chrome_before_showing():
    source = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")

    assert "property bool startupChromeReady: !macOSStyle" in source
    assert "function showInitialWindow()" in source
    assert "property int macOSChromeHeightDelta: 0" in source
    assert "startupGeometryTimer.restart()" in source
    assert "height - macOSChromeHeightDelta" in source
    assert "id: windowsMenuResetTimer" in source
    assert "Qt.callLater(root.dismissStartupMenus)" in source


def test_main_tables_can_clear_their_selection():
    actor_panel = (ROOT / "qml" / "components" / "ActorPanel.qml").read_text(
        encoding="utf-8"
    )
    character_table = (ROOT / "qml" / "components" / "CharacterTable.qml").read_text(
        encoding="utf-8"
    )

    assert "function clearActorSelection()" in actor_panel
    assert "Keys.onEscapePressed: panel.clearActorSelection()" in actor_panel
    assert "actorsView.indexAt(" in actor_panel
    assert "rowIndex < 0" in actor_panel
    assert "id: deleteGlobalActorDialog" in actor_panel
    assert "Удалить из глобальной базы?" in actor_panel
    assert "Актёры, уже добавленные в проекты" in actor_panel
    assert "function requestProjectActorDeletion()" in actor_panel
    assert "Qt.ControlModifier" in actor_panel
    assert "Qt.MetaModifier" in actor_panel
    assert "id: deleteProjectActorsDialog" in actor_panel
    assert "Назначения этих актёров будут сняты:" in actor_panel
    assert "function clearCharacterSelection()" in character_table
    assert "Keys.onEscapePressed: table.clearCharacterSelection()" in character_table
    assert "characterView.indexAt(" in character_table
    assert "rowIndex < 0" in character_table


def test_settings_use_platform_navigation_and_shared_page_headers():
    navigation = (ROOT / "qml" / "components" / "SettingsNavigation.qml").read_text(
        encoding="utf-8"
    )
    global_settings = (
        ROOT / "qml" / "components" / "GlobalSettingsDialog.qml"
    ).read_text(encoding="utf-8")
    project_settings = (
        ROOT / "qml" / "components" / "ProjectSettingsDialog.qml"
    ).read_text(encoding="utf-8")

    assert 'text: qsTr("Разделы")' not in navigation
    assert "SettingsPageHeader" in global_settings
    assert "SettingsPageHeader" in project_settings
    assert "предварительной версии интерфейс доступен" not in global_settings
