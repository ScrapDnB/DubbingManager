pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

FocusScope {
    id: tabs

    property var model: []
    property int currentIndex: 0
    property real tabWidth: 120
    property color softMuted: tabPalette.placeholderText

    signal activated(int index)

    implicitWidth: Math.max(1, model.length) * tabWidth
    implicitHeight: 34
    activeFocusOnTab: true

    function select(index) {
        var bounded = Math.max(0, Math.min(model.length - 1, index))
        if (bounded === currentIndex) {
            return
        }
        currentIndex = bounded
        activated(bounded)
    }

    Accessible.role: Accessible.PageTabList

    Keys.onLeftPressed: select(currentIndex - 1)
    Keys.onRightPressed: select(currentIndex + 1)
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Home) {
            select(0)
            event.accepted = true
        } else if (event.key === Qt.Key_End) {
            select(model.length - 1)
            event.accepted = true
        }
    }

    SystemPalette {
        id: tabPalette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Qt.rgba(
            tabPalette.mid.r,
            tabPalette.mid.g,
            tabPalette.mid.b,
            0.45
        )
    }

    Row {
        anchors.fill: parent

        Repeater {
            model: tabs.model

            delegate: Item {
                id: tabItem

                required property int index
                required property string modelData
                readonly property bool selected: index === tabs.currentIndex

                width: tabs.tabWidth
                height: tabs.height

                Accessible.name: modelData
                Accessible.role: Accessible.PageTab
                Accessible.selected: selected

                Rectangle {
                    anchors.fill: parent
                    anchors.bottomMargin: 1
                    color: tabMouse.containsMouse && !tabItem.selected
                        ? Qt.rgba(
                            tabPalette.text.r,
                            tabPalette.text.g,
                            tabPalette.text.b,
                            0.055
                        )
                        : "transparent"
                }

                Label {
                    anchors.centerIn: parent
                    width: parent.width - 16
                    text: tabItem.modelData
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    color: tabItem.selected
                        ? tabPalette.text
                        : tabs.softMuted
                    font.weight: tabItem.selected
                        ? Font.DemiBold
                        : Font.Normal
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    height: 2
                    radius: 1
                    visible: tabItem.selected
                    color: tabPalette.highlight
                }

                MouseArea {
                    id: tabMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        tabs.forceActiveFocus()
                        tabs.select(tabItem.index)
                    }
                }
            }
        }
    }
}
