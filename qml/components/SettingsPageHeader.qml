import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: header

    property string title: ""
    property string subtitle: ""
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    Layout.fillWidth: true
    spacing: macOSStyle ? 3 : 4

    Label {
        Layout.fillWidth: true
        text: header.title
        font.pixelSize: header.macOSStyle ? 20 : 22
        font.weight: Font.DemiBold
        elide: Text.ElideRight
    }

    Label {
        Layout.fillWidth: true
        visible: text.length > 0
        text: header.subtitle
        wrapMode: Text.WordWrap
        color: palette.placeholderText
        font.pixelSize: header.macOSStyle ? 12 : 13
    }
}
