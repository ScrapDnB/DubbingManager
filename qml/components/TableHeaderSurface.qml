pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: header

    default property alias contentData: contentHost.data
    property color softHeader: palette.base
    property color softBorder: palette.mid
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    implicitHeight: macOSStyle ? 24 : 30

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.fill: parent
        color: header.macOSStyle ? "transparent" : header.softHeader
        border.color: header.macOSStyle
            ? "transparent" : header.softBorder
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        visible: header.macOSStyle
        color: header.softBorder
    }

    Item {
        id: contentHost
        anchors.fill: parent
    }
}
