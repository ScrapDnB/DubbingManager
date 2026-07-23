import QtQuick
import QtQuick.Controls

Item {
    id: control

    property string text: ""
    property bool enabled: true
    property bool checked: false
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    implicitWidth: checkboxLoader.item ? checkboxLoader.item.implicitWidth : 120
    implicitHeight: checkboxLoader.item ? checkboxLoader.item.implicitHeight : 28
    Accessible.name: text

    signal toggled(bool checked)

    Loader {
        id: checkboxLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsCheckbox : nativeCheckbox
    }

    Component {
        id: nativeCheckbox

        CheckBox {
            text: control.text
            enabled: control.enabled
            checked: control.checked
            onToggled: control.toggled(checked)
        }
    }

    Component {
        id: windowsCheckbox

        CheckBox {
            id: checkbox

            text: control.text
            enabled: control.enabled
            checked: control.checked
            implicitHeight: 28
            spacing: 7
            hoverEnabled: true
            onToggled: control.toggled(checked)

            indicator: Rectangle {
                x: checkbox.leftPadding
                anchors.verticalCenter: parent.verticalCenter
                implicitWidth: 18
                implicitHeight: 18
                radius: 3
                border.width: 1
                border.color: checkbox.checked ? checkbox.palette.highlight
                    : Qt.rgba(
                        checkbox.palette.text.r, checkbox.palette.text.g,
                        checkbox.palette.text.b, checkbox.hovered ? 0.44 : 0.28
                    )
                color: checkbox.checked ? checkbox.palette.highlight
                    : checkbox.hovered ? Qt.rgba(
                        checkbox.palette.highlight.r, checkbox.palette.highlight.g,
                        checkbox.palette.highlight.b, 0.06
                    ) : "transparent"

                Label {
                    anchors.centerIn: parent
                    text: "\u2713"
                    visible: checkbox.checked
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 14
                }
            }

            contentItem: Label {
                text: checkbox.text
                color: checkbox.enabled ? checkbox.palette.text
                    : Qt.rgba(
                        checkbox.palette.text.r, checkbox.palette.text.g,
                        checkbox.palette.text.b, 0.45
                    )
                leftPadding: checkbox.indicator.width + checkbox.spacing
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
    }
}
