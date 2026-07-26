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
    property int actorMarkerShape: 0
    property int actorMarkerSize: 0
    property string actorSearchText: ""

    modal: true
    title: qsTr("Подсветка актёров")
    standardButtons: Dialog.Close
    width: boundedWidth(480, 36)
    height: boundedHeight(620, 36)

    function matchesActor(name) {
        var needle = actorSearchText.trim().toLocaleLowerCase()
        return needle.length === 0
            || String(name).toLocaleLowerCase().indexOf(needle) >= 0
    }

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

        TextField {
            id: actorSearchField
            Layout.fillWidth: true
            placeholderText: qsTr("Имя или фамилия")
            selectByMouse: true
            onTextChanged: dialog.actorSearchText = text
        }

        TableHeaderSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: dialog.tableHeaderHeight
            softHeader: dialog.softHeader
            softBorder: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8
                TableHeaderLabel { text: qsTr("Актёр"); Layout.fillWidth: true }
                TableHeaderLabel {
                    text: qsTr("Белый текст")
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
                visible: dialog.matchesActor(actorRow.name)
                height: visible ? dialog.compactRowHeight : 0
                color: actorRow.index % 2 === 0
                    ? dialog.softRow
                    : dialog.softAltRow

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    ActorColorSwatch {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        swatchColor: actorRow.actorColor
                        markerShape: dialog.actorMarkerShape
                        markerSize: dialog.actorMarkerSize
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
                visible: dialog.actorSearchText.length > 0
                    ? actorList.contentHeight <= 0
                    : actorList.count === 0
                text: dialog.actorSearchText.length > 0
                    ? qsTr("Актёры не найдены")
                    : qsTr("В проекте нет актёров")
                color: dialog.softMuted
            }
        }
    }
}
