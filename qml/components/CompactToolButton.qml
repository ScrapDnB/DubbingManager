pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    property int buttonSize: Math.max(
        macOSStyle ? 28 : 40,
        Math.ceil(controlFontMetrics.height + (macOSStyle ? 10 : 18))
    )
    property int glyphSize: Math.max(
        macOSStyle ? 16 : 24,
        Math.round(controlFontMetrics.height * (macOSStyle ? 1.0 : 1.35))
    )

    implicitWidth: buttonSize
    implicitHeight: buttonSize
    padding: macOSStyle ? 4 : 6
    hoverEnabled: true
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
            radius: 6
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
                if (control.checked)
                    return Qt.rgba(
                        control.palette.highlight.r,
                        control.palette.highlight.g,
                        control.palette.highlight.b,
                        control.hovered ? 0.26 : 0.20
                    )
                if (control.hovered)
                    return Qt.rgba(
                        control.palette.text.r,
                        control.palette.text.g,
                        control.palette.text.b,
                        0.09
                    )
                return "transparent"
            }
            border.width: control.checked ? 1 : 0
            border.color: Qt.rgba(
                control.palette.highlight.r,
                control.palette.highlight.g,
                control.palette.highlight.b,
                0.34
            )
        }
    }

    FontMetrics {
        id: controlFontMetrics
        font: control.font
    }

    PlatformToolTip {
        target: control
        text: control.toolTipText
    }
}
