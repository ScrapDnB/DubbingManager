pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property var entries: []
    readonly property alias menuVisible: popup.visible
    signal itemTriggered(int index)

    implicitHeight: 32
    leftPadding: 12
    rightPadding: 12
    topPadding: 4
    bottomPadding: 4
    hoverEnabled: true

    contentItem: Label {
        text: control.text
        color: control.palette.text
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
    }

    background: Rectangle {
        radius: 3
        color: control.down || popup.visible ? Qt.rgba(
            control.palette.highlight.r, control.palette.highlight.g,
            control.palette.highlight.b, 0.16
        ) : control.hovered ? Qt.rgba(
            control.palette.highlight.r, control.palette.highlight.g,
            control.palette.highlight.b, 0.10
        ) : "transparent"
    }

    function openMenu() {
        popup.open()
    }

    function closeMenu() {
        popup.close()
    }

    onClicked: popup.visible ? closeMenu() : openMenu()

    Popup {
        id: popup
        x: 0
        y: control.height
        width: 240
        height: menuColumn.implicitHeight + topPadding + bottomPadding
        leftPadding: 4
        rightPadding: 4
        topPadding: 4
        bottomPadding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        contentItem: Column {
            id: menuColumn
            width: popup.availableWidth
            spacing: 1

            Repeater {
                model: control.entries

                delegate: Item {
                    required property var modelData
                    required property int index

                    width: menuColumn.width
                    height: modelData.separator === true ? 9 : 32

                    Rectangle {
                        visible: modelData.separator === true
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: 1
                        color: Qt.rgba(0.5, 0.5, 0.5, 0.28)
                    }

                    AbstractButton {
                        id: menuItem
                        visible: modelData.separator !== true
                        anchors.fill: parent
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 4
                        bottomPadding: 4
                        hoverEnabled: true
                        enabled: modelData.enabled === undefined || modelData.enabled

                        contentItem: Label {
                            text: modelData.text || ""
                            color: menuItem.enabled ? menuItem.palette.text : Qt.rgba(
                                menuItem.palette.text.r, menuItem.palette.text.g,
                                menuItem.palette.text.b, 0.42
                            )
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
                        }

                        background: Rectangle {
                            radius: 3
                            color: menuItem.down ? Qt.rgba(
                                menuItem.palette.highlight.r, menuItem.palette.highlight.g,
                                menuItem.palette.highlight.b, 0.16
                            ) : menuItem.hovered ? Qt.rgba(
                                menuItem.palette.highlight.r, menuItem.palette.highlight.g,
                                menuItem.palette.highlight.b, 0.10
                            ) : "transparent"
                        }

                        onClicked: {
                            popup.close()
                            control.itemTriggered(index)
                        }
                    }
                }
            }
        }

        background: Rectangle {
            radius: 6
            border.width: 1
            border.color: Qt.rgba(
                control.palette.text.r, control.palette.text.g,
                control.palette.text.b, 0.18
            )
            color: control.palette.base
        }
    }
}
