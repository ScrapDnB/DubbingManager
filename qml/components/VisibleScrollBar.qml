import QtQuick
import QtQuick.Controls

ScrollBar {
    policy: ScrollBar.AsNeeded
    active: size < 1.0 || hovered || pressed
    interactive: true
}
