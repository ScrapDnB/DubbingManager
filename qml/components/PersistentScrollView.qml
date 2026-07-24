import QtQuick.Controls

ScrollView {
    rightPadding: verticalScrollBar.visible
        ? verticalScrollBar.implicitWidth + 4 : 0
    bottomPadding: horizontalScrollBar.visible
        ? horizontalScrollBar.implicitHeight + 4 : 0

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
    }
    ScrollBar.horizontal: VisibleScrollBar {
        id: horizontalScrollBar
    }
}
