pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int controlSize: macOSStyle ? 22 : 28
    readonly property int glyphSize: macOSStyle ? 13 : 16

    implicitWidth: controlSize
    implicitHeight: controlSize
    padding: macOSStyle ? 4 : 5
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    display: AbstractButton.IconOnly
    icon.source: iconSource
    icon.width: glyphSize
    icon.height: glyphSize
    icon.color: palette.buttonText
    Accessible.name: toolTipText

    Component.onCompleted: if (macOSStyle) {
        control.background = macOSBackground.createObject(control)
    }

    Component {
        id: macOSBackground

        Rectangle {
            radius: width / 2
            color: {
                if (!control.enabled)
                    return "transparent"
                if (control.pressed)
                    return Qt.rgba(
                        control.palette.text.r,
                        control.palette.text.g,
                        control.palette.text.b,
                        0.16
                    )
                if (control.hovered || control.visualFocus)
                    return Qt.rgba(
                        control.palette.text.r,
                        control.palette.text.g,
                        control.palette.text.b,
                        0.09
                    )
                return "transparent"
            }
        }
    }

    PlatformToolTip {
        target: control
        text: control.toolTipText
    }
}
