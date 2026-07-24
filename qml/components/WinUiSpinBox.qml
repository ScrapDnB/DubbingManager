pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property int from: 0
    property int to: 99
    property int value: 0
    property int stepSize: 1
    property bool editable: false
    property var textFromValue: function(value, locale) {
        return Number(value).toLocaleString(locale, "f", 0)
    }
    property var valueFromText: function(text, locale) {
        return Number.fromLocaleString(locale, text)
    }
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    implicitWidth: spinLoader.item ? spinLoader.item.implicitWidth : 84
    implicitHeight: spinLoader.item ? spinLoader.item.implicitHeight : 28

    signal valueModified()

    onValueChanged: {
        if (spinLoader.item && spinLoader.item.value !== value)
            spinLoader.item.value = value
    }

    Loader {
        id: spinLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsSpin : nativeSpin
    }

    Component {
        id: nativeSpin

        SpinBox {
            from: control.from
            to: control.to
            value: control.value
            stepSize: control.stepSize
            editable: control.editable
            textFromValue: function(value, locale) {
                return control.textFromValue(value, locale)
            }
            valueFromText: function(text, locale) {
                return control.valueFromText(text, locale)
            }
            onValueModified: {
                control.value = value
                control.valueModified()
            }
        }
    }

    Component {
        id: windowsSpin

        SpinBox {
            id: spin

            from: control.from
            to: control.to
            value: control.value
            stepSize: control.stepSize
            editable: control.editable
            textFromValue: function(value, locale) {
                return control.textFromValue(value, locale)
            }
            valueFromText: function(text, locale) {
                return control.valueFromText(text, locale)
            }
            implicitWidth: 84
            implicitHeight: 28
            leftPadding: 8
            rightPadding: 25
            topPadding: 3
            bottomPadding: 3
            onValueModified: {
                control.value = value
                control.valueModified()
            }

            background: Rectangle {
                radius: 4
                border.width: 1
                border.color: spin.activeFocus ? spin.palette.highlight
                    : Qt.rgba(
                        spin.palette.text.r, spin.palette.text.g,
                        spin.palette.text.b, 0.18
                    )
                color: "#ffffff"
            }

            contentItem: TextInput {
                z: 2
                text: spin.displayText
                font: spin.font
                color: spin.palette.text
                selectionColor: spin.palette.highlight
                selectedTextColor: spin.palette.highlightedText
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                readOnly: !spin.editable
                validator: spin.validator
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                selectByMouse: true
            }

            up.indicator: Rectangle {
                x: spin.width - width - 1
                y: 1
                implicitWidth: 23
                implicitHeight: 13
                radius: 3
                color: spin.up.pressed ? Qt.rgba(
                    spin.palette.highlight.r, spin.palette.highlight.g,
                    spin.palette.highlight.b, 0.18
                ) : spin.up.hovered ? Qt.rgba(
                    spin.palette.highlight.r, spin.palette.highlight.g,
                    spin.palette.highlight.b, 0.08
                ) : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "\u2303"
                    color: spin.palette.text
                    font.pixelSize: 11
                }
            }

            down.indicator: Rectangle {
                x: spin.width - width - 1
                y: spin.height - height - 1
                implicitWidth: 23
                implicitHeight: 13
                radius: 3
                color: spin.down.pressed ? Qt.rgba(
                    spin.palette.highlight.r, spin.palette.highlight.g,
                    spin.palette.highlight.b, 0.18
                ) : spin.down.hovered ? Qt.rgba(
                    spin.palette.highlight.r, spin.palette.highlight.g,
                    spin.palette.highlight.b, 0.08
                ) : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "\u2304"
                    color: spin.palette.text
                    font.pixelSize: 11
                }
            }
        }
    }
}
