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


def test_layout_designer_opens_only_from_settings_and_tools():
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
    assert settings.count("Открыть конструктор макетов…") == 2
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
    assert 'text: qsTr("Режим прокрутки")' in source
    assert 'text: qsTr("Обычный")' in source
    assert 'text: qsTr("Постраничный")' in source
    assert "id: scrollModeSelector" in source
    assert "systemPalette.button" in source
    assert 'Accessible.name: qsTr("Постраничный режим прокрутки")' in source
    assert 'text: qsTr("Подсвечивать каждую реплику")' in source
    assert 'visible: scrollModeSelector.pageSelected' in source
    assert 'enabled: Boolean(\n                                        window.config.page_target_highlight_enabled' in source
    assert '"page_timecode_highlight_enabled", checked' in source
    assert "function highlightCurrentReplicaAtTimecode(" in source
    assert "window.teleprompter.currentIndexNow()" in source
    assert "lastTimecodeHighlightIndex === index" in source
    assert "longReplicaTargetY(targetIndex, pageScrollMode)" in source
    assert "replicaView.highlightCurrentReplicaAtTimecode(" in source
    assert 'qsTr("Смещение REAPER (%1 с)")' in source
    assert '"reaper_offset_enabled", checked' in source
    assert "followCurrentReplicaByPage" in source
    assert "ListView.NoHighlightRange" in source
    assert "pageScrollAnimation" in source
    assert "scrollDurationMs" in source
    assert "scrollSmoothnessLevel" in source
    assert 'qsTr("Уровень плавности · %1%")' in source
    assert "5000 / 150" in source
    assert "pausePageFollowAtVisibleBoundary" in source
    assert "function resumePageFollowForReaperPosition()" in source
    assert "Ручная пауза отменена: seek REAPER" in source
    assert "forceLayout();" in source
    assert "function queuePageFollow()" in source
    assert "function queueViewportFollow()" in source
    assert "function viewportConfigSignature()" in source
    assert "lastViewportConfigSignature" in source
    assert "signature === window.lastViewportConfigSignature" in source
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
    assert "function ensureReplicaItem(index)" in source
    assert "function replicaInsideCurrentPage(index)" in source
    assert "if (!replicaInsideCurrentPage(currentIndex))" in source
    assert '"Seek REAPER внутри текущей страницы"' in source
    assert "var sourceY = clampedContentY(contentY);" in source
    assert "function longReplicaTargetY(index, pageMode)" in source
    assert "function pageFragmentStep()" in source
    assert "height - preferredHighlightBegin" in source
    assert "function followCurrentLongReplica()" in source
    assert "longReplicaScrollAnimation" in source
    assert "replicaView.followCurrentLongReplica();" in source
    assert "var renderedHeight = bounds.item.playbackHeight;" in source
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
    assert "function minimumContentY()" in source
    assert "function maximumContentY()" in source
    assert "function restoreValidContentBounds()" in source
    assert "isFinite(originY)" in source
    assert "function prefetchNextReplicaDuringGap()" in source
    assert "pageGapPrefetchIndex >= 0" in source
    assert "pageGapPrefetchIndex !== currentIndex" in source
    assert "function prepareForTimeSeek()" in source
    assert "function queueModelRefresh()" in source
    assert "retargetThreshold" in source
    assert "function startPageScroll(sourceY, targetY, targetIndex)" in source
    assert "function deferReaperFollowDuringPageTurn()" in source
    assert "function finishDeferredReaperPageFollow()" in source
    assert '"Seek REAPER отложен до конца перелистывания"' in source
    assert '"Перелистывание завершено перед seek REAPER"' in source
    assert "smoothDeferredReaperPageFollow = true" in source
    assert "if (!resumeDeferredSeekSmoothly)" in source
    assert "timeDelta >= Math.max(0.5, elapsed * 4)" in source
    assert "function episodeFinishedAtReplica(index)" in source
    assert "function finalReplicaBottomTargetY(index)" in source
    assert '"Конец серии ожидает конца перелистывания"' in source
    assert '"Конец серии: последняя реплика остаётся внизу"' in source
    assert "function scrollDurationForMove(" in source
    assert "function continuousScrollDeadline(index, bounds)" in source
    assert "function pageScrollDurationForTarget(" in source
    assert "function nextActiveReplicaStart(index)" in source
    assert "Math.pow(" in source
    assert "Math.min(1, distanceScreens), 0.65" in source
    assert "(deadline - currentTime) * 1000 - 100" in source
    assert 'limit = "дедлайн"' in source
    assert "scrollDebugDesiredDurationMs" in source
    assert "scrollDebugAvailableDurationMs" in source
    assert "scrollDebugActualDurationMs" in source
    assert "Easing.InOutCubic" in source
    assert "scrollDurationForMove(sourceY, targetY, -1)" in source
    assert 'qsTr("Окончание реплики")' in source
    assert "required property string endTime" in source
    assert "function timeRangeText(bracketed, multiline)" in source
    assert '(multiline ? " -\\n" : " - ")' in source
    assert "replicaDelegate.timeRangeText(true, false)" in source
    assert "replicaDelegate.timeRangeText(false, false)" in source
    assert "replicaDelegate.timeRangeText(false, true)" in source
    assert source.count("replicaDelegate.timeRangeText(") == 3
    assert "id: teleprompterHeader" in source
    assert "id: teleprompterHeaderDivider" in source
    assert "id: headerResizeHandler" in source
    assert "readonly property bool hideLeadingTimecodeZeros:" in source
    assert 'text.replace(/^0+:/, "")' in source
    assert "parent.height * 0.72" in source
    assert '"teleprompter.headerHeight"' in source
    assert "teleprompterSurface.height - 160" in source
    assert "initialHeight + translation.y" in source
    assert "anchors.top: teleprompterHeader.visible" in source
    assert "readonly property real teleprompterFocusY:" in source
    assert "Math.min(height, teleprompterFocusY - y)" in source
    assert "window.colors.header_bg" not in source
    assert '"Фон заголовка"' not in source
    focus_index = source.index("id: focusSlider")
    elements_index = source.index('title: qsTr("Элементы")')
    text_size_index = source.index('title: qsTr("Размер текста")')
    assert focus_index < elements_index < text_size_index
    assert "Math.min(window.scrollDurationMs, 500)" not in source
    assert "pageScrollTargetIndex === targetIndex" in source
    assert "pageScrollTargetIndex === currentIndex" in source
    assert '"Анимация к фокусу продолжается"' in source
    assert "var finalViewportTop = pageScrollAnimation.to;" in source
    assert "var animationNeedsRetarget = false;" in source
    assert "function positionReplicaExactly(index, event)" in source
    assert "function materializeLocalNavigationIndex(index)" in source
    assert "var item = itemAtIndex(index);" in source
    assert "if (item) {\n                            return item;" in source
    assert "function correctPageScrollTarget()" in source
    assert "replicaView.correctPageScrollTarget();" in source
    assert "replicaView.fadePageTargetHighlight();" in source
    assert "showPageTargetHighlight(currentIndex, targetY);" in source
    assert "function updatePageTargetHighlightGeometry(index, targetY)" in source
    assert "function targetLineHighlightGeometry(targetContentY)" in source
    assert "pageTargetHighlightLineOnly" in source
    assert "var targetY = exactPageTargetY(index);" in source
    assert "contentY = targetY;" in source
    assert 'window.teleprompter.positionOrigin === "local"' in source
    assert "Math.abs(currentIndex - previousIndex) > 1" in source
    assert "item.y - preferredHighlightBegin" in source
    assert '"Пауза: точное позиционирование следующей реплики"' in source
    assert "function showPageTargetHighlight(" in source
    assert "function fadePageTargetHighlight()" in source
    assert "pageTargetHighlightFade" in source
    assert "page_target_highlight_enabled" in source
    assert "page_target_highlight" in source
    assert "page_gap_prefetch_seconds" in source
    assert "page_gap_prefetch_delay_seconds" in source
    assert "nextStart - currentEnd < gapThreshold" in source
    assert "currentTime < currentEnd + delay" in source
    assert "Пауза: следующая реплика" in source
    assert "targetItem.y - preferredHighlightBegin" in source
    assert "onDraggingChanged:" in source
    assert "onMovementEnded: finishManualDragScroll()" in source
    assert "manualWheelReleaseTimer" in source
    assert "replicaView.beginManualDragScroll();" in source
    assert "pausePageFollowAtVisibleBoundary();" in source
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
    assert "Подсвечивать цель при перемотке" in automation_settings
    assert 'key: "page_target_highlight"' in automation_settings
    assert 'key: "header_bg"' not in automation_settings
    assert "Фон заголовка" not in automation_settings
    assert "Яркость подсветки:" in automation_settings
    assert "Fade-out (затухание):" in automation_settings
    assert "Fade-in (появление):" in automation_settings
    assert '"page_target_highlight_opacity"' in automation_settings
    assert '"page_target_highlight_fade_ms"' in automation_settings
    assert '"page_target_highlight_fade_in_ms"' in automation_settings
    assert "targetHighlightBrightnessPercent" in source
    assert "targetHighlightFadeInMs" in source
    assert "targetHighlightFadeMs" in source
    assert "id: pageTargetHighlightFadeIn" in source
    assert "duration: window.targetHighlightFadeInMs" in source
    assert "var leadSeconds = window.targetHighlightFadeInMs / 1000" in source
    assert "timecodeHighlightDeadline = targetStart" in source
    assert "duration: window.targetHighlightFadeMs" in source
    assert "Подсветка прокрутки" in source
    assert "Яркость подсветки · %1%" in source
    assert "value * 0.0044" in source
    assert "percent * 0.0044" in automation_settings
    assert "property var colorPreviewOverrides: ({})" in source
    assert "function previewColor(index, value)" in source
    assert "function clearColorPreview()" in source
    assert "onSelectedColorChanged:" in source
    assert "window.previewColor(window.colorTarget, selectedColor);" in source
    assert "onRejected:" in source
    assert "window.clearColorPreview();" in source
    assert "property string colorOriginalValue" in automation_settings
    assert "ColorDialog.DontUseNativeDialog" not in source
    assert "ColorDialog.DontUseNativeDialog" not in automation_settings
    assert "pane.setColor(pane.colorTarget, pane.colorOriginalValue)" in automation_settings


def test_teleprompter_parallel_replica_expansion_is_layout_independent():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "required property bool parallelExpandable" in source
    assert "required property var subReplicas" in source
    assert "required property string replicaKey" in source
    assert "id: parallelExpansionPanel" in source
    assert "function setReplicaExpanded(index, expanded)" in source
    assert "function beginReplicaExpansion(index)" in source
    assert "function finishReplicaExpansion(index)" in source
    assert "readonly property real playbackHeight" in source
    assert "item.playbackHeight" in source
    assert "Развернуть реплику" in source
    assert source.index("LayoutTemplateFlat {") < source.index(
        "id: parallelExpansionPanel"
    )


def test_teleprompter_settings_show_page_options_without_mode_toggle():
    source = (
        ROOT / "qml" / "components" / "TeleprompterSettingsPane.qml"
    ).read_text(encoding="utf-8")

    assert 'text: qsTr("Постраничный режим")' not in source
    assert "page_scroll_mode" not in source
    assert 'title: qsTr("Паузы в постраничном режиме")' in source
    assert "page_gap_prefetch_seconds" in source
    assert "page_gap_prefetch_delay_seconds" in source


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


def test_teleprompter_list_click_aligns_replica_to_the_top_transactionally():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )
    float_source = (ROOT / "qml" / "components" / "TeleprompterFloatWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "replicaView.queueLocalNavigation(" in source
    assert "function queueLocalNavigation(index)" in source
    assert "function startQueuedLocalNavigation()" in source
    assert "function finishLocalNavigation()" in source
    assert '"Локальная навигация завершена"' in source
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
    assert "backend.projectFpsDisplay" in project_settings
    assert "предварительной версии интерфейс доступен" not in global_settings


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


def test_character_numeric_columns_fit_their_sorted_headers():
    character_table = (
        ROOT / "qml" / "components" / "CharacterTable.qml"
    ).read_text(encoding="utf-8")

    assert "baseWordsColumnWidth: Math.max(58" in character_table
    assert 'text: qsTr("Строк") + " ↓"' in character_table
    assert 'text: qsTr("Колец") + " ↓"' in character_table
    assert 'text: qsTr("Слов") + " ↓"' in character_table


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
    assert "Не разрывать реплики параллельными репликами" in source
    assert 'id: respectExistingSeparatorsCheck' in source
    assert '"respect_existing_separators"' in source
    assert "Учитывать уже имеющиеся разделители" in source
