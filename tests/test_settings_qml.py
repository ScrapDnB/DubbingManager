"""Regression checks for the settings QML interface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    assert "Application.font.pixelSize - 1" in navigation
    assert "Math.max(10, font.pixelSize - 1)" not in navigation
    assert "SettingsPageHeader" in global_settings
    assert "SettingsPageHeader" in project_settings
    assert "backend.projectFpsDisplay" in project_settings
    assert "предварительной версии интерфейс доступен" not in global_settings
    assert 'title: qsTr("Настройки программы")' in global_settings
    assert "heading: true" in global_settings
    assert "searchEnabled: true" in global_settings
    assert "MontageSettingsPane" not in global_settings
    assert 'title: qsTr("Вид телесуфлёра")' not in global_settings
    assert 'title: qsTr("Импорт ASS")' in global_settings
    assert 'title: qsTr("Импорт SRT")' in global_settings
    assert 'title: qsTr("Импорт DOCX")' in global_settings


def test_interface_onboarding_is_first_run_only_and_reuses_ui_preferences():
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    onboarding = (
        ROOT / "qml" / "components" / "InterfaceOnboardingDialog.qml"
    ).read_text(encoding="utf-8")

    assert 'uiState.hasValue("main.width")' in main
    assert 'uiState.intValue("onboarding.interfaceVersion", 0) < 1' in main
    assert "interfaceOnboardingDialog.openForFirstRun()" in main
    assert 'qsTr("Настроить интерфейс...")' in main
    assert "function openFromSettings()" in onboarding
    assert '"main.characterCompactRows"' in onboarding
    assert '"actorColorCellFill"' in onboarding
    assert '"main.characterColumnsHidden"' in onboarding
    assert '"main.episodeTimelinePlacement"' in onboarding
    assert "configurationAccepted(" in onboarding
    assert "function previewColumnWidth(key)" in onboarding
    assert 'qsTr("Таймлайн под таблицей")' in onboarding
    assert 'qsTr("Таймлайн внизу всего окна")' in onboarding
    assert onboarding.count(
        'visible: dialog.actorColorDisplayDraft === "cell"'
    ) >= 3
    assert onboarding.count(
        "Layout.preferredHeight: dialog.windowsStyle ? 116 : 88"
    ) == 3
    assert "fontSizeMode: Text.HorizontalFit" in onboarding
    assert "height: dialog.tablePreviewRowHeight" in onboarding
    assert onboarding.count("height: dialog.tablePreviewRowHeight") == 2
    assert "onboardingTableFontMetrics.height" in onboarding
