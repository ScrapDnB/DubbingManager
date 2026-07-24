import QtQuick
import QtQuick.Controls

ScrollView {
    id: scrollView

    rightPadding: Qt.platform.os !== "osx" && verticalScrollBar.size < 1.0
        ? verticalScrollBar.width + 4 : 0

    ScrollBar.vertical: VisibleScrollBar {
        id: verticalScrollBar
        parent: scrollView
        x: scrollView.width - width
        y: 0
        width: Math.max(10, implicitWidth)
        height: scrollView.height
    }

    ScrollBar.horizontal: ScrollBar {
        policy: ScrollBar.AlwaysOff
    }
}
