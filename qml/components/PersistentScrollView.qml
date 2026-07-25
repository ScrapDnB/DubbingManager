import QtQuick
import QtQuick.Controls

ScrollView {
    id: scrollView

    readonly property bool hasVerticalOverflow: contentHeight > availableHeight + 1

    rightPadding: hasVerticalOverflow
        ? verticalScrollBar.width + 4 : 0

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        contentOverflow: scrollView.hasVerticalOverflow
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
