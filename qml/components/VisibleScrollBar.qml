pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    property bool contentOverflow: size < 1.0
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    policy: contentOverflow ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
    minimumSize: 0.08
    active: contentOverflow || hovered || pressed
    interactive: true

    Component.onCompleted: {
        if (macOSStyle)
            control.contentItem = macOSHandle.createObject(control)
    }

    Component {
        id: macOSHandle

        Rectangle {
            implicitWidth: 6
            implicitHeight: 6
            radius: 3
            color: control.palette.text
            opacity: !control.contentOverflow
                ? 0
                : control.hovered || control.pressed ? 0.58 : 0.34

            Behavior on opacity {
                NumberAnimation { duration: 100 }
            }
        }
    }
}
