import QtQuick.Controls
import QtQuick.Layouts

Button {
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    Layout.minimumWidth: implicitWidth
    Layout.minimumHeight: implicitHeight
    Layout.maximumWidth: macOSStyle ? implicitWidth : Number.POSITIVE_INFINITY
}
