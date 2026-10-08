pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control

    property int textAlignment: Text.AlignLeft
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    padding: 0
    leftPadding: textAlignment === Text.AlignLeft ? 6 : 2
    rightPadding: textAlignment === Text.AlignRight ? 6 : 2

    contentItem: Label {
        text: control.text
        color: control.enabled
            ? (control.macOSStyle
                ? control.palette.placeholderText
                : control.palette.buttonText)
            : control.palette.placeholderText
        font.pixelSize: control.macOSStyle ? 11 : control.font.pixelSize
        font.weight: control.macOSStyle ? Font.Medium : Font.DemiBold
        horizontalAlignment: control.textAlignment
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 5
        color: control.macOSStyle && control.hovered
            ? Qt.rgba(
                control.palette.text.r,
                control.palette.text.g,
                control.palette.text.b,
                0.06
            )
            : "transparent"
    }
}
