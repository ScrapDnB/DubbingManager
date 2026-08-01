import QtQuick
import QtQuick.Controls

ScrollView {
    id: scrollView

    property bool persistentVerticalScrollBar: true

    readonly property bool hasVerticalOverflow: contentHeight > availableHeight + 1
    readonly property real scrollBarExtent: verticalScrollBar.width
        || verticalScrollBar.implicitWidth || 8

    rightPadding: hasVerticalOverflow
        ? scrollBarExtent + 4 : 0

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        contentOverflow: scrollView.hasVerticalOverflow
        persistent: scrollView.persistentVerticalScrollBar
        parent: scrollView
        anchors.top: scrollView.top
        anchors.right: scrollView.right
        anchors.bottom: scrollView.bottom
        width: Math.max(10, implicitWidth)
    }

    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }
}
