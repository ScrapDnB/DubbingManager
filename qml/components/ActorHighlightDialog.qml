pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var montageBackend
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted

    modal: true
    title: qsTr("Подсветка актёров")
    standardButtons: Dialog.Close
    width: boundedWidth(480, 36)
    height: boundedHeight(620, 36)

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true

            AdaptiveButton {
                text: qsTr("Выбрать всех")
                Layout.preferredWidth: 110
                onClicked: dialog.montageBackend.setAllActorsHighlighted(true)
            }
            AdaptiveButton {
                text: qsTr("Снять все")
                Layout.preferredWidth: 100
                onClicked: dialog.montageBackend.setAllActorsHighlighted(false)
            }
            Item { Layout.fillWidth: true }
            Label {
                text: dialog.montageBackend.highlightSummary
                color: dialog.softMuted
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            color: dialog.softHeader
            border.color: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8
                Label { text: qsTr("Актёр"); font.bold: true; Layout.fillWidth: true }
                Label {
                    text: qsTr("Белый текст")
                    font.bold: true
                    Layout.preferredWidth: 105
                }
            }
        }

        PersistentListView {
            id: actorList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.montageBackend
                ? dialog.montageBackend.highlightModel
                : null
            delegate: Rectangle {
                id: actorRow

                required property int index
                required property string actorId
                required property string name
                required property color actorColor
                required property bool selected
                required property bool negative

                width: actorList.viewportWidth
                height: 34
                color: actorRow.index % 2 === 0
                    ? dialog.softRow
                    : dialog.softAltRow

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        radius: 2
                        color: actorRow.actorColor
                        border.color: dialog.softBorder
                    }

                    CheckBox {
                        text: actorRow.name
                        checked: actorRow.selected
                        Layout.fillWidth: true
                        onToggled: {
                            dialog.montageBackend.setActorHighlighted(
                                actorRow.actorId,
                                checked
                            )
                        }
                    }

                    CheckBox {
                        Accessible.name: qsTr("Белый текст для ") + actorRow.name
                        checked: actorRow.negative
                        Layout.preferredWidth: 105
                        onToggled: {
                            dialog.montageBackend.setActorNegative(
                                actorRow.actorId,
                                checked
                            )
                        }
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: actorList.count === 0
                text: qsTr("В проекте нет актёров")
                color: dialog.softMuted
            }
        }
    }
}
