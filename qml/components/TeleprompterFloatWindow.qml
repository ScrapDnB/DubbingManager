pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: floatWindow

    required property var teleprompter
    required property color softBorder
    required property color softMuted
    property var ownerWindow

    width: 300
    height: 440
    minimumWidth: 280
    minimumHeight: 340
    maximumWidth: 520
    maximumHeight: 700
    visible: false
    title: qsTr("Телесуфлёр")
    transientParent: null
    flags: Qt.Tool
        | Qt.WindowStaysOnTopHint
        | Qt.CustomizeWindowHint
        | Qt.WindowDoesNotAcceptFocus
        | Qt.FramelessWindowHint
    color: palette.window

    function openNearOwner() {
        if (ownerWindow) {
            x = ownerWindow.x + ownerWindow.width - width - 24
            y = ownerWindow.y + 72
        }
        visible = true
        raise()
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    Connections {
        target: floatWindow.teleprompter
        function onChanged() {
            episodeBox.currentIndex = episodeBox.indexOfValue(
                floatWindow.teleprompter.episode
            )
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            radius: 4
            color: Qt.rgba(
                palette.text.r,
                palette.text.g,
                palette.text.b,
                0.12
            )

            Label {
                anchors.centerIn: parent
                text: qsTr("Управление")
                font.bold: true
            }

            HoverHandler {
                cursorShape: Qt.OpenHandCursor
            }
            DragHandler {
                target: null
                onActiveChanged: if (active) floatWindow.startSystemMove()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            FluentButton {
                text: qsTr("Назад")
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                onClicked: floatWindow.teleprompter.navigate(-1)
            }
            FluentButton {
                text: qsTr("Вперёд")
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                onClicked: floatWindow.teleprompter.navigate(1)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Серия:") }
            PlatformComboBox {
                id: episodeBox
                Layout.fillWidth: true
                textRole: "name"
                valueRole: "name"
                model: floatWindow.teleprompter.episodesModel
                Component.onCompleted: currentIndex = indexOfValue(
                    floatWindow.teleprompter.episode
                )
                onActivated: floatWindow.teleprompter.setEpisode(currentValue)
            }
        }

        Label {
            text: qsTr("Список реплик:")
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 4
            color: palette.base
            border.width: 1
            border.color: floatWindow.softBorder
            clip: true

            PersistentListView {
                id: activeList
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: floatWindow.teleprompter.model
                currentIndex: floatWindow.teleprompter.currentIndex

                delegate: Rectangle {
                    id: navigationRow

                    required property int index
                    required property real start
                    required property string time
                    required property string character
                    required property bool active

                    width: activeList.viewportWidth
                    height: active ? 30 : 0
                    visible: active
                    color: index === activeList.currentIndex
                        ? Qt.rgba(
                            palette.highlight.r,
                            palette.highlight.g,
                            palette.highlight.b,
                            0.14
                        ) : navigationHover.hovered ? Qt.rgba(
                            palette.highlight.r,
                            palette.highlight.g,
                            palette.highlight.b,
                            0.07
                        ) : index % 2 === 0 ? "transparent"
                            : Qt.rgba(
                                palette.text.r,
                                palette.text.g,
                                palette.text.b,
                                0.025
                            )

                    HoverHandler { id: navigationHover }
                    TapHandler {
                        onTapped: floatWindow.teleprompter.jumpTo(
                            navigationRow.start
                        )
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 6
                        spacing: 7

                        Label {
                            text: navigationRow.time
                            color: floatWindow.softMuted
                            Layout.preferredWidth: 56
                            horizontalAlignment: Text.AlignRight
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

        FluentButton {
            text: qsTr("Скрыть")
            Layout.fillWidth: true
            onClicked: floatWindow.close()
        }
    }
}
