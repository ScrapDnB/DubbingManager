import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText
    property int buttonSize: Math.max(
        40, Math.ceil(controlFontMetrics.height + 18)
    )
    property int glyphSize: Math.max(
        24, Math.round(controlFontMetrics.height * 1.35)
    )

    implicitWidth: buttonSize
    implicitHeight: buttonSize
    padding: 6
    display: AbstractButton.IconOnly
    icon.source: iconSource
    icon.width: glyphSize
    icon.height: glyphSize
    icon.color: palette.buttonText
    Accessible.name: toolTipText

    FontMetrics {
        id: controlFontMetrics
        font: control.font
    }

    ToolTip.visible: hovered && toolTipText.length > 0
    ToolTip.text: toolTipText
    ToolTip.delay: 500
}
