pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property string text: ""
    property bool enabled: true
    property bool checked: false
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    readonly property bool hovered: radioLoader.item
        ? radioLoader.item.hovered : false
    implicitWidth: radioLoader.item ? radioLoader.item.implicitWidth : 120
    implicitHeight: radioLoader.item ? radioLoader.item.implicitHeight : 28
    Accessible.name: text

    signal toggled(bool checked)

    Loader {
        id: radioLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsRadio : nativeRadio
    }

    Component {
        id: nativeRadio

        RadioButton {
            text: control.text
            enabled: control.enabled
            checked: control.checked
            onToggled: {
                if (control.checked !== checked)
                    control.checked = checked
                control.toggled(checked)
            }
        }
    }

    Component {
        id: windowsRadio

        RadioButton {
            id: radio

            text: control.text
            enabled: control.enabled
            checked: control.checked
            implicitHeight: 28
            spacing: 7
            hoverEnabled: true
            onToggled: {
                if (control.checked !== checked)
                    control.checked = checked
                control.toggled(checked)
            }

            indicator: Rectangle {
                x: radio.leftPadding
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 18
                implicitHeight: 18
                radius: 9
                border.width: 1
                border.color: radio.checked ? radio.palette.highlight : Qt.rgba(
                    radio.palette.text.r, radio.palette.text.g,
                    radio.palette.text.b, radio.hovered ? 0.44 : 0.28
                )
                color: "transparent"

                Rectangle {
                    anchors.centerIn: parent
                    width: 8
                    height: 8
                    radius: 4
                    visible: radio.checked
                    color: radio.palette.highlight
                }
            }

            contentItem: Label {
                text: radio.text
                color: radio.enabled ? radio.palette.text : Qt.rgba(
                    radio.palette.text.r, radio.palette.text.g,
                    radio.palette.text.b, 0.45
                )
                leftPadding: radio.indicator.width + radio.spacing
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
    }
}
