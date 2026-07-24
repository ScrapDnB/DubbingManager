import QtQuick
import QtQuick.Controls

ListView {
    readonly property real scrollBarGutter: verticalScrollBar.visible
        ? verticalScrollBar.implicitWidth + 4 : 0
    readonly property real viewportWidth: Math.max(0, width - scrollBarGutter)

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
    }
}
