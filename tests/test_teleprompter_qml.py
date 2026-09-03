"""Regression checks for the teleprompter QML interface."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    assert 'text: qsTr("Смещение REAPER")' in source
    assert '"reaper_offset_enabled", checked' in source
    assert '"reaper_offset_seconds", value / 10' in source
    assert "followCurrentReplicaByPage" in source
    assert "ListView.NoHighlightRange" in source
    assert "pageScrollAnimation" in source
    assert "scrollDurationMs" in source
    assert "scrollSmoothnessLevel" in source
    assert 'qsTr("Уровень плавности · %1%")' in source
    assert "window.behavior.scrollDurationMaxMs" in source
    assert "pausePageFollowAtVisibleBoundary" in source
    assert "function resumePageFollowForReaperPosition()" in source
    assert "Ручная пауза отменена: seek REAPER" in source
    assert "forceLayout();" in source
    assert "function queuePageFollow()" in source
    assert "function queueContinuousFollow()" in source
    assert "property bool continuousFollowQueued: false" in source
    assert "replicaView.queueContinuousFollow();" in source
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
    assert "property bool pageFocusAlignmentActive: false" in source
    assert "property bool manualDragScroll: false" in source
    assert "var viewportBottom = sourceY + height;" in source
    assert "function currentReplicaFocusTargetY()" in source
    assert "function replicaReadingBounds(index)" in source
    assert "var readingViewportHeight = Math.max(" in source
    assert "1, height - preferredHighlightBegin" in source
    assert "> readingViewportHeight + 0.5" in source
    assert "tall: item.playbackHeight > height" not in source
    assert "function ensureReplicaItem(index)" in source
    assert "function replicaInsideCurrentPage(index)" in source
    assert "if (!replicaInsideCurrentPage(currentIndex))" in source
    assert '"Seek REAPER внутри текущей страницы"' in source
    assert "var sourceY = clampedContentY(contentY);" in source
    assert "function longReplicaTargetY(index, pageMode)" in source
    assert "function pageFragmentStep()" in source
    assert "height - preferredHighlightBegin" in source
    assert "function followCurrentLongReplica()" in source
    assert "bounds.item.replicaTextBottom()" in source
    assert "cacheBuffer: Math.max(height * 2, 800)" in source
    assert "currentIndex: playbackIndex" in source
    assert "onPlaybackIndexChanged:" in source
    assert "longReplicaScrollAnimation" in source
    assert "replicaView.queueContinuousFollow();" in source
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
    assert "function startPageScroll(" in source
    assert "function acquireGapPrefetch(" in source
    assert "function releaseGapPrefetch(reason, unexpected)" in source
    assert "function retainPrefetchForForwardSeek(" in source
    assert '"Промежуточная неактивная строка"' in source
    assert '"scroll_retarget_prevented"' in source
    assert "function deferReaperFollowDuringPageTurn()" in source
    assert "function finishDeferredReaperPageFollow()" in source
    assert '"Seek REAPER отложен до конца перелистывания"' in source
    assert '"Перелистывание завершено перед seek REAPER"' in source
    assert "animateDeferredReaperPageFollow =" in source
    assert "if (!animateDeferredSeek)" in source
    assert "timeDelta >= Math.max(0.5, elapsed * 4)" in source
    assert "function episodeFinishedAtReplica(index)" in source
    assert "function finalReplicaBottomTargetY(index)" in source
    assert '"Конец серии ожидает конца перелистывания"' in source
    assert '"Конец серии: позиция сохраняется"' in source
    assert "targetY > sourceY + 0.5" in source
    assert '"final-replica", true, false' in source
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
    assert "currentTime < currentEnd" in source
    assert "function desiredScrollDurationForMove(sourceY, targetY)" in source
    assert "function scrollDistanceScreens(sourceY, targetY)" in source
    scheduler_start = source.index("function scrollDurationForMove(")
    scheduler_end = source.index("function nextActiveReplicaStart(")
    scheduler = source[scheduler_start:scheduler_end]
    assert "var distanceScreens = scrollDistanceScreens(" in scheduler
    assert "var preferredStart = currentEnd + delay;" in source
    assert "var prefetchStart = Math.min(" in source
    assert "Пауза: мало времени для плавной прокрутки" in source
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
    assert 'text: qsTr("Смещение REAPER")' in source
    assert '"reaper_offset_seconds", value / 10' in source

    osc_settings = (ROOT / "qml" / "components" / "ReaperOscSettingsPane.qml").read_text(
        encoding="utf-8"
    )
    assert "Следовать только во время Play" not in osc_settings
    assert '"sync_play_only", checked' not in osc_settings
    assert 'title: qsTr("Запуск")' in osc_settings
    assert 'title: qsTr("OSC-подключение")' in osc_settings
    assert 'title: qsTr("Исходящие переходы")' not in osc_settings
    assert "Показывать диагностику постраничного режима" not in osc_settings

    automation_settings = (ROOT / "qml" / "components" / "TeleprompterSettingsPane.qml").read_text(
        encoding="utf-8"
    )
    assert 'title: qsTr("Диагностика")' in automation_settings
    assert 'title: qsTr("Анимация подсветки")' in automation_settings
    assert "Диагностический оверлей" in automation_settings
    assert "Показывать управление записью лога" in automation_settings
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
    assert "behavior.highlightOpacityMax" in source
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


def test_smooth_scroll_mode_is_fully_removed():
    paths = [
        ROOT / "config" / "constants.py",
        ROOT / "core" / "models.py",
        ROOT / "qml" / "components" / "TeleprompterWindow.qml",
        ROOT / "ui" / "qml_backend" / "features" / "settings_bridge.py",
        ROOT / "ui" / "qml_backend" / "features" / "teleprompter_bridge.py",
        ROOT / "tools" / "teleprompter_diagnostics.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "smooth_scroll_mode" not in combined
    assert "smoothFocusMode" not in combined
    assert "smoothFocusFrameTimer" not in combined
    assert 'setMode("smooth")' not in combined
    assert 'qsTr("Плавный")' not in combined


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


def test_teleprompter_diagnostics_use_event_driven_screenshots():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "function diagnosticEventNeedsScreenshot(event)" in source
    assert 'event === "page_scroll_started"' in source
    assert 'event === "page_scroll_finished"' in source
    assert "behavior.diagnosticScreenshotThrottleMs" in source
    assert "function diagnosticScreenshotSize()" in source
    assert "behavior.diagnosticScreenshotMaxDimension" in source
    assert "diagnosticRollingFrameTimer" not in source
    assert "diagnosticRollingFramePath" not in source


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


def test_teleprompter_pauses_while_the_reading_area_is_held():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "property bool pointerHeld: false" in source
    assert "function setPointerHeld(held)" in source
    assert "onPressedChanged: replicaView.setPointerHeld(pressed)" in source
    assert "pageScrollAnimation.stop();" in source
    assert "longReplicaScrollAnimation.stop();" in source
    assert "if (replicaView.pointerHeld)" in source


def test_disabling_reaper_follow_stops_all_running_scroll_motion():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "property bool lastSyncInEnabled: true" in source
    assert "replicaView.suspendReaperFollow();" in source
    assert "function suspendReaperFollow()" in source
    assert "pageScrollAnimation.stop();" in source
    assert "longReplicaScrollAnimation.stop();" in source
    assert source.count("!Boolean(window.config.sync_in)") >= 4


def test_teleprompter_has_delayed_follow_and_optional_deadline_catch_up():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )
    settings_source = (
        ROOT / "qml" / "components" / "TeleprompterSettingsPane.qml"
    ).read_text(encoding="utf-8")

    delay_index = source.index('text: qsTr("Задержка перелистывания")')
    offset_index = source.index('text: qsTr("Смещение REAPER")')
    assert delay_index < offset_index
    assert '"scroll_delay_seconds", value / 10' in source
    assert "id: scrollDelayTimer" in source
    assert "id: pageScrollDelayTimer" in source
    assert "function pageScrollDelayReady(targetIndex, owner)" in source
    assert "function queueTimedFollow()" in source
    assert "window.scrollDeadlineEnabled" in source
    assert '"scroll_deadline_enabled", checked' in settings_source
    assert "Ускорять прокрутку, чтобы успеть к таймкоду" in settings_source


def test_teleprompter_toolbar_supports_series_and_global_search():
    source = (ROOT / "qml" / "components" / "TeleprompterWindow.qml").read_text(
        encoding="utf-8"
    )
    template_source = (
        ROOT / "qml" / "components" / "LayoutTemplateFlat.qml"
    ).read_text(encoding="utf-8")

    assert 'id: quickSearchField' in source
    assert 'text: qsTr("Поиск в текущей серии")' in source
    assert 'text: qsTr("Глобальный поиск по проекту")' in source
    assert "GlobalSearchDialog {" in source
    assert "function refreshQuickSearch(revealFirst)" in source
    assert "function navigateQuickSearch(direction)" in source
    assert "function highlightedReplicaText(value, replicaIndex)" in source
    assert "displayReplicaText: window.highlightedReplicaText(" in source
    assert "property bool replicaTextStyled: false" in template_source
