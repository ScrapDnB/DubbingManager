"""Regression checks for the main QML application shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
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
    assert "Импортировать базу…" in actor_panel
    assert "Экспортировать базу…" in actor_panel
    assert "onGlobalActorBaseImportRequested" in main
    assert "onGlobalActorBaseExportRequested" in main
    assert "function clearCharacterSelection()" in character_table
    assert "Keys.onEscapePressed: table.clearCharacterSelection()" in character_table
    assert "characterView.indexAt(" in character_table
    assert "rowIndex < 0" in character_table


def test_character_numeric_columns_fit_their_sorted_headers():
    character_table = (
        ROOT / "qml" / "components" / "CharacterTable.qml"
    ).read_text(encoding="utf-8")

    assert "baseWordsColumnWidth: Math.max(58" in character_table
    assert 'text: qsTr("Строк") + " ↓"' in character_table
    assert 'text: qsTr("Реплик") + " ↓"' in character_table
    assert 'text: qsTr("Слов") + " ↓"' in character_table
