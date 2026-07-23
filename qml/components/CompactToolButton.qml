import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText

    implicitWidth: 30
    implicitHeight: 28
    padding: 4
    display: AbstractButton.IconOnly
    icon.source: iconSource
    icon.width: 16
    icon.height: 16
    icon.color: palette.buttonText
    Accessible.name: toolTipText

    ToolTip.visible: hovered && toolTipText.length > 0
    ToolTip.text: toolTipText
    ToolTip.delay: 500
}
