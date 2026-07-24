pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property string text: ""
    property string placeholderText: ""
    property bool enabled: true
    property bool selectByMouse: false
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    implicitWidth: textFieldLoader.item ? textFieldLoader.item.implicitWidth : 120
    implicitHeight: textFieldLoader.item ? textFieldLoader.item.implicitHeight : 26
    Accessible.name: placeholderText

    signal textEdited()
    signal accepted()

    onTextChanged: {
        if (textFieldLoader.item && textFieldLoader.item.text !== text)
            textFieldLoader.item.text = text
    }

    Loader {
        id: textFieldLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsTextField : nativeTextField
    }

    Component {
        id: nativeTextField

        TextField {
            text: control.text
            placeholderText: control.placeholderText
            enabled: control.enabled
            selectByMouse: control.selectByMouse
            onTextChanged: if (control.text !== text) control.text = text
            onTextEdited: control.textEdited()
            onAccepted: control.accepted()
        }
    }

    Component {
        id: windowsTextField

        TextField {
            id: field

            text: control.text
            placeholderText: control.placeholderText
            enabled: control.enabled
            selectByMouse: control.selectByMouse
            implicitHeight: 28
            leftPadding: 9
            rightPadding: 9
            topPadding: 4
            bottomPadding: 4
            onTextChanged: if (control.text !== text) control.text = text
            onTextEdited: control.textEdited()
            onAccepted: control.accepted()

            background: Rectangle {
                radius: 5
                border.width: 1
                border.color: field.activeFocus ? field.palette.highlight
                    : Qt.rgba(
                        field.palette.text.r, field.palette.text.g,
                        field.palette.text.b, field.hovered ? 0.28 : 0.16
                    )
                color: "#ffffff"
            }
        }
    }
}
