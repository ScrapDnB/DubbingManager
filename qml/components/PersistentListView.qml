import QtQuick
import QtQuick.Controls

ListView {
    id: listView

    readonly property real scrollBarGutter: verticalScrollBar.size < 1.0
        ? verticalScrollBar.width + 4 : 0
    readonly property real viewportWidth: Math.max(0, width - scrollBarGutter)

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        parent: listView
        x: listView.width - width
        y: 0
        width: Math.max(10, implicitWidth)
        height: listView.height
    }
}
