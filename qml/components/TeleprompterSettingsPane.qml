pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

PersistentScrollView {
    id: pane

    required property var configuration
    signal configEdited(var config)
    property string colorTarget: ""

    clip: true
    contentWidth: availableWidth

    function setValue(key, value) {
        var next = Object.assign({}, configuration)
        next[key] = value
        configEdited(next)
    }

    function setColor(key, value) {
        var next = Object.assign({}, configuration)
        var colors = Object.assign({}, next.colors || {})
        colors[key] = value
        next.colors = colors
        configEdited(next)
    }

    ColorDialog {
        id: colorDialog
        title: qsTr("Цвет телесуфлёра")
        onAccepted: pane.setColor(pane.colorTarget, selectedColor.toString())
    }

    ColumnLayout {
        width: pane.availableWidth
        spacing: 10

        GroupBox {
            title: qsTr("Отображение")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 3
                CheckBox { text: qsTr("Зеркально"); checked: Boolean(pane.configuration.is_mirrored); onToggled: pane.setValue("is_mirrored", checked) }
                CheckBox { text: qsTr("Показывать заголовок"); checked: Boolean(pane.configuration.show_header); onToggled: pane.setValue("show_header", checked) }
                CheckBox { text: qsTr("Системный пульт macOS"); checked: Boolean(pane.configuration.use_cocoa_float_window); onToggled: pane.setValue("use_cocoa_float_window", checked) }
                Label { text: qsTr("Позиция фокуса: ") + Math.round(Number(pane.configuration.focus_ratio || 0.5) * 100) + "%"; Layout.columnSpan: 2 }
                WinUiSlider { from: 0.1; to: 0.9; stepSize: 0.01; value: Number(pane.configuration.focus_ratio || 0.5); onMoved: pane.setValue("focus_ratio", value); Layout.fillWidth: true }
                Label { text: qsTr("Плавность: ") + Number(pane.configuration.scroll_smoothness_slider || 18); Layout.columnSpan: 2 }
                WinUiSlider { from: 0; to: 100; stepSize: 1; value: Number(pane.configuration.scroll_smoothness_slider || 18); onMoved: pane.setValue("scroll_smoothness_slider", Math.round(value)); Layout.fillWidth: true }
            }
        }

        GroupBox {
            title: qsTr("Размер текста")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Label { text: qsTr("Таймкод") }
                WinUiSpinBox { from: 10; to: 150; value: Number(pane.configuration.f_tc || 20); onValueModified: pane.setValue("f_tc", value) }
                Label { text: qsTr("Персонаж") }
                WinUiSpinBox { from: 10; to: 150; value: Number(pane.configuration.f_char || 24); onValueModified: pane.setValue("f_char", value) }
                Label { text: qsTr("Актёр") }
                WinUiSpinBox { from: 10; to: 150; value: Number(pane.configuration.f_actor || 18); onValueModified: pane.setValue("f_actor", value) }
                Label { text: qsTr("Реплика") }
                WinUiSpinBox { from: 10; to: 300; value: Number(pane.configuration.f_text || 36); onValueModified: pane.setValue("f_text", value) }
            }
        }

        GroupBox {
            title: qsTr("Цветовая схема")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Repeater {
                    model: [
                        { key: "bg", label: "Фон" },
                        { key: "active_text", label: "Активный текст" },
                        { key: "inactive_text", label: "Неактивный текст" },
                        { key: "tc", label: "Таймкод" },
                        { key: "actor", label: "Актёр" },
                        { key: "header_bg", label: "Фон заголовка" },
                        { key: "header_text", label: "Текст заголовка" }
                    ]
                    delegate: RowLayout {
                        id: colorRow
                        required property var modelData
                        Layout.columnSpan: 2
                        Label { text: colorRow.modelData.label; Layout.fillWidth: true }
                        Button {
                            text: qsTr("")
                            implicitWidth: 42
                            Rectangle {
                                anchors.centerIn: parent
                                width: 26
                                height: 14
                                color: (pane.configuration.colors || {})[
                                    colorRow.modelData.key
                                ] || "#000000"
                                border.color: palette.mid
                                radius: 2
                            }
                            onClicked: {
                                pane.colorTarget = colorRow.modelData.key
                                colorDialog.selectedColor = (pane.configuration.colors || {})[
                                    colorRow.modelData.key
                                ] || "#000000"
                                colorDialog.open()
                            }
                            ToolTip.visible: hovered
                            ToolTip.text: colorRow.modelData.label
                        }
                    }
                }
            }
        }

        GroupBox {
            title: qsTr("Навигация")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Label { text: qsTr("Предыдущая:") }
                TextField { text: String(pane.configuration.key_prev || "Left"); onEditingFinished: pane.setValue("key_prev", text); Layout.fillWidth: true }
                Label { text: qsTr("Следующая:") }
                TextField { text: String(pane.configuration.key_next || "Right"); onEditingFinished: pane.setValue("key_next", text); Layout.fillWidth: true }
            }
        }

    }
}
