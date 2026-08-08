pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

NativeDialogWindow {
    id: window

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
    transientParent: windowsStyle ? null : ownerWindow

    property bool sidePanelVisible: true
    property bool followEnabled: true
    property string observedEpisode: ""
    property var editingSourceIds: []
    property int colorTarget: -1
    readonly property var config: teleprompter.config
    readonly property var colors: config.colors
    readonly property bool pageDebugVisible: Boolean(config.page_debug_overlay)
    readonly property int scrollDurationMs: Math.round(
        150 * Math.pow(
            5000 / 150,
            Math.max(0, Math.min(
                100, Number(config.scroll_smoothness_slider || 0)
            )) / 100
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
        teleprompter.navigate(direction);
    }

    function jumpToReplica(seconds) {
        followEnabled = true;
        replicaView.cancelPageHold();
        teleprompter.jumpTo(seconds);
        Qt.callLater(function() {
            replicaView.scrollCurrentReplicaToFocusBoundary();
        });
    }

    function displayedTimecode(value) {
        var text = String(value || "")
        if (window.config.hide_leading_timecode_zeros
                && text.indexOf("0:") === 0) {
            return text.slice(2)
        }
        return text
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
                window.resetFollowingState();
            }
        }
        function onPositionChanged() {
            if (window.teleprompter.positionOrigin === "reaper"
                    && !replicaView.pageScrollMode
                    && !window.followEnabled) {
                window.followEnabled = true;
            }
            replicaView.followCurrentLongReplica();
            replicaView.queuePageFollow();
            if (window.teleprompter.positionOrigin === "reaper") {
                replicaView.resumePageFollowForReaperPosition();
                replicaView.prefetchNextReplicaDuringGap();
            }
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
        function onReplicaJumpRequested(seconds) {
            window.jumpToReplica(seconds);
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
        onAccepted: {
            var keys = ["bg", "active_text", "inactive_text", "tc", "actor", "header_bg", "header_text", "block_border"];
            if (window.colorTarget >= 0 && window.colorTarget < keys.length) {
                window.teleprompter.setConfigValue("colors." + keys[window.colorTarget], selectedColor.toString());
            }
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

        Rectangle {
            visible: window.config.show_header
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 86 : 0
            color: window.colors.header_bg

            Label {
                anchors.centerIn: parent
                text: window.displayedTimecode(window.teleprompter.timecode)
                color: window.colors.header_text
                font.pixelSize: Math.min(58, parent.height * 0.65)
                font.bold: true
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
                                    model: ["Фон", "Активный текст", "Неактивный текст", "Таймкод", "Актёр", "Фон заголовка", "Текст заголовка", "Границы блоков"]
                                    delegate: RowLayout {
                                        id: colorRow
                                        required property int index
                                        required property string modelData
                                        readonly property color swatchColor: [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_bg, window.colors.header_text, window.colors.block_border][colorRow.index]

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
                                                var values = [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_bg, window.colors.header_text, window.colors.block_border];
                                                window.colorTarget = colorRow.index;
                                                colorDialog.selectedColor = values[colorRow.index];
                                                colorDialog.open();
                                            }
                                        }
                                    }
                                }

                            }

                            CollapsibleSection {
                                title: qsTr("Прокрутка")
                                expanded: true
                                sidebarStyle: window.macOSStyle
                                Layout.fillWidth: true

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
                                CheckBox {
                                    text: qsTr("Постраничный режим")
                                    checked: Boolean(window.config.page_scroll_mode)
                                    onToggled: window.appBridge.settings.setPrompterPageScrollMode(checked)
                                    PlatformToolTip {
                                        target: parent
                                        text: qsTr("Прокручивать после последней полностью видимой реплики")
                                    }
                                }

                                Label {
                                    text: qsTr("Плавность · %1 мс").arg(window.scrollDurationMs)
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
                                        window.jumpToReplica(navigationRow.start);
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
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: window.colors.bg
                clip: true

                PersistentListView {
                    id: replicaView
                    anchors.fill: parent
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
                    property bool pageFocusAlignmentActive: false
                    property int pageGapPrefetchIndex: -1
                    // StrictlyEnforceRange fights direct contentY animation
                    // when a single delegate is taller than the viewport.
                    property int longReplicaIndex: -1
                    property int pageTargetHighlightIndex: -1
                    property real pageTargetHighlightOpacity: 0
                    property bool manualDragScroll: false
                    property string pageDebugEvent: "Ожидание"
                    property real pageDebugSourceY: 0
                    property real pageDebugTargetY: 0
                    property real pageDebugItemTop: -1
                    property real pageDebugItemBottom: -1
                    preferredHighlightBegin: height * focusSlider.value
                    preferredHighlightEnd: preferredHighlightBegin
                    highlightRangeMode: pageScrollMode || longReplicaIndex === currentIndex
                        ? ListView.NoHighlightRange : ListView.StrictlyEnforceRange
                    highlightMoveDuration: window.scrollDurationMs

                    NumberAnimation {
                        id: pageScrollAnimation
                        target: replicaView
                        property: "contentY"
                        duration: window.scrollDurationMs
                        easing.type: Easing.OutCubic
                        onStopped: {
                            replicaView.pageFocusAlignmentActive = false;
                            replicaView.fadePageTargetHighlight();
                        }
                    }

                    NumberAnimation {
                        id: pageTargetHighlightFade
                        target: replicaView
                        property: "pageTargetHighlightOpacity"
                        duration: 1000
                        easing.type: Easing.OutCubic
                    }

                    NumberAnimation {
                        id: longReplicaScrollAnimation
                        target: replicaView
                        property: "contentY"
                        duration: Math.max(80, Math.min(window.scrollDurationMs, 500))
                        easing.type: Easing.OutCubic
                    }

                    function capturePageDebug(event, sourceY, targetY, itemTop, itemBottom) {
                        pageDebugEvent = event;
                        pageDebugSourceY = sourceY;
                        pageDebugTargetY = targetY;
                        pageDebugItemTop = itemTop;
                        pageDebugItemBottom = itemBottom;
                    }

                    function replicaFocusTargetY(index) {
                        positionViewAtIndex(index, ListView.Beginning);
                        forceLayout();
                        return Math.max(
                            0,
                            Math.min(
                                contentHeight - height,
                                contentY - preferredHighlightBegin
                            )
                        );
                    }

                    function clampedContentY(value) {
                        return Math.max(0, Math.min(contentHeight - height, value));
                    }

                    // A replica can be taller than the reading viewport.  In
                    // that case an index is not a sufficient scroll target:
                    // the target must also depend on the current time inside
                    // the replica.  The same bounds are used by both modes.
                    function replicaReadingBounds(index) {
                        positionViewAtIndex(index, ListView.Beginning);
                        forceLayout();
                        var item = itemAtIndex(index);
                        if (!item) {
                            longReplicaIndex = -1;
                            return null;
                        }
                        longReplicaIndex = item.height > height ? index : -1;
                        var topY = clampedContentY(item.y - preferredHighlightBegin);
                        var bottomY = clampedContentY(item.y + item.height - height);
                        return {
                            item: item,
                            topY: topY,
                            bottomY: Math.max(topY, bottomY),
                            tall: item.height > height
                        };
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

                    function longReplicaTargetY(index, pageMode) {
                        var bounds = replicaReadingBounds(index);
                        if (!bounds || !bounds.tall) {
                            return bounds ? bounds.topY : contentY;
                        }
                        var distance = bounds.bottomY - bounds.topY;
                        var progress = replicaTimeProgress(index);
                        if (!pageMode || distance <= 0) {
                            return bounds.topY + distance * progress;
                        }
                        // The time interval selects a stable page, preventing
                        // small OSC updates from repeatedly nudging the text.
                        var step = pageFragmentStep();
                        var pages = Math.max(1, Math.ceil(distance / step));
                        var page = Math.min(pages, Math.floor(progress * (pages + 1)));
                        return Math.min(bounds.bottomY, bounds.topY + page * step);
                    }

                    function followCurrentLongReplica() {
                        if (pageScrollMode || !window.followEnabled
                                || manualDragScroll || currentIndex < 0) {
                            return;
                        }
                        forceLayout();
                        var sourceY = contentY;
                        var bounds = replicaReadingBounds(currentIndex);
                        var targetY = longReplicaTargetY(currentIndex, false);
                        contentY = sourceY;
                        if (!bounds || !bounds.tall || Math.abs(targetY - sourceY) <= 0.5) {
                            return;
                        }
                        longReplicaScrollAnimation.stop();
                        longReplicaScrollAnimation.from = sourceY;
                        longReplicaScrollAnimation.to = targetY;
                        longReplicaScrollAnimation.start();
                    }

                    function currentReplicaFocusTargetY() {
                        return replicaFocusTargetY(currentIndex);
                    }

                    function showPageTargetHighlight(index) {
                        pageTargetHighlightFade.stop();
                        if (!Boolean(window.config.page_target_highlight_enabled)) {
                            pageTargetHighlightIndex = -1;
                            pageTargetHighlightOpacity = 0;
                            return;
                        }
                        pageTargetHighlightIndex = index;
                        pageTargetHighlightOpacity = 0.22;
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

                    function startPageScroll(sourceY, targetY, targetIndex) {
                        showPageTargetHighlight(targetIndex);
                        pageScrollAnimation.from = sourceY;
                        pageScrollAnimation.to = targetY;
                        pageScrollAnimation.start();
                    }

                    function followCurrentReplicaByPage() {
                        if (!pageScrollMode) {
                            capturePageDebug("Пропуск: постраничный режим выключен", contentY, contentY, -1, -1);
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
                        if (pageGapPrefetchIndex === currentIndex
                                && pageScrollAnimation.running) {
                            capturePageDebug("Пропуск: следующая реплика уже подтягивается", contentY, contentY, -1, -1);
                            return;
                        }
                        forceLayout();
                        var sourceY = contentY;
                        pageScrollAnimation.stop();
                        var targetY = longReplicaTargetY(currentIndex, true);
                        var targetItem = itemAtIndex(currentIndex);
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        var viewportBottom = sourceY + height;
                        contentY = sourceY;
                        if (itemTop < sourceY || itemBottom > viewportBottom) {
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
                        pageScrollAnimation.stop();
                        var targetY = replicaFocusTargetY(nextIndex);
                        var targetItem = itemAtIndex(nextIndex);
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        var viewportBottom = sourceY + height;
                        contentY = sourceY;
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
                        forceLayout();
                        pageGapPrefetchIndex = -1;
                        var sourceY = contentY;
                        pageScrollAnimation.stop();
                        var targetY = longReplicaTargetY(currentIndex, true);
                        var targetItem = itemAtIndex(currentIndex);
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        contentY = sourceY;
                        capturePageDebug("Клик: выравнивание реплики к фокусу", sourceY, targetY, itemTop, itemBottom);
                        if (Math.abs(targetY - sourceY) > 0.5) {
                            pageFocusAlignmentActive = true;
                            startPageScroll(sourceY, targetY, currentIndex);
                        }
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
                            // Delegate heights change after a resize, a font
                            // update, or a mode switch.  Never continue an
                            // animation calculated for the old viewport.
                            pageScrollAnimation.stop();
                            longReplicaScrollAnimation.stop();
                            pageFocusAlignmentActive = false;
                            pageGapPrefetchIndex = -1;
                            longReplicaIndex = -1;
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
                        pageScrollAnimation.stop();
                        longReplicaScrollAnimation.stop();
                        pageTargetHighlightFade.stop();
                        pageFocusAlignmentActive = false;
                        pageGapPrefetchIndex = -1;
                        pageTargetHighlightIndex = -1;
                        pageTargetHighlightOpacity = 0;
                        manualDragScroll = false;
                        cancelPageHold();
                    }

                    function beginManualDragScroll() {
                        pageScrollAnimation.stop();
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
                        manualDragScroll = false;
                        if (pageScrollMode) {
                            Qt.callLater(pausePageFollowAtVisibleBoundary);
                        }
                    }

                    onCurrentIndexChanged: {
                        var wasPrefetched = pageGapPrefetchIndex === currentIndex;
                        pageGapPrefetchIndex = -1;
                        longReplicaIndex = -1;
                        if (!wasPrefetched || !pageScrollAnimation.running) {
                            queuePageFollow();
                        }
                    }
                    onHeightChanged: queueViewportFollow()
                    onWidthChanged: queueViewportFollow()
                    onContentHeightChanged: queueViewportFollow()
                    onPageScrollModeChanged: {
                        pageGapPrefetchIndex = -1;
                        longReplicaIndex = -1;
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
                            pageScrollAnimation.stop();
                            replicaView.pageGapPrefetchIndex = -1;
                            replicaView.contentY = Math.max(0, Math.min(replicaView.contentHeight - replicaView.height, replicaView.contentY - event.angleDelta.y));
                            if (replicaView.pageScrollMode) {
                                Qt.callLater(replicaView.pausePageFollowAtVisibleBoundary);
                            } else {
                                window.followEnabled = false;
                            }
                            event.accepted = true;
                        }
                    }

                    delegate: Item {
                        id: replicaDelegate
                        required property int index
                        required property real start
                        required property string time
                        required property string character
                        required property string actor
                        required property string replicaText
                        required property string actorColor
                        required property bool active
                        required property bool colorActive
                        required property var sourceIds

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

                        Rectangle {
                            anchors.fill: parent
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
                                        text: qsTr("Фрагмент %1").arg(index + 1)
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
                                window.jumpToReplica(replicaDelegate.start);
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
                                visible: window.config.layout_type === "Сценарий 1"
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
                                        text: qsTr("[") + window.displayedTimecode(replicaDelegate.time) + "]"
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
                                visible: window.config.layout_type === "Сценарий 2"
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
                                        text: window.displayedTimecode(replicaDelegate.time)
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
                                visible: window.config.layout_type === "Сценарий 3"
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
                                        text: window.displayedTimecode(replicaDelegate.time)
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
                    width: Math.min(parent.width - 24, 430)
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
