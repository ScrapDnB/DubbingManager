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
    required property color softMuted
    readonly property var teleprompter: appBridge.teleprompter

    modal: false
    title: qsTr("Телесуфлёр - серия ") + teleprompter.episode
    width: boundedWidth(1240, 40)
    height: boundedHeight(820, 50)
    minimumWidth: 760
    minimumHeight: 520
    standardButtons: Dialog.NoButton

    property bool sidePanelVisible: true
    property bool followEnabled: true
    property var editingSourceIds: []
    property int colorTarget: -1
    readonly property string fixedFontFamily: Qt.platform.os === "osx"
        ? "Menlo"
        : Qt.platform.os === "windows"
            ? "Consolas"
            : "DejaVu Sans Mono"
    readonly property var config: teleprompter.config
    readonly property var colors: config.colors

    SystemPalette {
        id: systemPalette
        colorGroup: SystemPalette.Active
    }

    function openFor(episode) {
        if (!teleprompter.prepare(episode)) {
            return
        }
        open()
        requestActivate()
    }

    function navigate(direction) {
        followEnabled = true
        teleprompter.navigate(direction)
    }

    onClosed: {
        floatWindow.close()
        teleprompter.close()
    }

    Connections {
        target: window.teleprompter
        function onChanged() {
            episodeBox.currentIndex = episodeBox.indexOfValue(
                window.teleprompter.episode
            )
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
    }

    Connections {
        target: floatWindow
        function onVisibleChanged() {
            floatButton.checked = floatWindow.visible
        }
    }

    ColorDialog {
        id: colorDialog
        title: qsTr("Цвет телесуфлёра")
        onAccepted: {
            var keys = ["bg", "active_text", "inactive_text", "tc", "actor", "header_bg", "header_text"]
            if (window.colorTarget >= 0 && window.colorTarget < keys.length) {
                window.teleprompter.setConfigValue(
                    "colors." + keys[window.colorTarget], selectedColor.toString()
                )
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
        standardButtons: Dialog.Close

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: qsTr("Выбрать всех")
                    onClicked: window.teleprompter.selectAllActors(true)
                }
                Button {
                    text: qsTr("Снять выбор")
                    onClicked: window.teleprompter.selectAllActors(false)
                }
                Item { Layout.fillWidth: true }
            }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: window.teleprompter.actorModel

                delegate: CheckDelegate {
                    required property string actorId
                    required property string name
                    required property string color
                    required property bool selected
                    required property int roleCount

                    width: ListView.view.width
                    text: name + "  (" + roleCount + ")"
                    checked: selected
                    onToggled: window.teleprompter.setActorSelected(actorId, checked)

                    Rectangle {
                        width: 5
                        height: parent.height - 8
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        color: parent.color
                    }
                }
                ScrollBar.vertical: ScrollBar {}
            }
        }
    }

    NativeDialogWindow {
        id: editWindow
        ownerWindow: window
        modal: true
        title: qsTr("Редактировать реплику")
        width: boundedWidth(680, 40)
        height: boundedHeight(500, 50)
        standardButtons: Dialog.Save | Dialog.Cancel

        onAccepted: {
            if (window.teleprompter.editReplica(
                    window.editingSourceIds,
                    characterEdit.editText,
                    textEdit.text)) {
                close()
            }
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            Label { text: qsTr("Персонаж") }
            PlatformComboBox {
                id: characterEdit
                Layout.fillWidth: true
                editable: true
                model: window.teleprompter.characterNames
            }
            Label { text: qsTr("Текст") }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                TextArea {
                    id: textEdit
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                }
            }

            GroupBox {
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
                    TextField {
                        id: splitText
                        Layout.fillWidth: true
                        placeholderText: qsTr("Выделенная часть текста")
                    }
                    Button {
                        text: qsTr("Разделить реплику")
                        enabled: splitCharacter.editText.length > 0 && splitText.text.length > 0
                        onClicked: {
                            var remaining = textEdit.text.replace(splitText.text, "").trim()
                            if (window.teleprompter.splitReplica(
                                    window.editingSourceIds,
                                    remaining,
                                    splitText.text,
                                    splitCharacter.editText)) {
                                editWindow.close()
                            }
                        }
                    }
                }
            }
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                spacing: 6

                ToolButton {
                    text: window.sidePanelVisible
                        ? "Скрыть настройки"
                        : "Показать настройки"
                    onClicked: window.sidePanelVisible = !window.sidePanelVisible
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Панель настроек и список реплик")
                }
                Label { text: qsTr("Серия:") }
                PlatformComboBox {
                    id: episodeBox
                    Layout.preferredWidth: 150
                    textRole: "name"
                    valueRole: "name"
                    model: window.teleprompter.episodesModel
                    Component.onCompleted: currentIndex = indexOfValue(window.teleprompter.episode)
                    onActivated: window.teleprompter.setEpisode(currentValue)
                }
                ToolButton {
                    text: qsTr("Обновить каст")
                    onClicked: window.teleprompter.refreshCast()
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Перечитать назначения актёров")
                }
                Item { Layout.fillWidth: true }
                ToolButton {
                    text: qsTr("Предыдущая реплика")
                    onClicked: window.navigate(-1)
                }
                ToolButton {
                    text: qsTr("Следующая реплика")
                    onClicked: window.navigate(1)
                }
                ToolButton {
                    id: floatButton
                    text: qsTr("Плавающее окно")
                    enabled: Qt.platform.os !== "osx"
                    checkable: true
                    checked: floatWindow.visible
                    onToggled: checked
                        ? floatWindow.openNearOwner()
                        : floatWindow.close()
                    ToolTip.visible: hovered
                    ToolTip.text: qsTr("Плавающий контроллер")
                }
                ToolButton { text: qsTr("Закрыть окно"); onClicked: window.close() }
            }
        }

        Rectangle {
            visible: window.config.show_header
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 86 : 0
            color: window.colors.header_bg

            Label {
                anchors.centerIn: parent
                text: window.teleprompter.timecode
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
                Layout.preferredWidth: visible ? 350 : 0
                Layout.fillHeight: true
                color: systemPalette.window
                border.color: window.softBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(
                            settingsColumn.implicitHeight,
                            Math.max(210, parent.height * 0.52)
                        )
                        clip: true
                        contentWidth: availableWidth

                        ColumnLayout {
                            id: settingsColumn
                            width: parent.width
                            spacing: 5

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: qsTr("Просмотр")
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                Label {
                                    visible: window.config.osc_enabled
                                    text: window.teleprompter.oscStatus.startsWith("OSC:")
                                        ? "REAPER подключён"
                                        : window.teleprompter.oscStatus
                                    color: window.softMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    Layout.maximumWidth: 150
                                    ToolTip.visible: oscStatusHover.hovered
                                    ToolTip.text: window.teleprompter.oscStatus
                                    HoverHandler { id: oscStatusHover }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                CheckBox {
                                    text: qsTr("Зеркально")
                                    checked: window.config.is_mirrored
                                    onToggled: window.teleprompter.setConfigValue(
                                        "is_mirrored", checked
                                    )
                                }
                                CheckBox {
                                    text: qsTr("Таймкод")
                                    checked: window.config.show_header
                                    onToggled: window.teleprompter.setConfigValue(
                                        "show_header", checked
                                    )
                                }
                                Item { Layout.fillWidth: true }
                            }

                            Label {
                                text: qsTr("Положение фокуса · ")
                                    + Math.round(focusSlider.value * 100) + "%"
                            }
                            Slider {
                                id: focusSlider
                                Layout.fillWidth: true
                                from: 0.1
                                to: 0.9
                                value: window.config.focus_ratio
                                onPressedChanged: if (!pressed)
                                    window.teleprompter.setConfigValue(
                                        "focus_ratio", value
                                    )
                            }

                            CollapsibleSection {
                                title: qsTr("Размер текста")
                                Layout.fillWidth: true

                                Repeater {
                                    model: [
                                        { label: "Таймкод", key: "f_tc", value: window.config.f_tc },
                                        { label: "Персонаж", key: "f_char", value: window.config.f_char },
                                        { label: "Актёр", key: "f_actor", value: window.config.f_actor },
                                        { label: "Реплика", key: "f_text", value: window.config.f_text }
                                    ]
                                    delegate: RowLayout {
                                        id: fontRow
                                        required property var modelData
                                        Layout.fillWidth: true
                                        Label {
                                            text: fontRow.modelData.label
                                            Layout.fillWidth: true
                                        }
                                        SpinBox {
                                            from: 10
                                            to: fontRow.modelData.key === "f_text"
                                                ? 300 : 150
                                            value: fontRow.modelData.value
                                            editable: true
                                            onValueModified: window.teleprompter.setConfigValue(
                                                fontRow.modelData.key, value
                                            )
                                        }
                                    }
                                }
                            }

                            CollapsibleSection {
                                title: qsTr("Цвета и пресеты")
                                Layout.fillWidth: true

                                Repeater {
                                    model: ["Фон", "Активный текст", "Неактивный текст", "Таймкод", "Актёр", "Фон заголовка", "Текст заголовка"]
                                    delegate: RowLayout {
                                        id: colorRow
                                        required property int index
                                        required property string modelData
                                        Layout.fillWidth: true
                                        Rectangle {
                                            Layout.preferredWidth: 18
                                            Layout.preferredHeight: 18
                                            radius: 2
                                            color: [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_bg, window.colors.header_text][colorRow.index]
                                            border.color: window.softBorder
                                        }
                                        Button {
                                            text: colorRow.modelData
                                            Layout.fillWidth: true
                                            onClicked: {
                                                var values = [window.colors.bg, window.colors.active_text, window.colors.inactive_text, window.colors.tc, window.colors.actor, window.colors.header_bg, window.colors.header_text]
                                                window.colorTarget = colorRow.index
                                                colorDialog.selectedColor = values[colorRow.index]
                                                colorDialog.open()
                                            }
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: qsTr("Пресеты") }
                                    Repeater {
                                        model: window.teleprompter.presetModel
                                        delegate: Button {
                                            id: presetButton
                                            required property int presetIndex
                                            required property bool filled
                                            required property string presetBackground
                                            required property string presetForeground
                                            Layout.fillWidth: true
                                            text: String(presetIndex + 1)
                                            ToolTip.visible: hovered
                                            ToolTip.text: filled
                                                ? "Применить пресет"
                                                : "Сохранить текущие цвета"
                                            onClicked: window.teleprompter.applyOrSavePreset(
                                                presetIndex
                                            )
                                            onPressAndHold: if (filled)
                                                window.teleprompter.clearPreset(presetIndex)
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

                            CollapsibleSection {
                                title: qsTr("Прокрутка")
                                expanded: true
                                Layout.fillWidth: true

                                Label {
                                    text: qsTr("Синхронизация REAPER")
                                    color: window.softMuted
                                }
                                CheckBox {
                                    text: qsTr("Телесуфлёр следует за REAPER")
                                    checked: window.config.sync_in
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled(
                                        "sync_in", checked
                                    )
                                }
                                CheckBox {
                                    text: qsTr("REAPER следует за навигацией")
                                    checked: window.config.sync_out
                                    onToggled: window.appBridge.settings.setPrompterSyncEnabled(
                                        "sync_out", checked
                                    )
                                }

                                Label {
                                    text: qsTr("Плавность · ")
                                        + Math.round(smoothSlider.value)
                                }
                                Slider {
                                    id: smoothSlider
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 100
                                    stepSize: 1
                                    value: window.config.scroll_smoothness_slider
                                    onPressedChanged: if (!pressed)
                                        window.teleprompter.setConfigValue(
                                            "scroll_smoothness_slider", value
                                        )
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: qsTr("Реплики")
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Button {
                            text: qsTr("Актёры...")
                            onClicked: actorFilterWindow.open()
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Выбрать актёров для телесуфлёра")
                        }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: window.teleprompter.model
                        currentIndex: window.teleprompter.currentIndex
                        delegate: ItemDelegate {
                            required property int index
                            required property real start
                            required property string time
                            required property string character
                            required property bool active
                            width: ListView.view.width
                            height: active ? implicitHeight : 0
                            visible: active
                            text: time + " - " + character
                            highlighted: index === ListView.view.currentIndex
                            onClicked: {
                                window.followEnabled = true
                                window.teleprompter.jumpTo(start)
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: window.colors.bg
                clip: true

                ListView {
                    id: replicaView
                    anchors.fill: parent
                    anchors.leftMargin: Math.max(20, parent.width * 0.025)
                    anchors.rightMargin: anchors.leftMargin
                    clip: true
                    spacing: Math.max(14, window.config.f_text * 0.45)
                    model: window.teleprompter.model
                    currentIndex: window.followEnabled
                        ? window.teleprompter.currentIndex
                        : -1
                    preferredHighlightBegin: height * focusSlider.value
                    preferredHighlightEnd: preferredHighlightBegin
                    highlightRangeMode: ListView.StrictlyEnforceRange
                    highlightMoveDuration: Math.round(
                        smoothSlider.value * 12
                    )
                    transform: Scale {
                        origin.x: replicaView.width / 2
                        xScale: window.config.is_mirrored ? -1 : 1
                    }

                    WheelHandler {
                        target: null
                        onWheel: function(event) {
                            window.followEnabled = false
                            replicaView.contentY = Math.max(
                                0,
                                Math.min(
                                    replicaView.contentHeight - replicaView.height,
                                    replicaView.contentY - event.angleDelta.y
                                )
                            )
                            event.accepted = true
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

                        readonly property real horizontalMargin: Math.max(
                            8, ListView.view.width * 0.015
                        )

                        x: horizontalMargin
                        width: ListView.view.width - horizontalMargin * 2
                        height: replicaColumn.implicitHeight + 18
                        opacity: active ? 1 : 0.72

                        ColumnLayout {
                            id: replicaColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Text {
                                    text: replicaDelegate.character
                                    color: replicaDelegate.colorActive
                                        ? replicaDelegate.actorColor
                                        : (replicaDelegate.active
                                            ? window.colors.active_text
                                            : window.colors.inactive_text)
                                    font.pixelSize: window.config.f_char
                                    font.bold: true
                                }
                                Text {
                                    text: qsTr("[") + replicaDelegate.time + "]"
                                    color: replicaDelegate.active ? window.colors.tc : window.colors.inactive_text
                                    font.family: window.fixedFontFamily
                                    font.pixelSize: window.config.f_tc
                                }
                                Text {
                                    text: qsTr("(") + replicaDelegate.actor + ")"
                                    color: replicaDelegate.active ? window.colors.actor : window.colors.inactive_text
                                    font.pixelSize: window.config.f_actor
                                    font.italic: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                            }
                            Text {
                                text: replicaDelegate.replicaText
                                color: replicaDelegate.active ? window.colors.active_text : window.colors.inactive_text
                                font.pixelSize: window.config.f_text
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignLeft
                                Layout.fillWidth: true
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                window.followEnabled = true
                                window.teleprompter.jumpTo(replicaDelegate.start)
                            }
                            onDoubleClicked: {
                                window.editingSourceIds = replicaDelegate.sourceIds
                                characterEdit.editText = replicaDelegate.character
                                textEdit.text = replicaDelegate.replicaText
                                splitCharacter.editText = ""
                                splitText.text = ""
                                editWindow.open()
                            }
                        }
                    }
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOff }
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
