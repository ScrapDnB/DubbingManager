pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: pane
    required property var backend
    required property color softMuted
    readonly property var labels: ({character: qsTr("Персонаж"), time_start: qsTr("Начало реплики"),
        time_end: qsTr("Конец реплики"), time_split: qsTr("Диапазон времени"), text: qsTr("Текст реплики")})
    spacing: 10

    RowLayout {
        Layout.fillWidth: true
        Label { text: qsTr("1  Колонки"); font.bold: true; Layout.fillWidth: true }
        AdaptiveButton { text: qsTr("Автоопределение"); onClicked: pane.backend.autoDetect() }
    }
    Label {
        text: qsTr("Текст обязателен. Персонаж и тайминг — по необходимости.")
        Layout.fillWidth: true
        color: pane.softMuted
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: pane.backend.fields
        delegate: ColumnLayout {
            id: fieldRow
            required property var modelData
            Layout.fillWidth: true
            spacing: 4
            Label {
                text: pane.labels[fieldRow.modelData.key] + (fieldRow.modelData.key === "text" ? " *" : "")
                font.bold: fieldRow.modelData.key === "text"
            }
            RowLayout {
                Layout.fillWidth: true
                PlatformComboBox {
                    id: columnCombo
                    objectName: "importColumn_" + fieldRow.modelData.key
                    Layout.fillWidth: true
                    model: pane.backend.columnsModel
                    textRole: "label"
                    valueRole: "index"
                    displayText: currentIndex < 0 ? qsTr("Не использовать") : currentText
                    currentIndex: {
                        var value = pane.backend.mapping[fieldRow.modelData.key]
                        return value === null || value === undefined ? -1 : Number(value)
                    }
                    onActivated: pane.backend.setMapping(fieldRow.modelData.key, currentValue)
                }
                ToolButton {
                    text: "×"
                    enabled: columnCombo.currentIndex >= 0
                    Accessible.name: qsTr("Не использовать: ") + fieldRow.modelData.label
                    onClicked: pane.backend.setMapping(fieldRow.modelData.key, -1)
                }
            }
        }
    }
    Label {
        text: qsTr("Для времени выберите либо одну колонку с диапазоном, либо отдельные начало и конец.")
        Layout.fillWidth: true
        color: pane.softMuted
        wrapMode: Text.WordWrap
    }
}
