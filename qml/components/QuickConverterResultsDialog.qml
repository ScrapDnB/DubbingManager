pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softHeader
    required property color softAltRow
    required property color softMuted
    readonly property var backend: appBridge ? appBridge.converter : null

    modal: true
    title: qsTr("Результаты конвертации")
    width: boundedWidth(780, 40)
    height: boundedHeight(500, 50)

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Label {
            Layout.fillWidth: true
            text: dialog.backend ? dialog.backend.summary : ""
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: dialog.softHeader

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 10
                Label { Layout.preferredWidth: 210; text: qsTr("Файл"); font.bold: true }
                Label { Layout.preferredWidth: 90; text: qsTr("Статус"); font.bold: true }
                Label { Layout.fillWidth: true; text: qsTr("Результат"); font.bold: true }
            }
        }

        PersistentListView {
            id: resultsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.backend ? dialog.backend.model : null

            delegate: Rectangle {
                id: resultRow
                required property int index
                required property string fileName
                required property string status
                required property string detail
                required property string outputPath
                required property string statusKind

                width: resultsView.viewportWidth
                height: 48
                color: index % 2 === 0 ? "transparent" : dialog.softAltRow

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 10

                    Label {
                        Layout.preferredWidth: 210
                        text: resultRow.fileName
                        elide: Text.ElideMiddle
                    }
                    Label {
                        Layout.preferredWidth: 90
                        text: resultRow.status
                        color: resultRow.statusKind === "error"
                            ? palette.brightText : dialog.softMuted
                    }
                    Label {
                        Layout.fillWidth: true
                        text: resultRow.detail
                        elide: Text.ElideMiddle
                    }
                    ToolButton {
                        visible: resultRow.outputPath.length > 0
                        text: qsTr("↗")
                        Accessible.name: qsTr("Открыть результат")
                        onClicked: dialog.backend.openResult(resultRow.index)
                        ToolTip.visible: hovered
                        ToolTip.text: Accessible.name
                    }
                }
            }
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: qsTr("Очистить")
            onClicked: {
                dialog.backend.clear()
                dialog.close()
            }
        }
        AdaptiveButton { text: qsTr("Закрыть"); onClicked: dialog.close() }
    }
}
