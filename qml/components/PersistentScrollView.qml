import QtQuick
import QtQuick.Controls

ScrollView {
    id: scrollView

    readonly property bool hasVerticalOverflow: contentHeight > availableHeight + 1
    readonly property real scrollBarExtent: verticalScrollBar.width
        || verticalScrollBar.implicitWidth || 8

    rightPadding: hasVerticalOverflow
        ? scrollBarExtent + 4 : 0

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        contentOverflow: scrollView.hasVerticalOverflow
    }

    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }
}
