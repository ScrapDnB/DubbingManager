import QtQuick
import QtQuick.Controls

ListView {
    id: listView

    property bool verticalScrollBarEnabled: true
    readonly property bool hasVerticalOverflow: contentHeight > height + 1
    readonly property real scrollBarExtent: verticalScrollBar.width
        || verticalScrollBar.implicitWidth || 8
    readonly property real scrollBarGutter: hasVerticalOverflow && verticalScrollBarEnabled
        ? scrollBarExtent + 4 : 0
    readonly property real viewportWidth: Math.max(0, width - scrollBarGutter)

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        contentOverflow: listView.verticalScrollBarEnabled
            && listView.hasVerticalOverflow
    }
}
