pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

NativeDialogWindow {
    id: window
    objectName: "teleprompterWindow"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    property int actorMarkerShape: 0
    property int actorMarkerSize: 0
    readonly property var teleprompter: appBridge.teleprompter

    modal: false
    title: qsTr("Телесуфлёр - серия ") + teleprompter.episode
    width: boundedWidth(1240, 40)
    height: boundedHeight(820, 50)
    minimumWidth: 760
    minimumHeight: 520
    standardButtons: Dialog.NoButton
    // A transient window is minimized together with its owner on Windows.
    // Keep the owner only for sizing and initial placement there.
    transientParent: windowsStyle || !ownerWindow ? null : ownerWindow

    property bool sidePanelVisible: true
    property bool followEnabled: true
    property real headerHeight: Math.max(
        48,
        appBridge.uiState.intValue("teleprompter.headerHeight", 86)
    )
    property string observedEpisode: ""
    property var editingSourceIds: []
    property int colorTarget: -1
    property var colorPreviewOverrides: ({})
    property bool debugSimulationRunning: false
    property real debugSimulationSpeed: 1
    property real lastObservedPositionTime: -1
    property int pendingLocalNavigationIndex: -1
    property string lastViewportConfigSignature: ""
    readonly property var config: teleprompter.config
    readonly property var colors: Object.assign(
        {}, config.colors || {}, colorPreviewOverrides
    )
    readonly property bool hideLeadingTimecodeZeros: Boolean(
        config.hide_leading_timecode_zeros
    )
    readonly property bool pageDebugVisible: Boolean(config.page_debug_overlay)
    readonly property real targetHighlightOpacity: Math.max(0, Math.min(
        0.44,
        config.page_target_highlight_opacity === undefined
            ? 0.22 : Number(config.page_target_highlight_opacity)
    ))
    readonly property int targetHighlightBrightnessPercent: Math.round(
        targetHighlightOpacity / 0.44 * 100
    )
    readonly property int targetHighlightFadeMs: Math.max(0, Math.min(
        10000,
        config.page_target_highlight_fade_ms === undefined
            ? 1000 : Number(config.page_target_highlight_fade_ms)
    ))
    readonly property int scrollSmoothnessLevel: Math.round(
        Math.max(0, Math.min(
            100, Number(config.scroll_smoothness_slider || 0)
        ))
    )
    // Internal duration for one useful screen of travel.  The setting is
    // presented as a level: actual animations also account for distance and
    // the time left before the next timed scroll target.
    readonly property int scrollDurationMs: Math.round(
        150 * Math.pow(
            5000 / 150,
            scrollSmoothnessLevel / 100
        )
    )
    readonly property int toolbarControlHeight: Math.max(macOSStyle ? 28 : 40, Math.ceil(interfaceFontMetrics.height + (macOSStyle ? 10 : 18)))

    FontMetrics {
        id: interfaceFontMetrics
        font: Application.font
    }

    SystemPalette {
        id: systemPalette
        colorGroup: SystemPalette.Active
    }

    Timer {
        id: debugReaperTimer
        interval: 50
        repeat: true
        running: window.pageDebugVisible
            && window.teleprompter.debugSimulationActive
            && window.debugSimulationRunning
        onTriggered: window.teleprompter.debugSetReaperTime(
            window.teleprompter.time
                + interval / 1000 * window.debugSimulationSpeed
        )
    }

    function setDebugReaperTime(seconds) {
        if (!teleprompter.debugSimulationActive) {
            teleprompter.debugSetSimulationActive(true);
        }
        teleprompter.debugSetReaperTime(Math.max(0, Number(seconds)));
    }

    function parseDebugTimecode(value) {
        var parts = String(value || "").trim().split(":");
        var seconds = 0;
        for (var index = 0; index < parts.length; index++) {
            var part = Number(parts[index]);
            if (!isFinite(part)) {
                return Number.NaN;
            }
            seconds = seconds * 60 + part;
        }
        return seconds;
    }

    function viewportConfigSignature() {
        // Only settings that can change delegate or viewport geometry belong
        // here. Colors, target-highlight options and OSC settings update
        // their bindings without interrupting an active scroll transaction.
        return [
            config.layout_type,
            config.f_tc, config.f_char, config.f_actor, config.f_text,
            config.bold_tc, config.bold_char,
            config.bold_actor, config.bold_text,
            config.show_header, config.show_timecode,
            config.show_end_timecode,
            config.show_character, config.show_actor, config.show_replica,
            config.hide_leading_timecode_zeros,
            config.focus_ratio, config.page_scroll_mode
        ].join("|");
    }

    Component.onCompleted: {
        lastViewportConfigSignature = viewportConfigSignature();
    }

    onPageDebugVisibleChanged: {
        if (!pageDebugVisible) {
            debugSimulationRunning = false;
            teleprompter.debugSetSimulationActive(false);
        }
    }

    function openFor(episode) {
        resetFollowingState();
        if (!teleprompter.prepare(episode)) {
            return;
        }
        open();
        requestActivate();
    }

    function setEpisode(episode) {
        if (String(episode) === String(teleprompter.episode)) {
            return;
        }
        resetFollowingState();
        teleprompter.setEpisode(episode);
    }

    function resetFollowingState() {
        followEnabled = true;
        replicaView.resetPageFollowState();
    }

    function navigate(direction) {
        followEnabled = true;
        replicaView.cancelPageHold();
        pendingLocalNavigationIndex = -1;
        teleprompter.navigate(direction);
    }

    function jumpToReplica(index) {
        followEnabled = true;
        replicaView.cancelPageHold();
        pendingLocalNavigationIndex = index;
        teleprompter.jumpToIndex(index);
    }

    function displayedTimecode(value) {
        var text = String(value || "")
        if (window.hideLeadingTimecodeZeros) {
            return text.replace(/^0+:/, "")
        }
        return text
    }

    function colorKeyAt(index) {
        var keys = [
            "bg", "active_text", "inactive_text", "tc", "actor",
            "header_text", "block_border",
            "page_target_highlight"
        ];
        return index >= 0 && index < keys.length ? keys[index] : "";
    }

    function previewColor(index, value) {
        var key = colorKeyAt(index);
        if (!key) {
            return;
        }
        var next = Object.assign({}, colorPreviewOverrides);
        next[key] = String(value);
        colorPreviewOverrides = next;
    }

    function clearColorPreview() {
        colorPreviewOverrides = ({});
    }

    function openReplicaEditor(sourceIds, character, replicaText) {
        editingSourceIds = sourceIds;
        characterEdit.editText = character;
        textEdit.text = replicaText;
        splitCharacter.editText = "";
        editWindow.clearTransferSelection();
        editWindow.open();
    }

    onClosed: {
        floatWindow.close();
        teleprompter.close();
    }

    Connections {
        target: window.teleprompter
        function onChanged() {
            var currentEpisode = String(window.teleprompter.episode);
            episodeBox.currentIndex = episodeBox.indexOfValue(currentEpisode);
            if (window.observedEpisode !== currentEpisode) {
                window.observedEpisode = currentEpisode;
                window.lastObservedPositionTime = -1;
                window.resetFollowingState();
            } else {
                replicaView.queueModelRefresh();
            }
        }
        function onPositionChanged() {
            var currentTime = Number(window.teleprompter.time);
            var previousTime = window.lastObservedPositionTime;
            var discontinuity = previousTime >= 0
                && (currentTime < previousTime - 0.02
                    || Math.abs(currentTime - previousTime) > 3);
            window.lastObservedPositionTime = currentTime;
            if (window.teleprompter.positionOrigin === "local"
                    || discontinuity) {
                replicaView.prepareForTimeSeek();
            }
            if (window.teleprompter.positionOrigin === "local") {
                var explicitIndex = window.pendingLocalNavigationIndex;
                window.pendingLocalNavigationIndex = -1;
                if (explicitIndex >= 0) {
                    replicaView.queueLocalNavigation(explicitIndex);
                } else {
                    // Read through a method rather than a cached QML property:
                    // Connections can run before the currentIndex binding has
                    // reevaluated for keyboard/toolbar navigation.
                    replicaView.queueLocalNavigation(
                        window.teleprompter.currentIndexNow()
                    );
                }
                return;
            }
            if (window.teleprompter.positionOrigin === "reaper"
                    && !replicaView.pageScrollMode
                    && !window.followEnabled
                    && !replicaView.manualDragScroll
                    && !replicaView.dragging
                    && !replicaView.moving) {
                window.followEnabled = true;
            }
            replicaView.followCurrentLongReplica();
            replicaView.queuePageFollow();
            if (window.teleprompter.positionOrigin === "reaper") {
                replicaView.resumePageFollowForReaperPosition();
                replicaView.prefetchNextReplicaDuringGap();
            }
        }
        function onConfigChanged() {
            var signature = window.viewportConfigSignature();
            if (signature === window.lastViewportConfigSignature) {
                return;
            }
            window.lastViewportConfigSignature = signature;
            // Font profiles, layout and focus can change delegate geometry
            // without changing the window itself.  Recalculate against the
            // newly rendered items instead of reusing old pixel targets.
            Qt.callLater(replicaView.queueViewportFollow);
        }
    }

    Shortcut {
        sequence: window.config.key_prev || "Left"
        onActivated: window.navigate(-1)
    }
    Shortcut {
        sequence: window.config.key_next || "Right"
        onActivated: window.navigate(1)
    }
    TeleprompterFloatWindow {
        id: floatWindow
        ownerWindow: window
        teleprompter: window.teleprompter
        uiState: window.appBridge.uiState
        softBorder: window.softBorder
        softMuted: window.softMuted
    }

    Connections {
        target: floatWindow
        function onVisibleChanged() {
            floatButton.checked = floatWindow.visible;
        }
        function onReplicaJumpRequested(index) {
            window.jumpToReplica(index);
        }
        function onNavigationRequested(direction) {
            window.navigate(direction);
        }
        function onEpisodeChangeRequested(episode) {
            window.setEpisode(episode);
        }
    }

    ColorDialog {
        id: colorDialog
        title: qsTr("Цвет телесуфлёра")
        property bool previewActive: false
        onSelectedColorChanged: {
            if (previewActive) {
                window.previewColor(window.colorTarget, selectedColor);
            }
        }
        onAccepted: {
            var key = window.colorKeyAt(window.colorTarget);
            previewActive = false;
            if (key) {
                window.teleprompter.setConfigValue(
                    "colors." + key, selectedColor.toString()
                );
            }
            window.clearColorPreview();
        }
        onRejected: {
            previewActive = false;
            window.clearColorPreview();
        }
    }

    NativeDialogWindow {
        id: actorFilterWindow
        ownerWindow: window
        modal: false
        title: qsTr("Актёры телесуфлёра")
        width: boundedWidth(440, 40)
        height: boundedHeight(560, 50)
        standardButtons: macOSStyle ? Dialog.NoButton : Dialog.Close
        property string actorSearchText: ""

        function matchesActor(name) {
            var needle = actorSearchText.trim().toLocaleLowerCase();
            return needle.length === 0 || String(name).toLocaleLowerCase().indexOf(needle) >= 0;
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                AdaptiveButton {
                    text: qsTr("Выбрать всех")
                    onClicked: window.teleprompter.selectAllActors(true)
                }
                AdaptiveButton {
                    text: qsTr("Снять выбор")
                    onClicked: window.teleprompter.selectAllActors(false)
                }
                Item {
                    Layout.fillWidth: true
                }
            }

            TextField {
                id: actorFilterSearchField
                Layout.fillWidth: true
                placeholderText: qsTr("Имя или фамилия")
                selectByMouse: true
                onTextChanged: actorFilterWindow.actorSearchText = text
            }

            TableHeaderSurface {
                Layout.fillWidth: true
                Layout.preferredHeight: actorFilterWindow.tableHeaderHeight
                softHeader: window.softHeader
                softBorder: window.softBorder

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8
                    TableHeaderLabel {
                        text: qsTr("Актёр")
                        Layout.fillWidth: true
                    }
                    TableHeaderLabel {
                        text: qsTr("Роли")
                        Layout.preferredWidth: 48
                    }
                    Item {
                        Layout.preferredWidth: 28
                    }
                }
            }

            PersistentListView {
                id: actorFilterList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: window.teleprompter.actorModel

                delegate: Item {
                    id: actorFilterRow

                    required property int index
                    required property string actorId
                    required property string name
                    required property string color
                    required property bool selected
                    required property int roleCount

                    width: actorFilterList.viewportWidth
                    visible: actorFilterWindow.matchesActor(actorFilterRow.name)
                    height: visible ? actorFilterWindow.compactRowHeight : 0

                    HoverHandler {
                        id: rowHover
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: rowHover.hovered ? Qt.rgba(systemPalette.highlight.r, systemPalette.highlight.g, systemPalette.highlight.b, 0.12) : (actorFilterRow.index % 2 === 0 ? window.softRow : window.softAltRow)
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        ActorColorSwatch {
                            Layout.preferredWidth: 16
                            Layout.preferredHeight: 16
                            swatchColor: actorFilterRow.color
                            markerShape: window.actorMarkerShape
                            markerSize: window.actorMarkerSize
                        }
                        Label {
                            text: actorFilterRow.name
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: actorFilterRow.roleCount
                            Layout.preferredWidth: 48
                            horizontalAlignment: Text.AlignHCenter
                        }
                        CheckBox {
                            Accessible.name: qsTr("Показывать реплики ") + actorFilterRow.name
                            checked: actorFilterRow.selected
                            Layout.preferredWidth: 28
                            onToggled: window.teleprompter.setActorSelected(actorFilterRow.actorId, checked)
                        }
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: actorFilterWindow.actorSearchText.length > 0 ? actorFilterList.contentHeight <= 0 : actorFilterList.count === 0
                    text: actorFilterWindow.actorSearchText.length > 0 ? qsTr("Актёры не найдены") : qsTr("В проекте нет актёров")
                    color: window.softMuted
                }
            }
        }
    }

    NativeDialogWindow {
        id: editWindow
        ownerWindow: window
        modal: true
        title: qsTr("Редактировать реплику")
        width: boundedWidth(680, 40)
        // Keep the compact editor by default and grow only for wrapped lines
        // in the transfer preview, so the text editor never has to shrink.
        height: boundedHeight(500 + Math.max(0, splitPreview.implicitHeight - splitPreviewMetrics.height), 50)
        standardButtons: Dialog.Save | Dialog.Cancel

        FontMetrics {
            id: splitPreviewMetrics
            font: Application.font
        }

        property int transferSelectionStart: 0
        property int transferSelectionEnd: 0
        property string transferSelectionText: ""
        readonly property string selectedReplicaText: transferSelectionText.replace(/\u2029/g, "\n").trim()
        readonly property string splitCharacterName: String(splitCharacter.editText || splitCharacter.currentText || "").trim()

        function clearTransferSelection() {
            transferSelectionStart = 0;
            transferSelectionEnd = 0;
            transferSelectionText = "";
        }

        function rememberTransferSelection() {
            var start = Math.min(textEdit.selectionStart, textEdit.selectionEnd);
            var end = Math.max(textEdit.selectionStart, textEdit.selectionEnd);
            if (end > start) {
                transferSelectionStart = start;
                transferSelectionEnd = end;
                transferSelectionText = textEdit.text.slice(start, end);
            } else if (textEdit.activeFocus) {
                // A click inside the editor intentionally cancels the previous
                // selection. Losing focus to a Windows Fluent control does not.
                clearTransferSelection();
            }
        }

        function transferSelectedText() {
            if (window.editingSourceIds.length !== 1 || !selectedReplicaText.length || !splitCharacterName.length) {
                return;
            }

            var remaining = textEdit.text.slice(0, transferSelectionStart) + textEdit.text.slice(transferSelectionEnd);
            if (window.teleprompter.splitReplica(window.editingSourceIds, remaining, selectedReplicaText, splitCharacterName)) {
                editWindow.close();
            }
        }

        onAccepted: {
            if (window.teleprompter.editReplica(window.editingSourceIds, characterEdit.editText, textEdit.text)) {
                close();
            }
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            Label {
                text: qsTr("Персонаж")
            }
            PlatformComboBox {
                id: characterEdit
                Layout.fillWidth: true
                editable: true
                model: window.teleprompter.characterNames
            }
            Label {
                text: qsTr("Текст")
            }
            PersistentScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                TextArea {
                    id: textEdit
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    onSelectionStartChanged: editWindow.rememberTransferSelection()
                    onSelectionEndChanged: editWindow.rememberTransferSelection()
                }
            }

            FormSection {
                title: qsTr("Передать часть текста другому персонажу")
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    PlatformComboBox {
                        id: splitCharacter
                        Layout.fillWidth: true
                        editable: true
                        model: window.teleprompter.characterNames
                    }
                    Label {
                        id: splitPreview
                        Layout.fillWidth: true
                        text: editWindow.selectedReplicaText.length > 0 ? qsTr("Будет передано: ") + editWindow.selectedReplicaText : qsTr("Выделите часть текста выше")
                        color: editWindow.selectedReplicaText.length > 0 ? palette.text : window.softMuted
                        wrapMode: Text.WordWrap
                    }
                    AdaptiveButton {
                        text: qsTr("Передать выделенное")
                        enabled: window.editingSourceIds.length === 1 && editWindow.selectedReplicaText.length > 0 && editWindow.splitCharacterName.length > 0
                        onClicked: editWindow.transferSelectedText()
                    }
                }
            }
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: window.toolbarControlHeight
            Layout.leftMargin: window.macOSStyle ? 12 : 0
            Layout.rightMargin: window.macOSStyle ? 12 : 0
            spacing: window.macOSStyle ? 10 : 8

            CompactToolButton {
                Layout.alignment: Qt.AlignVCenter
                iconSource: Qt.resolvedUrl("../icons/settings.svg")
                toolTipText: window.sidePanelVisible ? qsTr("Скрыть настройки") : qsTr("Показать настройки")
                checkable: true
                checked: window.sidePanelVisible
                onClicked: window.sidePanelVisible = !window.sidePanelVisible
            }
            Label {
                text: qsTr("Серия:")
            }
            PlatformComboBox {
                id: episodeBox
                Layout.preferredWidth: 150
                Layout.minimumHeight: window.toolbarControlHeight
                Layout.preferredHeight: window.toolbarControlHeight
                Layout.maximumHeight: window.toolbarControlHeight
                Layout.alignment: Qt.AlignVCenter
                textRole: "name"
                valueRole: "name"
                model: window.teleprompter.episodesModel
                Component.onCompleted: currentIndex = indexOfValue(window.teleprompter.episode)
                onActivated: window.setEpisode(currentValue)
            }
            AdaptiveButton {
                text: qsTr("Обновить каст")
                Layout.preferredHeight: window.toolbarControlHeight
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.teleprompter.refreshCast()
            }
            Item {
                Layout.fillWidth: true
            }
            CompactToolButton {
                iconSource: Qt.resolvedUrl("../icons/chevron-left.svg")
                toolTipText: qsTr("Предыдущая реплика")
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.navigate(-1)
            }
            CompactToolButton {
                iconSource: Qt.resolvedUrl("../icons/chevron-right.svg")
                toolTipText: qsTr("Следующая реплика")
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.navigate(1)
            }
            CompactToolButton {
                id: floatButton
                visible: true
                iconSource: Qt.resolvedUrl("../icons/remote-control.svg")
                toolTipText: qsTr("Плавающий контроллер")
                Layout.alignment: Qt.AlignVCenter
                enabled: true
                checkable: true
                checked: floatWindow.visible
                onToggled: checked ? floatWindow.openNearOwner() : floatWindow.close()
            }
            CompactToolButton {
                visible: Boolean(window.config.osc_enabled)
                enabled: window.teleprompter.oscAvailable
                iconSource: Qt.resolvedUrl("../icons/refresh.svg")
                toolTipText: qsTr("Переподключить REAPER")
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.teleprompter.restartOsc()
                PlatformToolTip {
                    target: parent
                    text: qsTr("Перезапустить подключение OSC без сброса позиции")
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                visible: window.sidePanelVisible
                Layout.preferredWidth: visible ? (window.macOSStyle ? 336 : 350) : 0
                Layout.fillHeight: true
                color: systemPalette.window
                border.width: window.macOSStyle ? 0 : 1
                border.color: window.softBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: window.macOSStyle ? 12 : 8
                    anchors.rightMargin: window.macOSStyle ? 12 : 8
                    anchors.topMargin: window.macOSStyle ? 10 : 8
                    anchors.bottomMargin: window.macOSStyle ? 10 : 8
                    spacing: window.macOSStyle ? 10 : 8

                    PersistentScrollView {
                        id: settingsScroll
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(settingsColumn.implicitHeight, Math.max(260, parent.height * 0.62))
                        clip: true
                        contentWidth: availableWidth
                        contentHeight: settingsColumn.implicitHeight
                        persistentVerticalScrollBar: false

                        ColumnLayout {
                            id: settingsColumn
                            width: settingsScroll.availableWidth
                            spacing: window.macOSStyle ? 9 : 5

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    id: oscStatusLabel
                                    text: qsTr("Просмотр")
                                    font.weight: window.macOSStyle ? Font.DemiBold : Font.Bold
                                    font.pixelSize: window.macOSStyle ? 11 : font.pixelSize
                                    font.capitalization: window.macOSStyle ? Font.AllUppercase : Font.MixedCase
                                    color: window.macOSStyle ? window.softMuted : systemPalette.text
                                    Layout.fillWidth: true
                                }
                                RowLayout {
                                    visible: window.macOSStyle && window.config.osc_enabled
                                    spacing: 5
                                    Layout.maximumWidth: 190

                                    Rectangle {
                                        implicitWidth: 8
                                        implicitHeight: 8
                                        Layout.preferredWidth: implicitWidth
                                        Layout.preferredHeight: implicitHeight
                                        radius: 4
                                        color: window.teleprompter.reaperConnectionState === "active" ? "#2E9E5B" : window.teleprompter.reaperConnectionState === "lost" || window.teleprompter.reaperConnectionState === "error" || window.teleprompter.reaperConnectionState === "unavailable" ? "#D65D4A" : window.softMuted
                                    }
                                    Label {
                                        text: window.teleprompter.reaperConnectionText
                                        color: window.softMuted
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    HoverHandler {
                                        id: oscStatusHover
                                    }
                                    PlatformToolTip {
                                        target: parent
                                        active: oscStatusHover.hovered
                                        text: window.teleprompter.reaperConnectionText + "\n" + window.teleprompter.oscStatus
                                    }
                                }
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: Boolean(window.config.layout_template)
                                text: qsTr("Активен пользовательский макет: %1").arg(
                                    window.config.layout_template
                                        ? window.config.layout_template.name : ""
                                )
                                color: window.softMuted
                                wrapMode: Text.WordWrap
                            }

                            RowLayout {
                                visible: !window.macOSStyle && window.config.osc_enabled
                                Layout.fillWidth: true
                                spacing: 6

                                Rectangle {
                                    implicitWidth: 8
                                    implicitHeight: 8
                                    Layout.preferredWidth: implicitWidth
                                    Layout.preferredHeight: implicitHeight
                                    radius: 4
                                    color: window.teleprompter.reaperConnectionState === "active" ? "#2E9E5B" : window.teleprompter.reaperConnectionState === "lost" || window.teleprompter.reaperConnectionState === "error" || window.teleprompter.reaperConnectionState === "unavailable" ? "#D65D4A" : window.softMuted
                                }
                                Label {
                                    text: window.teleprompter.reaperConnectionText
                                    color: window.softMuted
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                HoverHandler {
                                    id: windowsOscStatusHover
                                }
                                PlatformToolTip {
                                    target: parent
                                    active: windowsOscStatusHover.hovered
                                    text: window.teleprompter.reaperConnectionText + "\n" + window.teleprompter.oscStatus
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: qsTr("Разметка") }
                                PlatformComboBox {
                                    id: prompterLayoutCombo
                                    Layout.fillWidth: true
                                    model: [
                                        "Сценарий 1",
                                        "Сценарий 2",
                                        "Сценарий 3"
                                    ]
                                    currentIndex: Math.max(
                                        0, model.indexOf(
                                            String(window.config.layout_type)
                                        )
                                    )
                                    onActivated: window.teleprompter.setConfigValue(
                                        "layout_type", currentText
                                    )
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                CheckBox {
                                    text: qsTr("Зеркально")
                                    checked: window.config.is_mirrored
                                    onToggled: window.teleprompter.setConfigValue("is_mirrored", checked)
                                }
                                CheckBox {
                                    text: qsTr("Таймкод")
                                    checked: window.config.show_header
                                    onToggled: window.teleprompter.setConfigValue("show_header", checked)
                                }
                                Item {
                                    Layout.fillWidth: true
                                }
                            }

                            Label {
                                text: qsTr("Положение фокуса · ") + Math.round(focusSlider.value * 100) + "%"
                            }
                            Slider {
                                id: focusSlider
                                Layout.fillWidth: true
                                from: 0.1
                                to: 0.9
                                value: window.config.focus_ratio
                                onPressedChanged: if (!pressed)
                                    window.teleprompter.setConfigValue("focus_ratio", value)
                            }

                            CollapsibleSection {
                                title: qsTr("Элементы")
                                sidebarStyle: window.macOSStyle
                                Layout.fillWidth: true

                                CheckBox {
                                    text: qsTr("Таймкод")
                                    checked: Boolean(window.config.show_timecode)
                                    onToggled: window.teleprompter.setConfigValue("show_timecode", checked)
                                }
                                CheckBox {
                                    text: qsTr("Окончание реплики")
                                    checked: Boolean(window.config.show_end_timecode)
                                    enabled: Boolean(window.config.show_timecode)
                                    onToggled: window.teleprompter.setConfigValue(
                                        "show_end_timecode", checked
                                    )
                                }
                                CheckBox {
                                    text: qsTr("Персонаж")
                                    checked: Boolean(window.config.show_character)
                                    onToggled: window.teleprompter.setConfigValue("show_character", checked)
                                }
                                CheckBox {
                                    text: qsTr("Актёр")
                                    checked: Boolean(window.config.show_actor)
                                    onToggled: window.teleprompter.setConfigValue("show_actor", checked)
                                }
                                CheckBox {
                                    text: qsTr("Реплика")
                                    checked: Boolean(window.config.show_replica)
                                    onToggled: window.teleprompter.setConfigValue("show_replica", checked)
                                }
                                CheckBox {
                                    text: qsTr("Границы блоков")
                                    checked: Boolean(window.config.show_block_borders)
                                    onToggled: window.teleprompter.setConfigValue("show_block_borders", checked)
                                }
                                CheckBox {
                                    text: qsTr("Скрывать нули")
                                    checked: Boolean(window.config.hide_leading_timecode_zeros)
                                    onToggled: window.teleprompter.setConfigValue("hide_leading_timecode_zeros", checked)
                                }
                            }

                            CollapsibleSection {
                                title: qsTr("Размер текста")
                                sidebarStyle: window.macOSStyle
                                Layout.fillWidth: true

                                Repeater {
                                    model: [
                                        {
                                            label: "Таймкод",
                                            key: "f_tc",
                                            value: window.config.f_tc,
                                            boldKey: "bold_tc",
                                            boldValue: window.config.bold_tc
                                        },
                                        {
                                            label: "Персонаж",
                                            key: "f_char",
                                            value: window.config.f_char,
                                            boldKey: "bold_char",
                                            boldValue: window.config.bold_char
                                        },
                                        {
                                            label: "Актёр",
                                            key: "f_actor",
                                            value: window.config.f_actor,
                                            boldKey: "bold_actor",
                                            boldValue: window.config.bold_actor
                                        },
                                        {
                                            label: "Реплика",
                                            key: "f_text",
                                            value: window.config.f_text,
                                            boldKey: "bold_text",
                                            boldValue: window.config.bold_text
                                        }
                                    ]
                                    delegate: RowLayout {
                                        id: fontRow
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Label {
                                            text: fontRow.modelData.label
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            elide: Text.ElideRight
                                        }
                                        SpinBox {
                                            // Fluent's up/down affordances need room beside the value.
                                            // Keep this wide enough for the editable numeric field and
                                            // let the label yield space first on a narrow sidebar.
                                            Layout.preferredWidth: window.windowsStyle ? 108 : 88
                                            Layout.minimumWidth: window.windowsStyle ? 100 : 80
                                            Layout.maximumWidth: window.windowsStyle ? 112 : 96
                                            from: 10
                                            to: fontRow.modelData.key === "f_text" ? 300 : 150
                                            value: fontRow.modelData.value
                                            editable: true
                                            onValueModified: window.teleprompter.setConfigValue(fontRow.modelData.key, value)
                                        }
                                        CheckBox {
                                            text: qsTr("Жирный")
                                            Layout.preferredWidth: implicitWidth
                                            Layout.minimumWidth: implicitWidth
                                            checked: fontRow.modelData.boldValue
                                            onToggled: window.teleprompter.setConfigValue(
                                                fontRow.modelData.boldKey,
                                                checked
                                            )
                                        }
                                    }
                                }
                            }

                            CollapsibleSection {
                                title: qsTr("Цвета и пресеты")
                                sidebarStyle: window.macOSStyle
                                Layout.fillWidth: true

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 5

                                    Label {
                                        text: qsTr("Пресеты")
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 4
                                        columnSpacing: 6
                                        rowSpacing: 6

                                        Repeater {
                                            model: window.teleprompter.presetModel
                                            delegate: AdaptiveButton {
                                                id: presetButton
                                                required property int presetIndex
                                                required property bool filled
                                                required property string presetBackground
                                                required property string presetForeground
                                                Layout.fillWidth: true
                                                Layout.minimumWidth: 0
                                                Layout.maximumWidth: Number.POSITIVE_INFINITY
                                                Layout.preferredWidth: 1
                                                Layout.preferredHeight: window.macOSStyle ? implicitHeight : 30
                                                text: String(presetIndex + 1)
                                                PlatformToolTip {
                                                    target: presetButton
                                                    text: presetButton.filled
                                                        ? qsTr("Применить пресет")
                                                        : qsTr("Сохранить текущие цвета")
                                                }
                                                onClicked: window.teleprompter.applyOrSavePreset(presetIndex)
                                                onPressAndHold: if (filled)
                                                    window.teleprompter.clearPreset(presetIndex)

                                                Menu {
                                                    id: presetContextMenu

                                                    MenuItem {
                                                        text: qsTr("Перезаписать пресет")
                                                        onTriggered: window.teleprompter.savePreset(
                                                            presetButton.presetIndex
                                                        )
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    z: 10
                                                    acceptedButtons: Qt.RightButton
                                                    preventStealing: true

                                                    onClicked: function(mouse) {
                                                        if (presetButton.filled)
                                                            presetContextMenu.popup(mouse.x, mouse.y)
                                                    }
                                                }

                                                Rectangle {
                                                    visible: presetButton.filled
                                                    width: 12
                                                    height: 4
                                                    radius: 2
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    anchors.bottom: parent.bottom
                                                    anchors.bottomMargin: 3
                                                    color: presetButton.presetBackground
                                                    border.color: presetButton.presetForeground
                                                }
                                            }
                                        }
                                    }
                                }

                                Repeater {
                                    model: ["Фон", "Активный текст", "Неактивный текст", "Таймкод", "Актёр", "Текст заголовка", "Границы блоков", "Подсветка прокрутки"]
                                    delegate: RowLayout {
                                        id: colorRow
                                        required property int index
                                        required property string modelData
                                        readonly property color swatchColor: [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_text, window.colors.block_border, window.colors.page_target_highlight][colorRow.index]

                                        Layout.fillWidth: true
                                        spacing: 8

                                        Rectangle {
                                            Layout.preferredWidth: 16
                                            Layout.preferredHeight: 16
                                            radius: window.macOSStyle ? 8 : 3
                                            color: colorRow.swatchColor
                                            border.width: 1
                                            border.color: window.softBorder
                                        }

                                        AdaptiveButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: window.macOSStyle ? implicitHeight : 32
                                            text: colorRow.modelData
                                            Accessible.name: qsTr("Изменить цвет: ") + colorRow.modelData

                                            onClicked: {
                                                var values = [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_text, window.colors.block_border, window.colors.page_target_highlight];
                                                colorDialog.previewActive = false;
                                                window.colorTarget = colorRow.index;
                                                colorDialog.selectedColor = values[colorRow.index];
                                                window.clearColorPreview();
                                                colorDialog.previewActive = true;
                                                colorDialog.open();
                                            }
                                        }
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: qsTr("Яркость подсветки · %1%").arg(
                                        window.targetHighlightBrightnessPercent
                                    )
                                }
                                Slider {
                                    id: targetHighlightBrightnessSlider
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    stepSize: 1
                                    value: window.targetHighlightBrightnessPercent
                                    onPressedChanged: if (!pressed) {
                                        window.teleprompter.setConfigValue(
                                            "page_target_highlight_opacity",
                                            Math.max(0, Math.min(
                                                0.44, value * 0.0044
                                            ))
                                        )
                                    }
                                    PlatformToolTip {
                                        target: targetHighlightBrightnessSlider
                                        text: qsTr("0% — полностью прозрачная, 100% — наиболее заметная")
                                    }
                                }

                            }

                            CollapsibleSection {
                                title: qsTr("Прокрутка")
                                expanded: true
                                sidebarStyle: window.macOSStyle
                                Layout.fillWidth: true

                                Label {
                                    text: qsTr("Режим прокрутки")
                                    color: window.softMuted
                                }
                                Rectangle {
                                    id: scrollModeSelector
                                    readonly property bool pageSelected:
                                        Boolean(window.config.page_scroll_mode)

                                    Layout.fillWidth: true
                                    Layout.preferredHeight: Math.max(
                                        34, window.toolbarControlHeight
                                    )
                                    radius: window.macOSStyle ? 7 : 4
                                    color: Qt.rgba(
                                        systemPalette.text.r,
                                        systemPalette.text.g,
                                        systemPalette.text.b,
                                        0.055
                                    )
                                    border.width: 1
                                    border.color: window.softBorder

                                    function setPageMode(enabled) {
                                        if (pageSelected !== enabled) {
                                            window.appBridge.settings.setPrompterPageScrollMode(
                                                enabled
                                            );
                                        }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        spacing: 2

                                        Rectangle {
                                            id: continuousModeSegment
                                            readonly property bool selected:
                                                !scrollModeSelector.pageSelected

                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: window.macOSStyle ? 5 : 3
                                            color: selected
                                                ? systemPalette.button
                                                : continuousModeMouse.containsMouse
                                                    ? Qt.rgba(
                                                        systemPalette.text.r,
                                                        systemPalette.text.g,
                                                        systemPalette.text.b,
                                                        0.07
                                                    )
                                                    : "transparent"
                                            border.width: selected || activeFocus ? 1 : 0
                                            border.color: window.softBorder
                                            activeFocusOnTab: true
                                            Accessible.role: Accessible.RadioButton
                                            Accessible.name: qsTr("Обычный режим прокрутки")
                                            Accessible.checked: selected
                                            Accessible.onPressAction:
                                                scrollModeSelector.setPageMode(false)
                                            Keys.onPressed: function(event) {
                                                if (event.key === Qt.Key_Space
                                                        || event.key === Qt.Key_Return
                                                        || event.key === Qt.Key_Enter) {
                                                    scrollModeSelector.setPageMode(false);
                                                    event.accepted = true;
                                                }
                                            }

                                            MouseArea {
                                                id: continuousModeMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: scrollModeSelector.setPageMode(false)
                                            }

                                            Text {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                text: qsTr("Обычный")
                                                color: continuousModeSegment.selected
                                                    ? systemPalette.buttonText
                                                    : window.softMuted
                                                font.weight: continuousModeSegment.selected
                                                    ? Font.DemiBold : Font.Normal
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                elide: Text.ElideRight
                                            }
                                        }

                                        Rectangle {
                                            id: pageModeSegment
                                            readonly property bool selected:
                                                scrollModeSelector.pageSelected

                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: window.macOSStyle ? 5 : 3
                                            color: selected
                                                ? systemPalette.button
                                                : pageModeMouse.containsMouse
                                                    ? Qt.rgba(
                                                        systemPalette.text.r,
                                                        systemPalette.text.g,
                                                        systemPalette.text.b,
                                                        0.07
                                                    )
                                                    : "transparent"
                                            border.width: selected || activeFocus ? 1 : 0
                                            border.color: window.softBorder
                                            activeFocusOnTab: true
                                            Accessible.role: Accessible.RadioButton
                                            Accessible.name: qsTr("Постраничный режим прокрутки")
                                            Accessible.checked: selected
                                            Accessible.onPressAction:
                                                scrollModeSelector.setPageMode(true)
                                            Keys.onPressed: function(event) {
                                                if (event.key === Qt.Key_Space
                                                        || event.key === Qt.Key_Return
                                                        || event.key === Qt.Key_Enter) {
                                                    scrollModeSelector.setPageMode(true);
                                                    event.accepted = true;
                                                }
                                            }

                                            MouseArea {
                                                id: pageModeMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: scrollModeSelector.setPageMode(true)
                                            }

                                            Text {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 8
                                                text: qsTr("Постраничный")
                                                color: pageModeSegment.selected
                                                    ? systemPalette.buttonText
                                                    : window.softMuted
                                                font.weight: pageModeSegment.selected
                                                    ? Font.DemiBold : Font.Normal
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }

                                    PlatformToolTip {
                                        target: parent
                                        text: scrollModeSelector.pageSelected
                                            ? qsTr("Прокрутка экранными фрагментами")
                                            : qsTr("Плавное следование по окончании реплик")
                                    }
                                }

                                Label {
                                    text: qsTr("Синхронизация REAPER")
                                    color: window.softMuted
                                }
                                CheckBox {
                                    text: qsTr("Телесуфлёр следует за REAPER")
                                    checked: window.config.sync_in
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled("sync_in", checked)
                                }
                                CheckBox {
                                    text: qsTr("Следовать только во время Play")
                                    checked: Boolean(window.config.sync_play_only)
                                    enabled: Boolean(window.config.sync_in)
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled(
                                        "sync_play_only", checked
                                    )
                                }
                                CheckBox {
                                    text: qsTr("REAPER следует за навигацией")
                                    checked: window.config.sync_out
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled("sync_out", checked)
                                }
                                CheckBox {
                                    text: qsTr("Смещение REAPER (%1 с)").arg(
                                        Number(window.config.reaper_offset_seconds || 0)
                                    )
                                    checked: Boolean(window.config.reaper_offset_enabled)
                                    onToggled: window.teleprompter.setConfigValue(
                                        "reaper_offset_enabled", checked
                                    )
                                    PlatformToolTip {
                                        target: parent
                                        text: qsTr("Число секунд задаётся в глобальных настройках REAPER / OSC.")
                                    }
                                }
                                Label {
                                    text: qsTr("Уровень плавности · %1%")
                                        .arg(window.scrollSmoothnessLevel)
                                }
                                Slider {
                                    id: smoothSlider
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    value: window.config.scroll_smoothness_slider
                                    onPressedChanged: if (!pressed)
                                        window.teleprompter.setConfigValue("scroll_smoothness_slider", value)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: qsTr("Реплики")
                            font.weight: window.macOSStyle ? Font.DemiBold : Font.Bold
                            font.pixelSize: window.macOSStyle ? 11 : font.pixelSize
                            font.capitalization: window.macOSStyle ? Font.AllUppercase : Font.MixedCase
                            color: window.macOSStyle ? window.softMuted : systemPalette.text
                            Layout.fillWidth: true
                        }
                        AdaptiveButton {
                            text: qsTr("Актёры...")
                            onClicked: actorFilterWindow.open()
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 4
                        color: systemPalette.base
                        border.width: 1
                        border.color: window.softBorder
                        clip: true

                        PersistentListView {
                            id: navigationList
                            anchors.fill: parent
                            anchors.margins: 1
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds
                            model: window.teleprompter.model
                            currentIndex: window.teleprompter.currentIndex

                            delegate: Rectangle {
                                id: navigationRow

                                required property int index
                                required property real start
                                required property string time
                                required property string character
                                required property bool active

                                width: navigationList.viewportWidth
                                height: active ? 30 : 0
                                visible: active
                                color: index === navigationList.currentIndex ? Qt.rgba(systemPalette.highlight.r, systemPalette.highlight.g, systemPalette.highlight.b, 0.14) : navigationHover.hovered ? Qt.rgba(systemPalette.highlight.r, systemPalette.highlight.g, systemPalette.highlight.b, 0.07) : index % 2 === 0 ? "transparent" : Qt.rgba(systemPalette.text.r, systemPalette.text.g, systemPalette.text.b, 0.025)

                                HoverHandler {
                                    id: navigationHover
                                }
                                TapHandler {
                                    onTapped: {
                                        window.jumpToReplica(navigationRow.index);
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 6
                                    spacing: 7

                                    Label {
                                        text: window.displayedTimecode(navigationRow.time)
                                        color: systemPalette.text
                                        Layout.preferredWidth: 60
                                        horizontalAlignment: Text.AlignLeft
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: navigationRow.character
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: window.macOSStyle
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.right: parent.right
                    width: 1
                    color: Qt.rgba(systemPalette.text.r, systemPalette.text.g, systemPalette.text.b, 0.14)
                }
            }

            Rectangle {
                id: teleprompterSurface
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: window.colors.bg
                clip: true

                Rectangle {
                    id: teleprompterHeader
                    visible: window.config.show_header
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: visible ? Math.max(
                        48,
                        Math.min(
                            window.headerHeight,
                            Math.max(48, parent.height - 160)
                        )
                    ) : 0
                    color: window.colors.bg

                    Label {
                        anchors.centerIn: parent
                        text: window.displayedTimecode(
                            window.teleprompter.timecode
                        )
                        color: window.colors.header_text
                        font.pixelSize: Math.max(24, parent.height * 0.72)
                        font.bold: true
                    }

                    Item {
                        id: teleprompterHeaderDivider
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: -4
                        height: 9
                        z: 2

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            height: 1
                            color: window.colors.block_border || "#4D4D4D"
                        }

                        HoverHandler {
                            cursorShape: Qt.SizeVerCursor
                        }

                        DragHandler {
                            id: headerResizeHandler
                            target: null
                            yAxis.enabled: true
                            xAxis.enabled: false
                            property real initialHeight: 86

                            onActiveChanged: {
                                if (active) {
                                    initialHeight = teleprompterHeader.height;
                                } else {
                                    window.appBridge.uiState.setIntValue(
                                        "teleprompter.headerHeight",
                                        Math.round(window.headerHeight)
                                    );
                                }
                            }
                            onTranslationChanged: if (active) {
                                window.headerHeight = Math.max(
                                    48,
                                    Math.min(
                                        initialHeight + translation.y,
                                        Math.max(
                                            48,
                                            teleprompterSurface.height - 160
                                        )
                                    )
                                );
                            }
                        }
                    }
                }

                PersistentListView {
                    id: replicaView
                    objectName: "teleprompterReplicaView"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: teleprompterHeader.visible
                        ? teleprompterHeader.bottom : parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: Math.max(20, parent.width * 0.025)
                    anchors.rightMargin: anchors.leftMargin
                    clip: true
                    // The reading area intentionally has no scrollbar.  Do
                    // not reserve its gutter after delegates are created:
                    // otherwise Windows relayouts the first replica on the
                    // first scroll.
                    verticalScrollBarEnabled: false
                    spacing: Math.max(14, window.config.f_text * 0.45)
                    model: window.teleprompter.model
                    footer: Item {
                        width: replicaView.width
                        height: replicaView.pageScrollMode ? replicaView.height : 0
                    }
                    currentIndex: window.followEnabled ? window.teleprompter.currentIndex : -1
                    readonly property bool pageScrollMode: Boolean(window.config.page_scroll_mode)
                    property real pageScrollHoldUntil: -1
                    property real pageHoldLastReaperTime: -1
                    property real pageHoldLastReaperReceivedAt: -1
                    property bool pageFollowQueued: false
                    property bool viewportFollowQueued: false
                    property bool modelRefreshQueued: false
                    property bool pageFocusAlignmentActive: false
                    property int pageGapPrefetchIndex: -1
                    property int pageScrollTargetIndex: -1
                    property int lastPageFollowIndex: -1
                    property bool localNavigationActive: false
                    property int localNavigationTargetIndex: -1
                    property real localNavigationLastTargetY: Number.NaN
                    property int localNavigationStablePasses: 0
                    property bool localNavigationVerifying: false
                    property int pageTargetHighlightIndex: -1
                    property real pageTargetHighlightOpacity: 0
                    property bool pageTargetHighlightLineOnly: false
                    property real pageTargetHighlightX: 0
                    property real pageTargetHighlightY: 0
                    property real pageTargetHighlightWidth: 0
                    property real pageTargetHighlightHeight: 0
                    property bool manualDragScroll: false
                    property string pageDebugEvent: "Ожидание"
                    property real pageDebugSourceY: 0
                    property real pageDebugTargetY: 0
                    property real pageDebugItemTop: -1
                    property real pageDebugItemBottom: -1
                    property real pageDebugRenderedHeight: 0
                    property real pageDebugProgress: 0
                    property int pageDebugPage: 0
                    property int pageDebugPageCount: 1
                    property string pageDebugTimingSource: "visual"
                    property real pageDebugThresholdTime: -1
                    property int scrollDebugSmoothnessLevel: window.scrollSmoothnessLevel
                    property real scrollDebugDistanceScreens: 0
                    property int scrollDebugDesiredDurationMs: 0
                    property int scrollDebugAvailableDurationMs: -1
                    property int scrollDebugActualDurationMs: 0
                    property real scrollDebugDeadline: -1
                    property string scrollDebugDurationLimit: "нет"
                    property string pageDebugLastTraceSignature: ""
                    property var pageDebugTrace: []
                    // Keep the focus at the same absolute Y within the
                    // teleprompter when the in-viewport header is toggled.
                    // Only clamp when a very high focus would overlap it.
                    readonly property real teleprompterFocusY:
                        parent.height * focusSlider.value
                    preferredHighlightBegin: Math.max(
                        0,
                        Math.min(height, teleprompterFocusY - y)
                    )
                    preferredHighlightEnd: preferredHighlightBegin
                    // Keep one stable range mode. Switching it while
                    // currentIndex becomes -1 during manual scrolling makes
                    // ListView recycle and reposition most delegates.
                    highlightRangeMode: ListView.NoHighlightRange
                    highlightMoveDuration: window.scrollDurationMs

                    NumberAnimation {
                        id: pageScrollAnimation
                        target: replicaView
                        property: "contentY"
                        duration: window.scrollDurationMs
                        easing.type: Easing.InOutCubic
                        onStopped: replicaView.pageFocusAlignmentActive = false
                        onFinished: {
                            replicaView.correctPageScrollTarget();
                            replicaView.fadePageTargetHighlight();
                            replicaView.finishLocalNavigation();
                        }
                    }

                    Timer {
                        id: localNavigationTimer
                        interval: 32
                        repeat: false
                        onTriggered: {
                            if (replicaView.localNavigationVerifying) {
                                replicaView.finishLocalNavigation();
                            } else {
                                replicaView.startQueuedLocalNavigation();
                            }
                        }
                    }

                    Timer {
                        id: manualWheelReleaseTimer
                        interval: 140
                        repeat: false
                        onTriggered: {
                            if (replicaView.dragging || replicaView.moving) {
                                restart();
                                return;
                            }
                            replicaView.finishManualDragScroll();
                        }
                    }

                    NumberAnimation {
                        id: pageTargetHighlightFade
                        target: replicaView
                        property: "pageTargetHighlightOpacity"
                        duration: window.targetHighlightFadeMs
                        easing.type: Easing.OutCubic
                    }

                    NumberAnimation {
                        id: longReplicaScrollAnimation
                        target: replicaView
                        property: "contentY"
                        duration: window.scrollDurationMs
                        easing.type: Easing.InOutCubic
                        onFinished: replicaView.finishLocalNavigation()
                    }

                    function capturePageDebug(event, sourceY, targetY, itemTop, itemBottom) {
                        pageDebugEvent = event;
                        pageDebugSourceY = sourceY;
                        pageDebugTargetY = targetY;
                        pageDebugItemTop = itemTop;
                        pageDebugItemBottom = itemBottom;
                        if (!window.pageDebugVisible) {
                            return;
                        }
                        var signature = [
                            currentIndex,
                            pageDebugPage,
                            event,
                            Number(targetY).toFixed(1)
                        ].join("|");
                        if (signature === pageDebugLastTraceSignature) {
                            return;
                        }
                        pageDebugLastTraceSignature = signature;
                        var line = window.teleprompter.time.toFixed(3)
                            + "  i=" + currentIndex
                            + "  p=" + (pageDebugPage + 1)
                            + "/" + pageDebugPageCount
                            + "  " + event
                            + "  y=" + Number(sourceY).toFixed(1)
                            + "→" + Number(targetY).toFixed(1);
                        var nextTrace = pageDebugTrace.concat([line]);
                        pageDebugTrace = nextTrace.slice(
                            Math.max(0, nextTrace.length - 6)
                        );
                    }

                    function replicaFocusTargetY(index) {
                        var item = itemAtIndex(index);
                        // positionViewAtIndex() may change originY while a
                        // variable-height ListView materializes distant
                        // delegates.  Avoid that coordinate-system change
                        // whenever the target is already available.
                        if (!item) {
                            positionViewAtIndex(index, ListView.Beginning);
                            forceLayout();
                            item = itemAtIndex(index);
                        }
                        if (!item) {
                            return clampedContentY(contentY);
                        }
                        return clampedContentY(
                            item.y - preferredHighlightBegin
                        );
                    }

                    function minimumContentY() {
                        return isFinite(originY) ? Number(originY) : 0;
                    }

                    function maximumContentY() {
                        return minimumContentY()
                            + Math.max(0, contentHeight - height);
                    }

                    function clampedContentY(value) {
                        return Math.max(
                            minimumContentY(),
                            Math.min(maximumContentY(), value)
                        );
                    }

                    function replicaInsideCurrentPage(index) {
                        if (!pageScrollMode || index < 0) {
                            return false;
                        }
                        // Do not materialize a distant delegate here: doing
                        // so can itself rebase a variable-height ListView and
                        // move the page we are trying to preserve.
                        var item = itemAtIndex(index);
                        if (!item) {
                            return false;
                        }
                        var viewportTop = Number(contentY);
                        var viewportBottom = viewportTop + height;
                        return item.y >= viewportTop - 0.5
                            && item.y + item.height <= viewportBottom + 0.5;
                    }

                    function restoreValidContentBounds() {
                        var minimumY = minimumContentY();
                        var maximumY = maximumContentY();
                        if (isFinite(contentY)
                                && contentY >= minimumY - 0.5
                                && contentY <= maximumY + 0.5) {
                            return false;
                        }
                        // A variable-height ListView refines contentHeight as
                        // delegates are created and recycled. After a large
                        // manual scroll, resize or model refresh the previous
                        // pixel target can consequently lie beyond the new
                        // extent and leave the viewport effectively empty.
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageScrollTargetIndex = -1;
                        pageGapPrefetchIndex = -1;
                        pageFocusAlignmentActive = false;
                        contentY = Math.max(minimumY, Math.min(
                            maximumY,
                            isFinite(contentY) ? contentY : minimumY
                        ));
                        return true;
                    }

                    // A replica can be taller than the reading viewport.  In
                    // that case an index is not a sufficient scroll target:
                    // the target must also depend on the current time inside
                    // the replica.  The same bounds are used by both modes.
                    function replicaReadingBounds(index) {
                        var item = ensureReplicaItem(index);
                        // Measuring an already instantiated delegate must be
                        // read-only. positionViewAtIndex() on every OSC tick
                        // fights manual scrolling and ListView virtualization.
                        if (!item) {
                            return null;
                        }
                        var topY = clampedContentY(item.y - preferredHighlightBegin);
                        var bottomY = clampedContentY(item.y + item.height - height);
                        return {
                            item: item,
                            topY: topY,
                            bottomY: Math.max(topY, bottomY),
                            tall: item.height > height
                        };
                    }

                    function ensureReplicaItem(index) {
                        var item = itemAtIndex(index);
                        if (!item) {
                            positionViewAtIndex(index, ListView.Beginning);
                            forceLayout();
                            item = itemAtIndex(index);
                        }
                        return item;
                    }

                    function cancelLocalNavigation() {
                        localNavigationTimer.stop();
                        localNavigationActive = false;
                        localNavigationTargetIndex = -1;
                        localNavigationLastTargetY = Number.NaN;
                        localNavigationStablePasses = 0;
                        localNavigationVerifying = false;
                    }

                    function materializeLocalNavigationIndex(index) {
                        // Clicking a replica inside the teleprompter means its
                        // delegate is already alive.  Repositioning such an
                        // item to Center exposes an internal measurement step
                        // as a visible jump before the real focus animation.
                        var item = itemAtIndex(index);
                        if (item) {
                            return item;
                        }
                        // Resolve the requested variable-height delegate
                        // before calculating a pixel target. Repeatedly
                        // rebasing at the beginning would make ListView's
                        // virtual origin drift for very tall replicas.
                        positionViewAtIndex(index, ListView.Center);
                        forceLayout();
                        return itemAtIndex(index);
                    }

                    function queueLocalNavigation(index) {
                        index = Number(index);
                        if (!isFinite(index) || index < 0) {
                            cancelLocalNavigation();
                            return;
                        }
                        localNavigationTimer.stop();
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageScrollTargetIndex = -1;
                        pageGapPrefetchIndex = -1;
                        localNavigationActive = true;
                        localNavigationTargetIndex = index;
                        localNavigationLastTargetY = Number.NaN;
                        localNavigationStablePasses = 0;
                        localNavigationVerifying = false;

                        // A distant variable-height delegate has to be
                        // materialized before its final coordinate is known.
                        // A visible clicked delegate is reused in place and
                        // therefore never passes through ListView.Center.
                        materializeLocalNavigationIndex(index);
                        localNavigationTimer.restart();
                    }

                    function startQueuedLocalNavigation() {
                        if (!localNavigationActive) {
                            return;
                        }
                        var index = localNavigationTargetIndex;
                        if (index < 0) {
                            cancelLocalNavigation();
                            return;
                        }
                        var item = materializeLocalNavigationIndex(index);
                        if (!item) {
                            localNavigationTimer.restart();
                            return;
                        }
                        var bounds = replicaReadingBounds(index);
                        if (!bounds) {
                            localNavigationTimer.restart();
                            return;
                        }
                        // item.y is not stable across ListView origin changes.
                        // Ask ListView for the selected index's real beginning
                        // and derive the custom focus offset from that known
                        // position instead of an estimated delegate Y.
                        var sourceY = Number(contentY);
                        var targetY = Number(item.y)
                            - preferredHighlightBegin;
                        contentY = sourceY;
                        capturePageDebug(
                            "Локальная навигация к началу реплики",
                            sourceY, targetY, item.y, item.y + item.height
                        );
                        if (Math.abs(targetY - sourceY) <= 0.5) {
                            contentY = targetY;
                            finishLocalNavigation();
                            return;
                        }
                        if (pageScrollMode) {
                            startPageScroll(sourceY, targetY, index);
                            return;
                        }
                        longReplicaScrollAnimation.from = sourceY;
                        longReplicaScrollAnimation.to = targetY;
                        // A direct click is not racing playback.  Preserve
                        // the selected smoothness instead of capping it by the
                        // clicked replica's own timing.
                        longReplicaScrollAnimation.duration = scrollDurationForMove(
                            sourceY, targetY, -1
                        );
                        longReplicaScrollAnimation.start();
                    }

                    function indexAtReadingFocus() {
                        var focusY = contentY + preferredHighlightBegin;
                        for (var offset = 1; offset <= 24; offset += 3) {
                            var index = indexAt(width / 2, focusY + offset);
                            if (index >= 0) {
                                return index;
                            }
                        }
                        return -1;
                    }

                    function finishLocalNavigation() {
                        if (!localNavigationActive) {
                            return;
                        }
                        var index = localNavigationTargetIndex;
                        forceLayout();
                        if (index < 0) {
                            cancelLocalNavigation();
                            return;
                        }
                        var observedIndex = indexAtReadingFocus();
                        var item = itemAtIndex(index);
                        if (observedIndex !== index || !item) {
                            item = materializeLocalNavigationIndex(index);
                        }
                        var bounds = item ? replicaReadingBounds(index) : null;
                        if (!bounds || !itemAtIndex(index)) {
                            localNavigationVerifying = true;
                            localNavigationTimer.restart();
                            return;
                        }
                        // Delegate estimates can still refine while an
                        // animation is running. Resolve the final coordinate
                        // from the clicked index, never from a stale pixel Y.
                        var targetY = Number(bounds.item.y)
                            - preferredHighlightBegin;
                        var coordinateStable = isFinite(
                            localNavigationLastTargetY
                        ) && Math.abs(
                            localNavigationLastTargetY - targetY
                        ) <= 0.5;
                        contentY = targetY;
                        forceLayout();
                        var indexStable = indexAtReadingFocus() === index;
                        localNavigationLastTargetY = targetY;
                        localNavigationStablePasses = coordinateStable
                                && indexStable
                            ? localNavigationStablePasses + 1 : 0;
                        capturePageDebug(
                            "Локальная навигация завершена",
                            contentY, targetY,
                            bounds.item.y,
                            bounds.item.y + bounds.item.height
                        );
                        if (!indexStable) {
                            // A full second positioning pass is more reliable
                            // than repeatedly correcting a delegate coordinate
                            // derived from the same stale ListView estimate.
                            localNavigationLastTargetY = Number.NaN;
                            localNavigationStablePasses = 0;
                            localNavigationVerifying = false;
                            localNavigationTimer.restart();
                            return;
                        }
                        if (localNavigationStablePasses < 2) {
                            localNavigationVerifying = true;
                            localNavigationTimer.restart();
                            return;
                        }
                        cancelLocalNavigation();
                    }

                    function replicaTimeProgress(index) {
                        var replica = window.teleprompter.model.get(index);
                        if (!replica) {
                            return 0;
                        }
                        var start = Number(replica.start);
                        var end = Number(replica.end);
                        if (!isFinite(start) || !isFinite(end) || end <= start) {
                            return 0;
                        }
                        return Math.max(0, Math.min(
                            1, (Number(window.teleprompter.time) - start) / (end - start)
                        ));
                    }

                    function pageFragmentStep() {
                        // A page starts at the reading focus.  Its useful
                        // length is consequently the space below that line,
                        // minus a little overlap for reading continuity.
                        return Math.max(
                            1, height - preferredHighlightBegin
                            - window.config.f_text * 1.5
                        );
                    }

                    function sourceTimedContinuousTarget(index, bounds) {
                        var guides = bounds.item.laidOutTimingGuides();
                        if (!guides || guides.length <= 0) {
                            return Number.NaN;
                        }
                        var replica = window.teleprompter.model.get(index);
                        var currentTime = Number(window.teleprompter.time);
                        var previousTime = Number(replica.start);
                        var previousY = bounds.item.replicaTextTop();
                        var cursorY = previousY;
                        var resolved = false;
                        for (var guideIndex = 0;
                                guideIndex < guides.length;
                                guideIndex++) {
                            var guide = guides[guideIndex];
                            var guideTime = Number(guide.end);
                            if (currentTime <= guideTime) {
                                var duration = Math.max(
                                    0.001, guideTime - previousTime
                                );
                                var fraction = Math.max(0, Math.min(
                                    1, (currentTime - previousTime) / duration
                                ));
                                cursorY = previousY
                                    + (Number(guide.y) - previousY) * fraction;
                                resolved = true;
                                break;
                            }
                            previousTime = guideTime;
                            previousY = Number(guide.y);
                        }
                        if (!resolved) {
                            var replicaEnd = Number(replica.end);
                            var tailDuration = Math.max(
                                0.001, replicaEnd - previousTime
                            );
                            var tailFraction = Math.max(0, Math.min(
                                1, (currentTime - previousTime) / tailDuration
                            ));
                            cursorY = previousY + (
                                bounds.item.replicaTextBottom() - previousY
                            ) * tailFraction;
                        }
                        var readingBottom = preferredHighlightBegin
                            + pageFragmentStep();
                        pageDebugTimingSource = "ASS: плавная";
                        return Math.max(bounds.topY, Math.min(
                            bounds.bottomY,
                            clampedContentY(
                                bounds.item.y + cursorY - readingBottom
                            )
                        ));
                    }

                    function pageTransitionForFragment(
                            index, page, bounds, step, lastPage,
                            previousThreshold) {
                        var replica = window.teleprompter.model.get(index);
                        var guides = bounds.item.laidOutTimingGuides();
                        var focusY = bounds.topY + preferredHighlightBegin
                            - bounds.item.y;
                        var fragmentTop = focusY + page * step;
                        var fragmentBottom = focusY + (page + 1) * step;
                        var selected = null;
                        for (var guideIndex = 0;
                                guideIndex < guides.length;
                                guideIndex++) {
                            var guide = guides[guideIndex];
                            var guideY = Number(guide.y);
                            if (guideY > fragmentTop + 0.5
                                    && guideY <= fragmentBottom + 0.5
                                    && Number(guide.end) > previousThreshold) {
                                selected = guide;
                            }
                        }
                        if (selected) {
                            return {
                                time: Number(selected.end),
                                source: "ASS: конец строки " + selected.sourceId
                            };
                        }

                        // A source line can itself span more than one visual
                        // fragment (as in the problematic 8:28 ASS line).
                        // Such a page has no safe source boundary, so retain
                        // the proportional visual fallback without inventing
                        // line-level timing.
                        var start = Number(replica.start);
                        var end = Number(replica.end);
                        var renderedHeight = bounds.item.height;
                        var threshold = start + Math.min(
                            1, (page + 1) * step / renderedHeight
                        ) * (end - start);
                        if (threshold <= previousThreshold) {
                            threshold = previousThreshold + (
                                end - previousThreshold
                            ) / Math.max(1, lastPage - page);
                        }
                        return {
                            time: threshold,
                            source: guides.length > 0
                                ? "визуальный fallback"
                                : "визуальный"
                        };
                    }

                    function longReplicaTargetY(index, pageMode) {
                        var bounds = replicaReadingBounds(index);
                        if (!bounds || !bounds.tall) {
                            pageDebugRenderedHeight = bounds ? bounds.item.height : 0;
                            pageDebugProgress = replicaTimeProgress(index);
                            pageDebugPage = 0;
                            pageDebugPageCount = 1;
                            pageDebugTimingSource = "не требуется";
                            pageDebugThresholdTime = -1;
                            return bounds ? bounds.topY : contentY;
                        }
                        var distance = bounds.bottomY - bounds.topY;
                        var progress = replicaTimeProgress(index);
                        // Advance when playback reaches the corresponding
                        // visual boundary in the actual rendered text.  Do
                        // not divide time equally by the number of pages: a
                        // short final remainder would then make every earlier
                        // transition premature and add a useless last jump.
                        var step = pageFragmentStep();
                        var renderedHeight = bounds.item.height;
                        var lastPage = Math.max(
                            0, Math.floor((renderedHeight - 1) / step)
                        );
                        pageDebugRenderedHeight = renderedHeight;
                        pageDebugProgress = progress;
                        pageDebugPageCount = lastPage + 1;
                        if (!pageMode || distance <= 0) {
                            var timedTarget = sourceTimedContinuousTarget(
                                index, bounds
                            );
                            var target = isFinite(timedTarget)
                                ? timedTarget
                                : bounds.topY + distance * progress;
                            if (!isFinite(timedTarget)) {
                                pageDebugTimingSource = "визуальный";
                            }
                            pageDebugPage = Math.min(
                                lastPage,
                                Math.max(0, Math.floor(
                                    (target - bounds.topY) / step
                                ))
                            );
                            pageDebugThresholdTime = -1;
                            return target;
                        }
                        var replica = window.teleprompter.model.get(index);
                        var currentTime = Number(window.teleprompter.time);
                        var previousThreshold = Number(replica.start);
                        var page = 0;
                        var nextTransition = {
                            time: Number(replica.end),
                            source: "конец реплики"
                        };
                        for (var fragment = 0;
                                fragment < lastPage;
                                fragment++) {
                            var transition = pageTransitionForFragment(
                                index, fragment, bounds, step, lastPage,
                                previousThreshold
                            );
                            if (currentTime + 0.0005 < transition.time) {
                                nextTransition = transition;
                                break;
                            }
                            page = fragment + 1;
                            previousThreshold = transition.time;
                        }
                        pageDebugPage = page;
                        pageDebugTimingSource = nextTransition.source;
                        pageDebugThresholdTime = nextTransition.time;
                        return Math.min(bounds.bottomY, bounds.topY + page * step);
                    }

                    function followCurrentLongReplica() {
                        if (pageScrollMode || !window.followEnabled
                                || manualDragScroll || localNavigationActive
                                || currentIndex < 0) {
                            return;
                        }
                        forceLayout();
                        // Materializing a distant delegate can change originY.
                        // Establish the ListView coordinate system first, then
                        // capture the animation source in that same system.
                        if (!ensureReplicaItem(currentIndex)) {
                            capturePageDebug(
                                "Обычный режим: реплика не создана",
                                contentY, contentY, -1, -1
                            );
                            return;
                        }
                        var sourceY = clampedContentY(contentY);
                        contentY = sourceY;
                        var bounds = replicaReadingBounds(currentIndex);
                        var targetY = longReplicaTargetY(currentIndex, false);
                        var itemTop = bounds ? bounds.item.y : -1;
                        var itemBottom = bounds
                            ? bounds.item.y + bounds.item.height : -1;
                        if (!bounds || Math.abs(targetY - sourceY) <= 0.5) {
                            capturePageDebug(
                                bounds ? "Обычный режим: цель достигнута"
                                    : "Обычный режим: реплика не создана",
                                sourceY, targetY, itemTop, itemBottom
                            );
                            return;
                        }
                        if (!bounds.tall && longReplicaScrollAnimation.running
                                && Math.abs(longReplicaScrollAnimation.to - targetY) <= 0.5) {
                            return;
                        }
                        var retargetThreshold = Math.max(
                            2, Number(window.config.f_text) * 0.12
                        );
                        if (bounds.tall && longReplicaScrollAnimation.running
                                && Math.abs(
                                    longReplicaScrollAnimation.to - targetY
                                ) <= retargetThreshold) {
                            return;
                        }
                        longReplicaScrollAnimation.stop();
                        capturePageDebug(
                            bounds.tall
                                ? "Обычный режим: длинная реплика"
                                : "Обычный режим: переход к реплике",
                            sourceY, targetY, itemTop, itemBottom
                        );
                        longReplicaScrollAnimation.from = sourceY;
                        longReplicaScrollAnimation.to = targetY;
                        longReplicaScrollAnimation.duration = scrollDurationForMove(
                            sourceY, targetY,
                            continuousScrollDeadline(currentIndex, bounds)
                        );
                        longReplicaScrollAnimation.start();
                    }

                    function currentReplicaFocusTargetY() {
                        return replicaFocusTargetY(currentIndex);
                    }

                    function updatePageTargetHighlightGeometry(index, targetY) {
                        pageTargetHighlightLineOnly = false;
                        pageTargetHighlightX = 0;
                        pageTargetHighlightY = 0;
                        pageTargetHighlightWidth = 0;
                        pageTargetHighlightHeight = 0;
                        var bounds = replicaReadingBounds(index);
                        if (!bounds || !bounds.tall) {
                            return;
                        }
                        var geometry = bounds.item.targetLineHighlightGeometry(
                            targetY
                        );
                        if (!geometry) {
                            return;
                        }
                        pageTargetHighlightLineOnly = true;
                        pageTargetHighlightX = Number(geometry.x);
                        pageTargetHighlightY = Number(geometry.y);
                        pageTargetHighlightWidth = Number(geometry.width);
                        pageTargetHighlightHeight = Number(geometry.height);
                    }

                    function showPageTargetHighlight(index, targetY) {
                        pageTargetHighlightFade.stop();
                        if (!Boolean(window.config.page_target_highlight_enabled)) {
                            pageTargetHighlightIndex = -1;
                            pageTargetHighlightOpacity = 0;
                            pageTargetHighlightLineOnly = false;
                            return;
                        }
                        pageTargetHighlightIndex = index;
                        updatePageTargetHighlightGeometry(index, targetY);
                        pageTargetHighlightOpacity = window.targetHighlightOpacity;
                    }

                    function fadePageTargetHighlight() {
                        if (pageTargetHighlightOpacity <= 0) {
                            return;
                        }
                        pageTargetHighlightFade.stop();
                        pageTargetHighlightFade.from = pageTargetHighlightOpacity;
                        pageTargetHighlightFade.to = 0;
                        pageTargetHighlightFade.start();
                    }

                    function scrollDurationForMove(
                            sourceY, targetY, deadline) {
                        // The slider is a smoothness level, not a literal
                        // duration.  Short movements retain more of the
                        // configured smoothness through a sublinear distance
                        // curve, while a full-screen movement uses the whole
                        // internal duration represented by the level.
                        var screenDistance = Math.max(1, pageFragmentStep());
                        var distanceScreens = Math.abs(
                            targetY - sourceY
                        ) / screenDistance;
                        var distanceFactor = Math.pow(
                            Math.min(1, distanceScreens), 0.65
                        );
                        var desiredDuration = Math.max(
                            80, Math.round(
                                window.scrollDurationMs * distanceFactor
                            )
                        );
                        var duration = desiredDuration;
                        var currentTime = Number(window.teleprompter.time);
                        var availableDuration = -1;
                        var limit = "плавность";
                        if (isFinite(deadline) && deadline > currentTime) {
                            // Finish just before the next timed target.  The
                            // fixed reserve absorbs OSC and frame scheduling
                            // jitter without making long intervals feel fast.
                            availableDuration = Math.max(80, Math.round(
                                (deadline - currentTime) * 1000 - 100
                            ));
                            duration = Math.min(
                                desiredDuration, availableDuration
                            );
                            if (duration < desiredDuration) {
                                limit = "дедлайн";
                            }
                        } else if (isFinite(deadline) && deadline >= 0) {
                            availableDuration = 0;
                            duration = 80;
                            limit = "дедлайн прошёл";
                        }
                        scrollDebugSmoothnessLevel = window.scrollSmoothnessLevel;
                        scrollDebugDistanceScreens = distanceScreens;
                        scrollDebugDesiredDurationMs = desiredDuration;
                        scrollDebugAvailableDurationMs = availableDuration;
                        scrollDebugActualDurationMs = Math.round(duration);
                        scrollDebugDeadline = isFinite(deadline) ? deadline : -1;
                        scrollDebugDurationLimit = limit;
                        return Math.round(duration);
                    }

                    function nextActiveReplicaStart(index) {
                        for (var candidateIndex = index + 1;
                                candidateIndex < count; candidateIndex++) {
                            var candidate = window.teleprompter.model.get(
                                candidateIndex
                            );
                            if (candidate && candidate.active) {
                                return Number(candidate.start);
                            }
                        }
                        return -1;
                    }

                    function continuousScrollDeadline(index, bounds) {
                        var replica = window.teleprompter.model.get(index);
                        if (!replica) {
                            return -1;
                        }
                        var currentTime = Number(window.teleprompter.time);
                        if (bounds && bounds.tall) {
                            var guides = bounds.item.laidOutTimingGuides();
                            for (var guideIndex = 0;
                                    guides && guideIndex < guides.length;
                                    guideIndex++) {
                                var guideEnd = Number(guides[guideIndex].end);
                                if (isFinite(guideEnd)
                                        && guideEnd > currentTime + 0.0005) {
                                    return guideEnd;
                                }
                            }
                        }
                        var nextStart = nextActiveReplicaStart(index);
                        return isFinite(nextStart) && nextStart >= 0
                            ? nextStart : Number(replica.end);
                    }

                    function pageScrollDurationForTarget(
                            sourceY, targetY, targetIndex) {
                        var replica = window.teleprompter.model.get(targetIndex);
                        if (localNavigationActive) {
                            return scrollDurationForMove(sourceY, targetY, -1);
                        }
                        var deadline = targetIndex === currentIndex
                            ? Number(pageDebugThresholdTime)
                            : replica ? Number(replica.start) : -1;
                        if (!isFinite(deadline)
                                || deadline <= Number(window.teleprompter.time)) {
                            var nextStart = nextActiveReplicaStart(targetIndex);
                            deadline = isFinite(nextStart) && nextStart >= 0
                                ? nextStart
                                : replica ? Number(replica.end) : -1;
                        }
                        return scrollDurationForMove(sourceY, targetY, deadline);
                    }

                    function startPageScroll(sourceY, targetY, targetIndex) {
                        if (pageScrollAnimation.running
                                && pageScrollTargetIndex === targetIndex
                                && Math.abs(pageScrollAnimation.to - targetY) <= 0.5) {
                            return;
                        }
                        pageScrollAnimation.stop();
                        showPageTargetHighlight(targetIndex, targetY);
                        pageScrollTargetIndex = targetIndex;
                        pageScrollAnimation.from = sourceY;
                        pageScrollAnimation.to = targetY;
                        pageScrollAnimation.duration = pageScrollDurationForTarget(
                            sourceY, targetY, targetIndex
                        );
                        pageScrollAnimation.start();
                    }

                    function exactPageTargetY(index) {
                        if (!itemAtIndex(index)) {
                            positionViewAtIndex(index, ListView.Beginning);
                            forceLayout();
                        }
                        if (index === currentIndex) {
                            return longReplicaTargetY(index, true);
                        }
                        return replicaFocusTargetY(index);
                    }

                    function positionReplicaExactly(index, event) {
                        if (index < 0) {
                            return;
                        }
                        pageScrollTargetIndex = -1;
                        pageScrollAnimation.stop();
                        var targetY = exactPageTargetY(index);
                        contentY = targetY;
                        var item = itemAtIndex(index);
                        var itemTop = item ? item.y : targetY;
                        var itemBottom = item ? itemTop + item.height : itemTop;
                        capturePageDebug(event, targetY, targetY, itemTop, itemBottom);
                        showPageTargetHighlight(index, targetY);
                        fadePageTargetHighlight();
                    }

                    function correctPageScrollTarget() {
                        var index = pageScrollTargetIndex;
                        pageScrollTargetIndex = -1;
                        if (!pageScrollMode || manualDragScroll || index < 0) {
                            return;
                        }
                        // contentY is only an estimate while variable-height
                        // delegates between source and target are being made.
                        // Resolve the final position from the target index.
                        var sourceY = contentY;
                        var targetY = exactPageTargetY(index);
                        contentY = targetY;
                        updatePageTargetHighlightGeometry(index, targetY);
                        var item = itemAtIndex(index);
                        var itemTop = item ? item.y : targetY;
                        var itemBottom = item ? item.y + item.height : targetY;
                        capturePageDebug(
                            "Коррекция конечной позиции",
                            sourceY, targetY, itemTop, itemBottom
                        );
                    }

                    function followCurrentReplicaByPage() {
                        if (!pageScrollMode) {
                            return;
                        }
                        if (localNavigationActive) {
                            return;
                        }
                        if (!window.followEnabled) {
                            capturePageDebug("Пропуск: следование выключено", contentY, contentY, -1, -1);
                            return;
                        }
                        if (currentIndex < 0) {
                            capturePageDebug("Пропуск: нет текущей реплики", contentY, contentY, -1, -1);
                            return;
                        }
                        if (pageScrollHoldUntil >= 0) {
                            capturePageDebug("Пропуск: ручная пауза", contentY, contentY, -1, -1);
                            return;
                        }
                        if (pageFocusAlignmentActive) {
                            capturePageDebug("Пропуск: выравнивание по клику", contentY, contentY, -1, -1);
                            return;
                        }
                        if (manualDragScroll) {
                            capturePageDebug("Пропуск: ручное перетаскивание", contentY, contentY, -1, -1);
                            return;
                        }
                        // During a gap the next replica owns the scroll
                        // position, including after its animation has already
                        // finished.  Do not let the queued follow for the
                        // previous currentIndex pull the view back.
                        if (pageGapPrefetchIndex >= 0
                                && pageGapPrefetchIndex !== currentIndex) {
                            return;
                        }
                        var previousIndex = lastPageFollowIndex;
                        lastPageFollowIndex = currentIndex;
                        if (previousIndex < 0
                                || window.teleprompter.positionOrigin === "local"
                                || Math.abs(currentIndex - previousIndex) > 1) {
                            // A REAPER click or a repeated one-second step can
                            // skip several short replicas.  It is still not a
                            // page turn while the destination remains fully
                            // visible on the current page.
                            if (!replicaInsideCurrentPage(currentIndex)) {
                                positionReplicaExactly(
                                    currentIndex,
                                    "Точное позиционирование по индексу"
                                );
                                return;
                            }
                        }
                        forceLayout();
                        if (!ensureReplicaItem(currentIndex)) {
                            capturePageDebug(
                                "Постраничный режим: реплика не создана",
                                contentY, contentY, -1, -1
                            );
                            return;
                        }
                        var sourceY = clampedContentY(contentY);
                        contentY = sourceY;
                        var targetY = longReplicaTargetY(currentIndex, true);
                        var targetItem = itemAtIndex(currentIndex);
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        var viewportBottom = sourceY + height;
                        contentY = sourceY;
                        // OSC position updates arrive much faster than the
                        // configured animation duration. Keep an unchanged
                        // target running, but allow the next screen fragment
                        // of the same long replica to retarget the animation.
                        if (pageScrollAnimation.running
                                && pageScrollTargetIndex === currentIndex
                                && Math.abs(
                                    pageScrollAnimation.to - targetY
                                ) <= 0.5) {
                            capturePageDebug(
                                "Анимация к фокусу продолжается",
                                sourceY, pageScrollAnimation.to,
                                itemTop, itemBottom
                            );
                            return;
                        }
                        var animationNeedsRetarget = false;
                        if (pageScrollAnimation.running) {
                            var finalViewportTop = pageScrollAnimation.to;
                            var finalViewportBottom = finalViewportTop + height;
                            animationNeedsRetarget = itemTop < finalViewportTop
                                || itemBottom > finalViewportBottom;
                            if (!animationNeedsRetarget) {
                                capturePageDebug(
                                    "Текущий переход уже открывает реплику",
                                    sourceY, finalViewportTop,
                                    itemTop, itemBottom
                                );
                                return;
                            }
                        }
                        if (animationNeedsRetarget
                                || itemTop < sourceY
                                || itemBottom > viewportBottom) {
                            capturePageDebug("Переход к реплике", sourceY, targetY, itemTop, itemBottom);
                            if (Math.abs(targetY - sourceY) > 0.5) {
                                startPageScroll(sourceY, targetY, currentIndex);
                            }
                        } else {
                            capturePageDebug("Реплика уже видима", sourceY, targetY, itemTop, itemBottom);
                        }
                    }

                    function prefetchNextReplicaDuringGap() {
                        if (!pageScrollMode || !window.followEnabled
                                || pageScrollHoldUntil >= 0
                                || pageFocusAlignmentActive || manualDragScroll
                                || currentIndex < 0) {
                            return;
                        }
                        var currentReplica = window.teleprompter.model.get(currentIndex);
                        if (!currentReplica) {
                            return;
                        }
                        var nextIndex = -1;
                        for (var index = currentIndex + 1; index < count; index++) {
                            var candidate = window.teleprompter.model.get(index);
                            if (candidate && candidate.active) {
                                nextIndex = index;
                                break;
                            }
                        }
                        if (nextIndex < 0) {
                            pageGapPrefetchIndex = -1;
                            return;
                        }
                        var nextReplica = window.teleprompter.model.get(nextIndex);
                        var currentEnd = Number(currentReplica.end);
                        var nextStart = Number(nextReplica.start);
                        var gapThreshold = Number(
                            window.config.page_gap_prefetch_seconds || 0
                        );
                        var delay = Number(
                            window.config.page_gap_prefetch_delay_seconds || 0
                        );
                        var currentTime = Number(window.teleprompter.time);
                        if (gapThreshold <= 0
                                || nextStart - currentEnd < gapThreshold
                                || currentTime < currentEnd + delay
                                || currentTime >= nextStart) {
                            pageGapPrefetchIndex = -1;
                            return;
                        }
                        if (pageGapPrefetchIndex === nextIndex) {
                            return;
                        }
                        forceLayout();
                        var sourceY = contentY;
                        var targetItem = itemAtIndex(nextIndex);
                        if (!targetItem) {
                            // A seek can land deep inside a long gap, with the
                            // next delegate outside the instantiated range.
                            // Materializing it changes originY, so there is no
                            // safe old pixel coordinate to animate from.
                            pageGapPrefetchIndex = nextIndex;
                            positionReplicaExactly(
                                nextIndex,
                                "Пауза: точное позиционирование следующей реплики"
                            );
                            return;
                        }
                        var targetY = clampedContentY(
                            targetItem.y - preferredHighlightBegin
                        );
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        var viewportBottom = sourceY + height;
                        pageGapPrefetchIndex = nextIndex;
                        if (itemTop < sourceY || itemBottom > viewportBottom) {
                            capturePageDebug("Пауза: следующая реплика", sourceY, targetY, itemTop, itemBottom);
                            if (Math.abs(targetY - sourceY) > 0.5) {
                                startPageScroll(sourceY, targetY, nextIndex);
                            }
                        } else {
                            capturePageDebug("Пауза: следующая реплика уже видима", sourceY, targetY, itemTop, itemBottom);
                        }
                    }

                    function scrollCurrentReplicaToFocusBoundary() {
                        if (!pageScrollMode || currentIndex < 0) {
                            return;
                        }
                        pageGapPrefetchIndex = -1;
                        lastPageFollowIndex = currentIndex;
                        positionReplicaExactly(
                            currentIndex,
                            "Клик: точное выравнивание реплики к фокусу"
                        );
                    }

                    function queuePageFollow() {
                        if (pageFollowQueued) {
                            return;
                        }
                        pageFollowQueued = true;
                        Qt.callLater(function() {
                            pageFollowQueued = false;
                            followCurrentReplicaByPage();
                        });
                    }

                    function queueViewportFollow() {
                        if (viewportFollowQueued) {
                            return;
                        }
                        viewportFollowQueued = true;
                        Qt.callLater(function() {
                            viewportFollowQueued = false;
                            if (manualDragScroll || dragging || moving) {
                                return;
                            }
                            if (localNavigationActive) {
                                pageScrollAnimation.stop();
                                longReplicaScrollAnimation.stop();
                                forceLayout();
                                localNavigationTimer.restart();
                                return;
                            }
                            // Delegate heights change after a resize, a font
                            // update, or a mode switch.  Never continue an
                            // animation calculated for the old viewport.
                            pageScrollTargetIndex = -1;
                            pageScrollAnimation.stop();
                            longReplicaScrollAnimation.stop();
                            pageFocusAlignmentActive = false;
                            pageGapPrefetchIndex = -1;
                            forceLayout();
                            if (pageScrollMode) {
                                if (pageScrollHoldUntil >= 0) {
                                    pausePageFollowAtVisibleBoundary();
                                } else {
                                    followCurrentReplicaByPage();
                                }
                            } else {
                                followCurrentLongReplica();
                            }
                        });
                    }

                    function prepareForTimeSeek() {
                        manualWheelReleaseTimer.stop();
                        cancelLocalNavigation();
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageTargetHighlightFade.stop();
                        pageScrollTargetIndex = -1;
                        pageGapPrefetchIndex = -1;
                        lastPageFollowIndex = -1;
                        pageFocusAlignmentActive = false;
                        pageTargetHighlightIndex = -1;
                        pageTargetHighlightOpacity = 0;
                        pageTargetHighlightLineOnly = false;
                        manualDragScroll = false;
                        cancelPageHold();
                    }

                    function queueModelRefresh() {
                        if (modelRefreshQueued) {
                            return;
                        }
                        modelRefreshQueued = true;
                        Qt.callLater(function() {
                            modelRefreshQueued = false;
                            prepareForTimeSeek();
                            forceLayout();
                            queueViewportFollow();
                        });
                    }

                    function pausePageFollowAtVisibleBoundary() {
                        if (!pageScrollMode) {
                            return;
                        }
                        var viewportBottom = contentY + height;
                        var index = -1;
                        for (var probeY = viewportBottom - 1; probeY >= contentY; probeY -= 4) {
                            index = indexAt(width / 2, probeY);
                            if (index >= 0) {
                                break;
                            }
                        }
                        if (index < 0) {
                            cancelPageHold();
                            capturePageDebug("Пауза отменена: нет строки", contentY, contentY, -1, -1);
                            return;
                        }
                        var item = itemAtIndex(index);
                        if (item && item.y + item.height > viewportBottom) {
                            index -= 1;
                            item = itemAtIndex(index);
                        }
                        if (!item || item.y < contentY || item.y + item.height > viewportBottom) {
                            cancelPageHold();
                            capturePageDebug("Пауза отменена: строка вне экрана", contentY, contentY, -1, -1);
                            return;
                        }
                        pageScrollHoldUntil = Number(window.teleprompter.model.get(index).end);
                        pageHoldLastReaperTime = Number(window.teleprompter.time);
                        pageHoldLastReaperReceivedAt = Date.now();
                        capturePageDebug("Ручная пауза до конца строки " + index, contentY, contentY, item.y, item.y + item.height);
                    }

                    function resumePageFollowForReaperPosition() {
                        if (!pageScrollMode || pageScrollHoldUntil < 0) {
                            return;
                        }
                        var currentTime = Number(window.teleprompter.time);
                        var receivedAt = Date.now();
                        var elapsed = Math.max(
                            0,
                            (receivedAt - pageHoldLastReaperReceivedAt) / 1000
                        );
                        var delta = Math.abs(
                            currentTime - pageHoldLastReaperTime
                        );
                        var seekedBack = currentTime < pageHoldLastReaperTime - 0.02;
                        var jumped = delta >= Math.max(0.5, elapsed * 4);
                        var changedAfterPause = elapsed >= 0.75 && delta >= 0.02
                            && (delta > 3 || delta < elapsed * 0.5
                                || delta > elapsed * 3);
                        pageHoldLastReaperTime = currentTime;
                        pageHoldLastReaperReceivedAt = receivedAt;
                        if (seekedBack || jumped || changedAfterPause) {
                            // OSC does not distinguish a mouse seek from a
                            // held REAPER step command.  Both should preserve
                            // the current page while their destination is
                            // already visible; following resumes only once
                            // the playhead leaves that page.
                            if (replicaInsideCurrentPage(currentIndex)) {
                                capturePageDebug("Seek REAPER внутри текущей страницы", contentY, contentY, -1, -1);
                                return;
                            }
                            cancelPageHold();
                            capturePageDebug("Ручная пауза отменена: seek REAPER", contentY, contentY, -1, -1);
                            queuePageFollow();
                            return;
                        }
                        if (currentTime < pageScrollHoldUntil) {
                            return;
                        }
                        pageScrollHoldUntil = -1;
                        queuePageFollow();
                    }

                    function cancelPageHold() {
                        pageScrollHoldUntil = -1;
                        pageHoldLastReaperTime = -1;
                        pageHoldLastReaperReceivedAt = -1;
                    }

                    function resetPageFollowState() {
                        manualWheelReleaseTimer.stop();
                        cancelLocalNavigation();
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageTargetHighlightFade.stop();
                        pageFocusAlignmentActive = false;
                        pageGapPrefetchIndex = -1;
                        pageScrollTargetIndex = -1;
                        lastPageFollowIndex = -1;
                        pageTargetHighlightIndex = -1;
                        pageTargetHighlightOpacity = 0;
                        pageTargetHighlightLineOnly = false;
                        manualDragScroll = false;
                        cancelPageHold();
                    }

                    function beginManualDragScroll() {
                        manualWheelReleaseTimer.stop();
                        cancelLocalNavigation();
                        pageScrollTargetIndex = -1;
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageGapPrefetchIndex = -1;
                        manualDragScroll = true;
                        if (!pageScrollMode) {
                            window.followEnabled = false;
                        }
                    }

                    function finishManualDragScroll() {
                        if (!manualDragScroll) {
                            return;
                        }
                        if (pageScrollMode) {
                            // Establish the hold before releasing the manual
                            // guard, leaving no event-loop gap in which an OSC
                            // follow can overwrite the user's position.
                            pausePageFollowAtVisibleBoundary();
                        }
                        manualDragScroll = false;
                    }

                    onCurrentIndexChanged: {
                        var wasPrefetched = pageGapPrefetchIndex === currentIndex;
                        pageGapPrefetchIndex = -1;
                        if (!wasPrefetched || !pageScrollAnimation.running) {
                            queuePageFollow();
                        }
                    }
                    onHeightChanged: queueViewportFollow()
                    onWidthChanged: queueViewportFollow()
                    onPreferredHighlightBeginChanged: queueViewportFollow()
                    onContentHeightChanged: Qt.callLater(function() {
                        // contentHeight also changes while ListView creates
                        // and recycles delegates during a manual scroll.  It
                        // must not initiate automatic positioning.
                        var recovered = restoreValidContentBounds();
                        if (recovered && window.followEnabled
                                && !manualDragScroll && !dragging && !moving) {
                            queueViewportFollow();
                        }
                        if (pageScrollHoldUntil >= 0
                                && !manualDragScroll && !dragging && !moving) {
                            pausePageFollowAtVisibleBoundary();
                        }
                    })
                    onPageScrollModeChanged: {
                        pageGapPrefetchIndex = -1;
                        pageScrollTargetIndex = -1;
                        lastPageFollowIndex = -1;
                        cancelPageHold();
                        queueViewportFollow();
                    }
                    onDraggingChanged: {
                        if (dragging) {
                            beginManualDragScroll();
                        } else if (manualDragScroll && !moving) {
                            finishManualDragScroll();
                        }
                    }
                    onMovementEnded: finishManualDragScroll()
                    transform: Scale {
                        origin.x: replicaView.width / 2
                        xScale: window.config.is_mirrored ? -1 : 1
                    }

                    WheelHandler {
                        target: null
                        onWheel: function (event) {
                            // Set manualDragScroll synchronously so a page
                            // follow already queued by the latest OSC packet
                            // cannot undo this wheel step before the hold is
                            // calculated.
                            replicaView.beginManualDragScroll();
                            replicaView.contentY = replicaView.clampedContentY(
                                replicaView.contentY - event.angleDelta.y
                            );
                            manualWheelReleaseTimer.restart();
                            event.accepted = true;
                        }
                    }

                    delegate: Item {
                        id: replicaDelegate
                        required property int index
                        required property real start
                        required property string time
                        required property string endTime
                        required property string character
                        required property string actor
                        required property string replicaText
                        required property string actorColor
                        required property bool active
                        required property bool colorActive
                        required property var sourceIds
                        required property var timingGuides

                        readonly property real horizontalMargin: Math.max(8, replicaView.viewportWidth * 0.015)
                        readonly property real scenario3MetadataWidth: Math.min(
                            300,
                            Math.max(150, replicaView.viewportWidth * 0.24)
                        )
                        readonly property color blockBorderColor: window.colors.block_border || "#4D4D4D"
                        readonly property real pageTargetHighlightOpacity: (
                            replicaView.pageTargetHighlightIndex === index
                            && Boolean(window.config.page_target_highlight_enabled)
                        ) ? replicaView.pageTargetHighlightOpacity : 0
                        // Diagnostic-only guides show the boundaries used by
                        // the page target calculation for any oversized block,
                        // including one reached by manual scrolling.
                        readonly property real debugFragmentStep: replicaView.pageFragmentStep()
                        readonly property real debugFocusFragmentY: (
                            replicaView.contentY + replicaView.preferredHighlightBegin
                            - replicaDelegate.y
                        )
                        readonly property int debugFragmentCount: (
                            window.pageDebugVisible
                            && height > replicaView.height
                        ) ? Math.ceil(height / debugFragmentStep) + 2 : 0

                        x: horizontalMargin
                        width: replicaView.viewportWidth - horizontalMargin * 2
                        height: layoutContent.implicitHeight + (window.config.show_block_borders ? 20 : 18)
                        opacity: active ? 1 : 0.72

                        function timeRangeText(bracketed, multiline) {
                            var startText = window.displayedTimecode(time);
                            var endText = window.displayedTimecode(endTime);
                            if (bracketed) {
                                startText = "[" + startText + "]";
                                endText = "[" + endText + "]";
                            }
                            if (!Boolean(window.config.show_end_timecode)) {
                                return startText;
                            }
                            return startText + (multiline ? " -\n" : " - ")
                                + endText;
                        }

                        function activeReplicaTextItem() {
                            if (window.config.layout_template) {
                                return customLayoutRenderer.primaryTextItem;
                            }
                            if (window.config.layout_type === "Сценарий 1") {
                                return scenario1ReplicaBody;
                            }
                            if (window.config.layout_type === "Сценарий 2") {
                                return scenario2ReplicaBody;
                            }
                            return scenario3ReplicaBody;
                        }

                        function replicaTextTop() {
                            var item = activeReplicaTextItem();
                            return item ? item.mapToItem(replicaDelegate, 0, 0).y : 0;
                        }

                        function replicaTextBottom() {
                            var item = activeReplicaTextItem();
                            return item ? replicaTextTop() + item.height : height;
                        }

                        function laidOutTimingGuides() {
                            var item = activeReplicaTextItem();
                            if (!item || item.width <= 0 || !timingGuides
                                    || timingGuides.length <= 0) {
                                return [];
                            }
                            var top = replicaTextTop();
                            var result = [];
                            for (var guideIndex = 0;
                                    guideIndex < timingGuides.length;
                                    guideIndex++) {
                                var guide = timingGuides[guideIndex];
                                var endPosition = Math.max(
                                    0,
                                    Math.min(
                                        replicaText.length - 1,
                                        Number(guide.textEnd) - 1
                                    )
                                );
                                var cursorRect = timingTextLayout.positionToRectangle(
                                    endPosition
                                );
                                if (!cursorRect || !isFinite(cursorRect.y)) {
                                    continue;
                                }
                                result.push({
                                    sourceId: guide.sourceId,
                                    start: Number(guide.start),
                                    end: Number(guide.end),
                                    y: top + cursorRect.y + cursorRect.height
                                });
                            }
                            return result;
                        }

                        function targetLineHighlightGeometry(targetContentY) {
                            var textItem = activeReplicaTextItem();
                            if (!textItem || textItem.width <= 0
                                    || timingTextLayout.contentHeight <= 0) {
                                return null;
                            }
                            var mapped = textItem.mapToItem(
                                replicaDelegate, 0, 0
                            );
                            var focusY = Number(targetContentY)
                                + replicaView.preferredHighlightBegin
                                - replicaDelegate.y;
                            var textY = Math.max(0, Math.min(
                                timingTextLayout.contentHeight - 1,
                                focusY - mapped.y + 1
                            ));
                            var position = timingTextLayout.positionAt(1, textY);
                            var cursorRect = timingTextLayout.positionToRectangle(
                                Math.max(0, position)
                            );
                            if (!cursorRect || !isFinite(cursorRect.y)
                                    || !isFinite(cursorRect.height)) {
                                return null;
                            }
                            return {
                                x: mapped.x,
                                y: mapped.y + cursorRect.y,
                                width: textItem.width,
                                height: Math.max(
                                    cursorRect.height,
                                    Number(window.config.f_text) * 1.15
                                )
                            };
                        }

                        // Use the same Qt text layout engine as the visible
                        // Text items to translate UTF-16 source offsets into
                        // rendered Y coordinates.  It does not participate in
                        // the visual layout.
                        TextEdit {
                            id: timingTextLayout
                            x: -100000
                            y: 0
                            width: Math.max(
                                1,
                                replicaDelegate.activeReplicaTextItem()
                                    ? replicaDelegate.activeReplicaTextItem().width
                                    : replicaDelegate.width
                            )
                            height: contentHeight
                            opacity: 0
                            readOnly: true
                            activeFocusOnPress: false
                            textMargin: 0
                            text: replicaDelegate.replicaText
                            font.pixelSize: window.config.f_text
                            font.bold: window.config.bold_text
                            wrapMode: TextEdit.WordWrap
                        }

                        Rectangle {
                            x: replicaView.pageTargetHighlightLineOnly
                                ? replicaView.pageTargetHighlightX : 0
                            y: replicaView.pageTargetHighlightLineOnly
                                ? replicaView.pageTargetHighlightY : 0
                            width: replicaView.pageTargetHighlightLineOnly
                                ? replicaView.pageTargetHighlightWidth
                                : parent.width
                            height: replicaView.pageTargetHighlightLineOnly
                                ? replicaView.pageTargetHighlightHeight
                                : parent.height
                            color: window.colors.page_target_highlight || "#FFD54F"
                            opacity: replicaDelegate.pageTargetHighlightOpacity
                            radius: window.macOSStyle ? 5 : 3
                        }

                        Rectangle {
                            anchors.fill: parent
                            visible: window.config.show_block_borders
                            color: "transparent"
                            radius: window.macOSStyle ? 5 : 3
                            border.width: 1
                            border.color: replicaDelegate.blockBorderColor
                        }

                        Repeater {
                            model: replicaDelegate.debugFragmentCount

                            delegate: Item {
                                id: fragmentGuide
                                required property int index

                                x: 0
                                // The current fragment begins at the focus
                                // line.  Keep all diagnostic separators in
                                // that coordinate system, rather than from
                                // the top edge of the replica.
                                y: replicaDelegate.debugFocusFragmentY
                                    + index * replicaDelegate.debugFragmentStep
                                width: replicaDelegate.width
                                height: 18
                                z: 3
                                visible: y >= 0 && y <= replicaDelegate.height

                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width
                                    height: 1
                                    color: "#45D9FFFF"
                                }
                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: fragmentLabel.implicitWidth + 12
                                    height: fragmentLabel.implicitHeight + 4
                                    radius: 3
                                    color: "#D9103344"

                                    Text {
                                        id: fragmentLabel
                                        anchors.centerIn: parent
                                        text: qsTr("Фрагмент %1").arg(fragmentGuide.index + 1)
                                        color: "#B8F4FF"
                                        font.pixelSize: Math.max(11, window.config.f_text * 0.35)
                                        font.bold: true
                                    }
                                }
                            }
                        }

                        // The background remains a navigation target; the
                        // character and dialogue themselves open the editor.
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                window.jumpToReplica(replicaDelegate.index);
                            }
                            onDoubleClicked: window.openReplicaEditor(replicaDelegate.sourceIds, replicaDelegate.character, replicaDelegate.replicaText)
                        }

                        ColumnLayout {
                            id: layoutContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: window.config.show_block_borders ? 10 : 0
                            anchors.rightMargin: window.config.show_block_borders ? 10 : 0
                            spacing: 4

                            ColumnLayout {
                                visible: !window.config.layout_template
                                    && window.config.layout_type === "Сценарий 1"
                                Layout.fillWidth: true
                                spacing: 4

                                RowLayout {
                                    visible: window.config.show_timecode
                                        || window.config.show_character
                                        || window.config.show_actor
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Text {
                                        visible: window.config.show_character
                                        text: replicaDelegate.character
                                        color: replicaDelegate.colorActive ? replicaDelegate.actorColor : (replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text)
                                        font.pixelSize: window.config.f_char
                                        font.bold: window.config.bold_char
                                        font.underline: scenario1CharacterArea.containsMouse

                                        MouseArea {
                                            id: scenario1CharacterArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: window.openReplicaEditor(replicaDelegate.sourceIds, replicaDelegate.character, replicaDelegate.replicaText)
                                        }
                                    }
                                    Text {
                                        visible: window.config.show_timecode
                                        text: replicaDelegate.timeRangeText(true, false)
                                        color: replicaDelegate.active ? window.colors.tc : window.colors.inactive_text
                                        font.pixelSize: window.config.f_tc
                                        font.bold: window.config.bold_tc
                                    }
                                    Text {
                                        visible: window.config.show_actor
                                        text: qsTr("(") + replicaDelegate.actor + ")"
                                        color: replicaDelegate.active ? window.colors.actor : window.colors.inactive_text
                                        font.pixelSize: window.config.f_actor
                                        font.bold: window.config.bold_actor
                                        font.italic: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                                Text {
                                    id: scenario1ReplicaBody
                                    visible: window.config.show_replica
                                    text: replicaDelegate.replicaText
                                    color: replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text
                                    font.pixelSize: window.config.f_text
                                    font.bold: window.config.bold_text
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignLeft
                                    Layout.fillWidth: true
                                }
                            }

                            ColumnLayout {
                                visible: !window.config.layout_template
                                    && window.config.layout_type === "Сценарий 2"
                                Layout.fillWidth: true
                                spacing: 6

                                RowLayout {
                                    visible: window.config.show_timecode
                                        || window.config.show_character
                                        || window.config.show_actor
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Text {
                                        visible: window.config.show_timecode
                                        text: replicaDelegate.timeRangeText(false, false)
                                        color: replicaDelegate.active ? window.colors.tc : window.colors.inactive_text
                                        font.pixelSize: window.config.f_tc
                                        font.bold: window.config.bold_tc
                                    }
                                    Text {
                                        visible: window.config.show_timecode
                                            && (window.config.show_character
                                                || window.config.show_actor)
                                        text: "|"
                                        color: window.colors.inactive_text
                                        font.pixelSize: window.config.f_tc
                                    }
                                    Text {
                                        visible: window.config.show_character
                                        text: replicaDelegate.character
                                        color: replicaDelegate.colorActive ? replicaDelegate.actorColor : (replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text)
                                        font.pixelSize: window.config.f_char
                                        font.bold: window.config.bold_char
                                        font.underline: scenario2CharacterArea.containsMouse
                                        MouseArea {
                                            id: scenario2CharacterArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: window.openReplicaEditor(replicaDelegate.sourceIds, replicaDelegate.character, replicaDelegate.replicaText)
                                        }
                                    }
                                    Text {
                                        visible: window.config.show_actor
                                            && window.config.show_character
                                        text: "|"
                                        color: window.colors.inactive_text
                                        font.pixelSize: window.config.f_actor
                                        font.bold: window.config.bold_actor
                                    }
                                    Text {
                                        visible: window.config.show_actor
                                        text: replicaDelegate.actor
                                        color: replicaDelegate.active ? window.colors.actor : window.colors.inactive_text
                                        font.pixelSize: window.config.f_actor
                                        font.italic: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                                Text {
                                    id: scenario2ReplicaBody
                                    visible: window.config.show_replica
                                    text: replicaDelegate.replicaText
                                    color: replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text
                                    font.pixelSize: window.config.f_text
                                    font.bold: window.config.bold_text
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignLeft
                                    Layout.fillWidth: true
                                }
                            }

                            RowLayout {
                                visible: !window.config.layout_template
                                    && window.config.layout_type === "Сценарий 3"
                                Layout.fillWidth: true
                                spacing: Math.max(16, window.config.f_text * 0.6)

                                ColumnLayout {
                                    visible: window.config.show_timecode
                                        || window.config.show_character
                                        || window.config.show_actor
                                    Layout.alignment: Qt.AlignTop
                                    Layout.minimumWidth: replicaDelegate.scenario3MetadataWidth
                                    Layout.preferredWidth: replicaDelegate.scenario3MetadataWidth
                                    Layout.maximumWidth: replicaDelegate.scenario3MetadataWidth
                                    spacing: 3
                                    Text {
                                        visible: window.config.show_timecode
                                        text: replicaDelegate.timeRangeText(false, true)
                                        color: replicaDelegate.active ? window.colors.tc : window.colors.inactive_text
                                        font.pixelSize: window.config.f_tc
                                        font.bold: window.config.bold_tc
                                    }
                                    Text {
                                        visible: window.config.show_character
                                        text: replicaDelegate.character
                                        color: replicaDelegate.colorActive ? replicaDelegate.actorColor : (replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text)
                                        font.pixelSize: window.config.f_char
                                        font.bold: window.config.bold_char
                                        font.underline: scenario3CharacterArea.containsMouse
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        MouseArea {
                                            id: scenario3CharacterArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: window.openReplicaEditor(replicaDelegate.sourceIds, replicaDelegate.character, replicaDelegate.replicaText)
                                        }
                                    }
                                    Text {
                                        visible: window.config.show_actor
                                        text: replicaDelegate.actor
                                        color: replicaDelegate.active ? window.colors.actor : window.colors.inactive_text
                                        font.pixelSize: window.config.f_actor
                                        font.bold: window.config.bold_actor
                                        font.italic: true
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                                Text {
                                    id: scenario3ReplicaBody
                                    visible: window.config.show_replica
                                    text: replicaDelegate.replicaText
                                    color: replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text
                                    font.pixelSize: window.config.f_text
                                    font.bold: window.config.bold_text
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignLeft
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignTop
                                }
                            }

                            LayoutTemplateFlat {
                                id: customLayoutRenderer
                                visible: Boolean(window.config.layout_template)
                                Layout.fillWidth: true
                                rows: window.config.layout_template_rows || []
                                replicaDelegate: replicaDelegate
                                windowConfig: window.config
                                colors: window.colors
                                onEditRequested: {
                                    window.openReplicaEditor(
                                        replicaDelegate.sourceIds,
                                        replicaDelegate.character,
                                        replicaDelegate.replicaText
                                    );
                                }
                            }
                        }
                    }
                    ScrollBar.vertical: VisibleScrollBar {
                        contentOverflow: false
                    }
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 12
                    width: Math.min(parent.width - 24, 560)
                    height: debugColumn.implicitHeight + 20
                    visible: window.pageDebugVisible
                    z: 10
                    radius: 6
                    color: "#DD111111"
                    border.width: 1
                    border.color: "#99FFFFFF"

                    Column {
                        id: debugColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 3

                        Text {
                            text: qsTr("Диагностика постраничного режима")
                            color: "#FFFFFF"
                            font.bold: true
                        }
                        Text {
                            text: "event: " + replicaView.pageDebugEvent
                            color: "#FFD166"
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                        Text {
                            text: "time=" + window.teleprompter.time.toFixed(3)
                                + "  index=" + replicaView.currentIndex
                                + "  follow=" + window.followEnabled
                            color: "#FFFFFF"
                        }
                        Text {
                            text: "viewport=" + replicaView.width.toFixed(1)
                                + " × " + replicaView.height.toFixed(1)
                                + "  contentHeight=" + replicaView.contentHeight.toFixed(1)
                            color: "#FFFFFF"
                        }
                        Text {
                            text: "contentY=" + replicaView.contentY.toFixed(1)
                                + "  sourceY=" + replicaView.pageDebugSourceY.toFixed(1)
                                + "  targetY=" + replicaView.pageDebugTargetY.toFixed(1)
                            color: "#FFFFFF"
                        }
                        Text {
                            text: "item=" + replicaView.pageDebugItemTop.toFixed(1)
                                + "…" + replicaView.pageDebugItemBottom.toFixed(1)
                                + "  holdUntil=" + replicaView.pageScrollHoldUntil.toFixed(3)
                            color: "#FFFFFF"
                        }
                        Text {
                            text: "fragmentStep=" + Math.max(
                                1, replicaView.pageFragmentStep()
                            ).toFixed(1)
                                + "  guides: cyan lines start at the focus line"
                            color: "#B8F4FF"
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                        Text {
                            text: "renderedHeight="
                                + replicaView.pageDebugRenderedHeight.toFixed(1)
                                + "  progress="
                                + (replicaView.pageDebugProgress * 100).toFixed(1)
                                + "%  page=" + (replicaView.pageDebugPage + 1)
                                + "/" + replicaView.pageDebugPageCount
                            color: "#B8F4FF"
                        }
                        Text {
                            text: "timing=" + replicaView.pageDebugTimingSource
                                + (replicaView.pageDebugThresholdTime >= 0
                                    ? "  next="
                                        + replicaView.pageDebugThresholdTime.toFixed(3)
                                    : "")
                            color: "#B8F4FF"
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                        Text {
                            text: "smoothness="
                                + replicaView.scrollDebugSmoothnessLevel + "%"
                                + "  distance="
                                + replicaView.scrollDebugDistanceScreens.toFixed(2)
                                + " screen"
                                + "  desired="
                                + replicaView.scrollDebugDesiredDurationMs + "ms"
                            color: "#B8F4FF"
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                        Text {
                            text: "budget="
                                + (replicaView.scrollDebugAvailableDurationMs >= 0
                                    ? replicaView.scrollDebugAvailableDurationMs + "ms"
                                    : "∞")
                                + "  actual="
                                + replicaView.scrollDebugActualDurationMs + "ms"
                                + "  limit="
                                + replicaView.scrollDebugDurationLimit
                                + (replicaView.scrollDebugDeadline >= 0
                                    ? "  deadline="
                                        + replicaView.scrollDebugDeadline.toFixed(3)
                                    : "")
                            color: "#B8F4FF"
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                        Rectangle {
                            width: parent.width
                            height: 1
                            color: "#55FFFFFF"
                        }
                        Row {
                            spacing: 5
                            CheckBox {
                                id: debugSimulatorToggle
                                text: qsTr("Mock REAPER")
                                checked: window.teleprompter.debugSimulationActive
                                onToggled: {
                                    window.debugSimulationRunning = false;
                                    window.teleprompter.debugSetSimulationActive(checked);
                                }
                            }
                            Button {
                                text: qsTr("−5 с")
                                onClicked: window.setDebugReaperTime(
                                    window.teleprompter.time - 5
                                )
                            }
                            Button {
                                text: window.debugSimulationRunning
                                    ? qsTr("Пауза") : qsTr("Play")
                                enabled: window.teleprompter.debugSimulationActive
                                onClicked: window.debugSimulationRunning
                                    = !window.debugSimulationRunning
                            }
                            Button {
                                text: qsTr("+5 с")
                                onClicked: window.setDebugReaperTime(
                                    window.teleprompter.time + 5
                                )
                            }
                            ComboBox {
                                id: debugSpeedBox
                                width: 82
                                model: ["0.25×", "1×", "4×", "16×"]
                                currentIndex: 1
                                onActivated: window.debugSimulationSpeed
                                    = [0.25, 1, 4, 16][currentIndex]
                            }
                        }
                        Row {
                            spacing: 5
                            TextField {
                                id: debugTimeField
                                width: 110
                                placeholderText: qsTr("8:28.31")
                                onAccepted: {
                                    var seconds = window.parseDebugTimecode(text);
                                    if (isFinite(seconds)) {
                                        window.setDebugReaperTime(seconds);
                                    }
                                }
                            }
                            Button {
                                text: qsTr("Перейти")
                                onClicked: debugTimeField.accepted()
                            }
                            Button {
                                text: qsTr("Очистить лог")
                                onClicked: {
                                    replicaView.pageDebugTrace = [];
                                    replicaView.pageDebugLastTraceSignature = "";
                                }
                            }
                        }
                        Text {
                            text: replicaView.pageDebugTrace.join("\n")
                            color: "#D9F7FF"
                            font.family: "Menlo"
                            font.pixelSize: 10
                            width: parent.width
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: replicaView.count === 0
                    text: qsTr("Рабочий текст серии не найден")
                    color: window.colors.active_text
                    font.pixelSize: 22
                }
            }
        }
    }
}
