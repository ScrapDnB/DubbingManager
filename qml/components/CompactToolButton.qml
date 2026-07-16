import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText

    implicitWidth: 32
    implicitHeight: 30
    padding: 5
    display: AbstractButton.IconOnly
    icon.source: iconSource
    icon.width: 17
    icon.height: 17
    icon.color: palette.buttonText
    Accessible.name: toolTipText

    ToolTip.visible: hovered && toolTipText.length > 0
    ToolTip.text: toolTipText
    ToolTip.delay: 500
}
