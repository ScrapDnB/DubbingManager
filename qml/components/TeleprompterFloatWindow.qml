pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: floatWindow

    required property var teleprompter
    property var ownerWindow

    width: 330
    height: 310
    minimumWidth: 280
    minimumHeight: 220
    maximumWidth: 520
    maximumHeight: 520
    visible: false
    title: qsTr("Телесуфлёр")
    transientParent: ownerWindow
    flags: Qt.Tool | Qt.WindowStaysOnTopHint
    color: palette.window

    function openNearOwner() {
        if (ownerWindow) {
            x = ownerWindow.x + ownerWindow.width - width - 24
            y = ownerWindow.y + 72
        }
        visible = true
        raise()
        requestActivate()
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
        spacing: 6

        Label {
            text: floatWindow.teleprompter.timecode
            font.pixelSize: 22
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
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

        ListView {
            id: activeList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: floatWindow.teleprompter.model
            currentIndex: floatWindow.teleprompter.currentIndex

            delegate: ItemDelegate {
                required property int index
                required property real start
                required property string time
                required property string character
                required property bool active

                width: activeList.width
                height: active ? implicitHeight : 0
                visible: active
                text: time + "  " + character
                highlighted: index === activeList.currentIndex
                onClicked: floatWindow.teleprompter.jumpTo(start)
            }

            ScrollBar.vertical: ScrollBar {}
        }

        RowLayout {
            Layout.fillWidth: true

            Button {
                text: qsTr("Назад")
                Layout.fillWidth: true
                onClicked: floatWindow.teleprompter.navigate(-1)
            }
            Button {
                text: qsTr("Далее")
                Layout.fillWidth: true
                onClicked: floatWindow.teleprompter.navigate(1)
            }
            Button {
                text: qsTr("Скрыть")
                onClicked: floatWindow.close()
            }
        }
    }
}
