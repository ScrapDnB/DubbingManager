import QtQuick
import QtQuick.Controls

Label {
    id: control

    readonly property bool macOSStyle: Qt.platform.os === "osx"

    color: macOSStyle ? palette.placeholderText : palette.text
    font.pixelSize: macOSStyle ? 11 : 13
    font.weight: macOSStyle ? Font.Medium : Font.DemiBold
    verticalAlignment: Text.AlignVCenter
    elide: Text.ElideRight
}
