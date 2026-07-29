pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ToolButton {
    id: control

    property url iconSource
    property string toolTipText
    // Fluent's icon-only ToolButton scales small SVGs down on Windows.  Some
    // row actions need a deliberately legible glyph instead.
    property string overlayGlyph: ""
    property string overlayIconSource: ""
    property int overlayGlyphSize: 0
    property int overlayGlyphVerticalOffset: 0
    property int buttonSize: 0
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int controlSize: buttonSize > 0
        ? buttonSize : (macOSStyle ? 22 : 30)
    readonly property int glyphSize: macOSStyle ? 13 : 20

    implicitWidth: controlSize
    implicitHeight: controlSize
    padding: macOSStyle ? 4 : 5
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    display: AbstractButton.IconOnly
    icon.source: overlayIconSource.length > 0 ? "" : iconSource
    icon.width: glyphSize
    icon.height: glyphSize
    icon.color: palette.buttonText
    Accessible.name: toolTipText

    Text {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: (control.macOSStyle ? 0 : -2)
            + control.overlayGlyphVerticalOffset
        visible: control.overlayGlyph.length > 0
        text: control.overlayGlyph
        color: control.enabled ? control.palette.buttonText : control.palette.mid
        font.pixelSize: control.overlayGlyphSize > 0
            ? control.overlayGlyphSize : (control.macOSStyle ? 15 : 24)
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        renderType: Text.NativeRendering
    }

    Image {
        anchors.centerIn: parent
        visible: control.overlayIconSource.length > 0
        source: control.overlayIconSource
        width: control.macOSStyle ? 14 : 22
        height: width
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        opacity: control.enabled ? 1 : 0.45
    }

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
