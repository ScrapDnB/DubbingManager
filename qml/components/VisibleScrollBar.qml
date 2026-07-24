import QtQuick
import QtQuick.Controls

ScrollBar {
    policy: ScrollBar.AsNeeded
    minimumSize: 0.08
    active: Qt.platform.os === "osx"
        ? hovered || pressed
        : size < 1.0 || hovered || pressed
    interactive: true
}
