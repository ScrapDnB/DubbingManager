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
    assert "rememberTransferSelection" in source
    assert "transferSelectionStart" in source
    assert "transferSelectionEnd" in source
    assert "Передать выделенное" in source


def test_teleprompter_has_a_page_scroll_mode():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "Постраничный режим" in source
    assert 'qsTr("Смещение REAPER (%1 с)")' in source
    assert '"reaper_offset_enabled", checked' in source
    assert "followCurrentReplicaByPage" in source
    assert "ListView.NoHighlightRange" in source
    assert "pageScrollAnimation" in source
    assert "scrollDurationMs" in source
    assert 'qsTr("Плавность · %1 мс")' in source
    assert "5000 / 150" in source
    assert "pausePageFollowAtVisibleBoundary" in source
    assert "function resumePageFollowForReaperPosition()" in source
    assert "Ручная пауза отменена: seek REAPER" in source
    assert "forceLayout();" in source
    assert "function queuePageFollow()" in source
    assert "function queueViewportFollow()" in source
    assert "property bool viewportFollowQueued: false" in source
    assert "onHeightChanged: queueViewportFollow()" in source
    assert "onWidthChanged: queueViewportFollow()" in source
    assert "contentHeight also changes while ListView creates" in source
    assert "&& !manualDragScroll && !dragging && !moving" in source
    assert "function scrollCurrentReplicaToFocusBoundary()" in source
    assert "function resetPageFollowState()" in source
    assert "height: replicaView.pageScrollMode ? replicaView.height : 0" in source
    assert "property bool pageFocusAlignmentActive: false" in source
    assert "property bool manualDragScroll: false" in source
    assert "var viewportBottom = sourceY + height;" in source
    assert "function currentReplicaFocusTargetY()" in source
    assert "function replicaReadingBounds(index)" in source
    assert "function longReplicaTargetY(index, pageMode)" in source
    assert "function pageFragmentStep()" in source
    assert "height - preferredHighlightBegin" in source
    assert "function followCurrentLongReplica()" in source
    assert "longReplicaScrollAnimation" in source
    assert "replicaView.followCurrentLongReplica();" in source
    assert "var renderedHeight = bounds.item.height;" in source
    assert "Math.floor((renderedHeight - 1) / step)" in source
    assert "function sourceTimedContinuousTarget(index, bounds)" in source
    assert "function pageTransitionForFragment(" in source
    assert "bounds.item.laidOutTimingGuides()" in source
    assert 'source: "ASS: конец строки " + selected.sourceId' in source
    assert 'source: guides.length > 0' in source
    assert '"визуальный fallback"' in source
    assert "positionToRectangle(" in source
    assert "pageDebugThresholdTime" in source
    assert "readonly property int debugFragmentCount" in source
    assert "including one reached by manual scrolling" in source
    assert "readonly property real debugFocusFragmentY" in source
    assert "replicaView.contentY + replicaView.preferredHighlightBegin" in source
    assert 'text: qsTr("Фрагмент %1").arg(fragmentGuide.index + 1)' in source
    assert "guides: cyan lines start at the focus line" in source
    assert "function replicaFocusTargetY(index)" in source
    assert "function prefetchNextReplicaDuringGap()" in source
    assert "function startPageScroll(sourceY, targetY, targetIndex)" in source
    assert "function positionReplicaExactly(index, event)" in source
    assert "function correctPageScrollTarget()" in source
    assert "var targetY = exactPageTargetY(index);" in source
    assert "contentY = targetY;" in source
    assert 'window.teleprompter.positionOrigin === "local"' in source
    assert "Math.abs(currentIndex - previousIndex) > 1" in source
    assert "function showPageTargetHighlight(index)" in source
    assert "function fadePageTargetHighlight()" in source
    assert "pageTargetHighlightFade" in source
    assert "page_target_highlight_enabled" in source
    assert "page_target_highlight" in source
    assert "page_gap_prefetch_seconds" in source
    assert "page_gap_prefetch_delay_seconds" in source
    assert "nextStart - currentEnd < gapThreshold" in source
    assert "currentTime < currentEnd + delay" in source
    assert "Пауза: следующая реплика" in source
    assert "contentY - preferredHighlightBegin" in source
    assert "onDraggingChanged:" in source
    assert "onMovementEnded: finishManualDragScroll()" in source
    assert "longReplicaScrollAnimation.stop();" in source
    assert "function capturePageDebug(" in source
    assert 'text: qsTr("Mock REAPER")' in source
    assert "debugSetSimulationActive" in source
    assert "debugSetReaperTime" in source
    assert "debugSimulationSpeed" in source
    assert "pageDebugTrace" in source
    assert "pageDebugRenderedHeight" in source
    assert 'toolTipText: qsTr("Переподключить REAPER")' in source
    assert "window.teleprompter.restartOsc()" in source
    assert "pageDebugButton" not in source
    assert "readonly property bool pageDebugVisible" in source
    assert "visible: window.pageDebugVisible" in source
    assert "Следовать только во время Play" in source
    assert '"sync_play_only", checked' in source
    assert 'qsTr("Смещение REAPER (%1 с)")' in source

    osc_settings = (ROOT / "qml" / "components" / "ReaperOscSettingsPane.qml").read_text(
        encoding="utf-8"
    )
    assert "Следовать только во время Play" in osc_settings
    assert '"sync_play_only", checked' in osc_settings
    assert 'title: qsTr("Синхронизация")' in osc_settings
    assert 'title: qsTr("OSC-подключение")' in osc_settings
    assert 'title: qsTr("Исходящие переходы")' in osc_settings
    assert "Показывать диагностику постраничного режима" not in osc_settings

    automation_settings = (ROOT / "qml" / "components" / "TeleprompterSettingsPane.qml").read_text(
        encoding="utf-8"
    )
    assert 'title: qsTr("Автопрокрутка")' in automation_settings
    assert "Показывать диагностику постраничного режима" in automation_settings
    assert "Считать паузой интервал от:" in automation_settings
    assert "Подтягивать следующую реплику через:" in automation_settings
    assert 'title: qsTr("Подсветка цели")' in automation_settings
    assert "Выделять реплику при перемотке" in automation_settings


def test_teleprompter_restores_following_after_manual_scroll_and_list_jump():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "function jumpToReplica(index)" in source
    assert "teleprompter.jumpToIndex(index);" in source
    assert "function resetFollowingState()" in source
    assert "function setEpisode(episode)" in source
    assert "followCurrentReplicaByPage();" in source
    assert 'window.teleprompter.positionOrigin === "reaper"' in source
    assert "if (window.teleprompter.positionOrigin === \"reaper\") {\n                replicaView.resumePageFollowForReaperPosition();" in source
    assert "Qt.callLater(function() {\n                replicaView.followCurrentReplicaByPage();" not in source


def test_teleprompter_routes_float_navigation_through_window_state():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )
    float_source = (ROOT / "qml" / "components" / "TeleprompterFloatWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "function onNavigationRequested(direction)" in source
    assert "signal navigationRequested(int direction)" in float_source
    assert "signal episodeChangeRequested(string episode)" in float_source
    assert "navigateFromOsc" not in source
    assert "oscNavigationRequested" not in source
    assert "floatWindow.navigationRequested(-1)" in float_source
    assert "floatWindow.navigationRequested(1)" in float_source


def test_teleprompter_list_click_aligns_page_mode_replica_to_the_top():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )
    float_source = (ROOT / "qml" / "components" / "TeleprompterFloatWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "replicaView.scrollCurrentReplicaToFocusBoundary();" in source
    assert "Клик: точное выравнивание реплики к фокусу" in source
    assert "signal replicaJumpRequested(int index)" in float_source
    assert "floatWindow.replicaJumpRequested(" in float_source


def test_windows_teleprompter_is_not_transient_to_the_main_window():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "transientParent: windowsStyle || !ownerWindow ? null : ownerWindow" in source


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
