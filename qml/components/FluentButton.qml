pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property string text: ""
    property bool enabled: true
    property bool primary: false
    property bool danger: false
    readonly property bool windowsFluent: Qt.platform.os === "windows"
    implicitWidth: buttonLoader.item ? buttonLoader.item.implicitWidth : 80
    implicitHeight: buttonLoader.item ? buttonLoader.item.implicitHeight : 32
    Accessible.name: text

    signal clicked()

    Loader {
        id: buttonLoader
        anchors.fill: parent
        sourceComponent: control.windowsFluent
            ? windowsButton : nativeButton
    }

    Component {
        id: nativeButton

        Button {
            text: control.text
            enabled: control.enabled
            onClicked: control.clicked()
        }
    }

    Component {
        id: windowsButton

        Button {
            id: button

            readonly property color accent: palette.highlight
            readonly property color borderColor: Qt.rgba(
                palette.text.r, palette.text.g, palette.text.b, 0.15
            )

            text: control.text
            enabled: control.enabled
            implicitHeight: 32
            leftPadding: 11
            rightPadding: 11
            topPadding: 5
            bottomPadding: 5
            hoverEnabled: true
            onClicked: control.clicked()

            contentItem: Label {
                text: button.text
                font: button.font
                color: !button.enabled ? Qt.rgba(
                    button.palette.buttonText.r, button.palette.buttonText.g,
                    button.palette.buttonText.b, 0.42
                ) : control.primary ? "#ffffff"
                    : control.danger ? "#b42318" : button.palette.buttonText
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                radius: 5
                border.width: 1
                border.color: !button.enabled ? Qt.rgba(
                    button.borderColor.r, button.borderColor.g,
                    button.borderColor.b, 0.45
                ) : control.primary ? button.accent
                    : control.danger ? Qt.rgba(0.71, 0.14, 0.09, 0.38)
                    : button.borderColor
                color: !button.enabled ? "#f3f3f3" : control.primary
                    ? (button.down ? Qt.darker(button.accent, 1.16)
                        : button.hovered ? Qt.lighter(button.accent, 1.06)
                        : button.accent)
                    : button.down ? Qt.rgba(
                        button.accent.r, button.accent.g, button.accent.b, 0.16
                    ) : button.hovered ? Qt.rgba(
                        button.accent.r, button.accent.g, button.accent.b, 0.08
                    ) : "#ffffff"
            }
        }
    }
}
