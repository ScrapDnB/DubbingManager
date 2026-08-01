pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    // The attached Flickable assigns `size` only after construction.  Reading
    // it here made the macOS style receive an undefined value during startup.
    property bool contentOverflow: true
    property bool persistent: true
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    policy: !contentOverflow
        ? ScrollBar.AlwaysOff
        : persistent ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
    minimumSize: 0.08
    active: contentOverflow && (persistent || hovered || pressed)
    interactive: true
    opacity: !contentOverflow ? 0 : (persistent || hovered || pressed ? 1 : 0)
    implicitWidth: macOSStyle ? 8 : 10
    implicitHeight: macOSStyle ? 8 : 10

    Behavior on opacity {
        NumberAnimation { duration: 100 }
    }

    contentItem: Rectangle {
        // The native macOS style reads this property for its hover fade even
        // when an application supplies a custom handle.
        property int transitionDuration: 100
        implicitWidth: control.macOSStyle ? 6 : 8
        implicitHeight: control.macOSStyle ? 6 : 8
        radius: implicitWidth / 2
        color: control.palette.text
        opacity: !control.contentOverflow
            ? 0
            : control.hovered || control.pressed ? 0.58 : 0.34

        Behavior on opacity {
            NumberAnimation { duration: 100 }
        }
    }
}
