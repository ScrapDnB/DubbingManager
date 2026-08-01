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
    property var editingSourceIds: []
    property int colorTarget: -1
    readonly property var config: teleprompter.config
    readonly property var colors: config.colors
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
        if (!teleprompter.prepare(episode)) {
            return;
        }
        open();
        requestActivate();
    }

    function navigate(direction) {
        followEnabled = true;
        replicaView.cancelPageHold();
        teleprompter.navigate(direction);
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
            episodeBox.currentIndex = episodeBox.indexOfValue(window.teleprompter.episode);
        }
        function onPositionChanged() {
            replicaView.resumePageFollowWhenBoundaryEnds();
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
                onActivated: window.teleprompter.setEpisode(currentValue)
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
            AdaptiveButton {
                text: qsTr("Предыдущая реплика")
                Layout.preferredHeight: window.toolbarControlHeight
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.navigate(-1)
            }
            AdaptiveButton {
                text: qsTr("Следующая реплика")
                Layout.preferredHeight: window.toolbarControlHeight
                Layout.alignment: Qt.AlignVCenter
                onClicked: window.navigate(1)
            }
            AdaptiveButton {
                id: floatButton
                visible: true
                text: qsTr("Плавающее окно")
                Layout.preferredHeight: window.toolbarControlHeight
                Layout.alignment: Qt.AlignVCenter
                enabled: true
                checkable: true
                checked: floatWindow.visible
                onToggled: checked ? floatWindow.openNearOwner() : floatWindow.close()
                PlatformToolTip {
                    target: floatButton
                    text: qsTr("Плавающий контроллер")
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
                                    text: qsTr("REAPER следует за навигацией")
                                    checked: window.config.sync_out
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled("sync_out", checked)
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
                                    text: qsTr("Плавность · ") + Math.round(smoothSlider.value)
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
                                        window.followEnabled = true;
                                        replicaView.cancelPageHold();
                                        window.teleprompter.jumpTo(navigationRow.start);
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
                    currentIndex: window.followEnabled ? window.teleprompter.currentIndex : -1
                    readonly property bool pageScrollMode: Boolean(window.config.page_scroll_mode)
                    property real pageScrollHoldUntil: -1
                    preferredHighlightBegin: height * focusSlider.value
                    preferredHighlightEnd: preferredHighlightBegin
                    highlightRangeMode: pageScrollMode ? ListView.NoHighlightRange : ListView.StrictlyEnforceRange
                    highlightMoveDuration: Math.round(smoothSlider.value * 12)

                    NumberAnimation {
                        id: pageScrollAnimation
                        target: replicaView
                        property: "contentY"
                        duration: Math.max(120, Math.round(120 + smoothSlider.value * 10))
                        easing.type: Easing.OutCubic
                    }

                    function followCurrentReplicaByPage() {
                        if (!pageScrollMode || !window.followEnabled || currentIndex < 0 || pageScrollHoldUntil >= 0) {
                            return;
                        }
                        // positionViewAtIndex resolves the real delegate
                        // geometry, including wrapped text after a resize.
                        var sourceY = contentY;
                        pageScrollAnimation.stop();
                        positionViewAtIndex(currentIndex, ListView.Beginning);
                        var targetY = contentY;
                        var targetItem = currentItem;
                        var itemTop = targetItem ? targetItem.y : targetY;
                        var itemBottom = targetItem ? itemTop + targetItem.height : itemTop;
                        contentY = sourceY;
                        if (itemTop < sourceY || itemBottom > sourceY + height) {
                            pageScrollAnimation.from = sourceY;
                            pageScrollAnimation.to = targetY;
                            pageScrollAnimation.start();
                        }
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
                            pageScrollHoldUntil = -1;
                            return;
                        }
                        var item = itemAtIndex(index);
                        if (item && item.y + item.height > viewportBottom) {
                            index -= 1;
                            item = itemAtIndex(index);
                        }
                        if (!item || item.y < contentY || item.y + item.height > viewportBottom) {
                            pageScrollHoldUntil = -1;
                            return;
                        }
                        pageScrollHoldUntil = Number(window.teleprompter.model.get(index).end);
                    }

                    function resumePageFollowWhenBoundaryEnds() {
                        if (!pageScrollMode || pageScrollHoldUntil < 0 || window.teleprompter.time < pageScrollHoldUntil) {
                            return;
                        }
                        pageScrollHoldUntil = -1;
                        Qt.callLater(followCurrentReplicaByPage);
                    }

                    function cancelPageHold() {
                        pageScrollHoldUntil = -1;
                    }

                    onCurrentIndexChanged: Qt.callLater(followCurrentReplicaByPage)
                    onHeightChanged: Qt.callLater(pageScrollHoldUntil >= 0 ? pausePageFollowAtVisibleBoundary : followCurrentReplicaByPage)
                    onWidthChanged: Qt.callLater(pageScrollHoldUntil >= 0 ? pausePageFollowAtVisibleBoundary : followCurrentReplicaByPage)
                    onContentHeightChanged: if (pageScrollHoldUntil >= 0)
                        Qt.callLater(pausePageFollowAtVisibleBoundary)
                    onPageScrollModeChanged: {
                        if (!pageScrollMode) {
                            pageScrollAnimation.stop();
                        }
                        cancelPageHold();
                        Qt.callLater(followCurrentReplicaByPage);
                    }
                    transform: Scale {
                        origin.x: replicaView.width / 2
                        xScale: window.config.is_mirrored ? -1 : 1
                    }

                    WheelHandler {
                        target: null
                        onWheel: function (event) {
                            pageScrollAnimation.stop();
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

                        x: horizontalMargin
                        width: replicaView.viewportWidth - horizontalMargin * 2
                        height: layoutContent.implicitHeight + (window.config.show_block_borders ? 20 : 18)
                        opacity: active ? 1 : 0.72

                        Rectangle {
                            anchors.fill: parent
                            visible: window.config.show_block_borders
                            color: "transparent"
                            radius: window.macOSStyle ? 5 : 3
                            border.width: 1
                            border.color: replicaDelegate.blockBorderColor
                        }

                        // The background remains a navigation target; the
                        // character and dialogue themselves open the editor.
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                window.followEnabled = true;
                                replicaView.cancelPageHold();
                                window.teleprompter.jumpTo(replicaDelegate.start);
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
