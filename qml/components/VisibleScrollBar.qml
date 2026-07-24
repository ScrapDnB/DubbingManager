import QtQuick
import QtQuick.Controls

ScrollBar {
    policy: ScrollBar.AsNeeded
    minimumSize: 0.08
    active: size < 1.0 || hovered || pressed
    interactive: true
}
