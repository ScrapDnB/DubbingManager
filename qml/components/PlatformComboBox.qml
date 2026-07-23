import QtQuick
import QtQuick.Controls

Item {
    id: control

    property var model: null
    property string textRole: ""
    property string valueRole: ""
    property int currentIndex: 0
    property bool editable: false
    property string editText: ""
    property int count: 0
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    readonly property string currentText: comboLoader.item
        ? comboLoader.item.currentText : ""
    readonly property var currentValue: comboLoader.item
        ? comboLoader.item.currentValue : undefined
    implicitWidth: comboLoader.item ? comboLoader.item.implicitWidth : 120
    implicitHeight: comboLoader.item ? comboLoader.item.implicitHeight : 26
    Accessible.name: currentText

    signal activated(int index)
    signal accepted()

    function indexOfValue(value) {
        return comboLoader.item ? comboLoader.item.indexOfValue(value) : -1
    }

    function find(value) {
        return comboLoader.item ? comboLoader.item.find(value) : -1
    }

    onCurrentIndexChanged: {
        if (comboLoader.item && comboLoader.item.currentIndex !== currentIndex)
            comboLoader.item.currentIndex = currentIndex
    }
    onEditTextChanged: {
        if (comboLoader.item && comboLoader.item.editText !== editText)
            comboLoader.item.editText = editText
    }

    Loader {
        id: comboLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsCombo : nativeCombo
    }

    Component {
        id: nativeCombo

        ComboBox {
            model: control.model
            textRole: control.textRole
            valueRole: control.valueRole
            currentIndex: control.currentIndex
            editable: control.editable
            editText: control.editText
            onCurrentIndexChanged: if (control.currentIndex !== currentIndex)
                control.currentIndex = currentIndex
            onEditTextChanged: if (control.editText !== editText)
                control.editText = editText
            onCountChanged: control.count = count
            onActivated: control.activated(index)
            onAccepted: control.accepted()
            Component.onCompleted: control.count = count
        }
    }

    Component {
        id: windowsCombo

        ComboBox {
            id: combo

            model: control.model
            textRole: control.textRole
            valueRole: control.valueRole
            currentIndex: control.currentIndex
            editable: control.editable
            editText: control.editText
            implicitHeight: 28
            leftPadding: 9
            rightPadding: 28
            hoverEnabled: true

            onCurrentIndexChanged: if (control.currentIndex !== currentIndex)
                control.currentIndex = currentIndex
            onEditTextChanged: if (control.editText !== editText)
                control.editText = editText
            onCountChanged: control.count = count
            onActivated: control.activated(index)
            onAccepted: control.accepted()
            Component.onCompleted: control.count = count

            background: Rectangle {
                radius: 4
                border.width: 1
                border.color: combo.activeFocus ? combo.palette.highlight
                    : Qt.rgba(
                        combo.palette.text.r, combo.palette.text.g,
                        combo.palette.text.b, combo.hovered ? 0.28 : 0.16
                    )
                color: combo.down ? Qt.rgba(
                    combo.palette.highlight.r, combo.palette.highlight.g,
                    combo.palette.highlight.b, 0.10
                ) : combo.hovered ? Qt.rgba(
                    combo.palette.highlight.r, combo.palette.highlight.g,
                    combo.palette.highlight.b, 0.05
                ) : "#ffffff"
            }

            indicator: Text {
                x: combo.width - width - 9
                anchors.verticalCenter: parent.verticalCenter
                text: "\u25be"
                color: combo.palette.buttonText
                font.pixelSize: 13
            }

            delegate: ItemDelegate {
                width: combo.width - 8
                height: 28
                text: combo.textAt(index)
                highlighted: combo.highlightedIndex === index
                leftPadding: 8
                rightPadding: 8
                onClicked: {
                    combo.currentIndex = index
                    combo.activated(index)
                    combo.popup.close()
                }
                background: Rectangle {
                    radius: 3
                    color: parent.down ? Qt.rgba(
                        combo.palette.highlight.r, combo.palette.highlight.g,
                        combo.palette.highlight.b, 0.16
                    ) : parent.highlighted ? Qt.rgba(
                        combo.palette.highlight.r, combo.palette.highlight.g,
                        combo.palette.highlight.b, 0.09
                    ) : "transparent"
                }
            }

            popup: Popup {
                y: combo.height + 2
                width: combo.width
                implicitHeight: Math.min(contentItem.implicitHeight + 8, 260)
                padding: 4

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: combo.popup.visible ? combo.delegateModel : null
                    currentIndex: combo.highlightedIndex
                    ScrollIndicator.vertical: ScrollIndicator { }
                }

                background: Rectangle {
                    radius: 4
                    border.color: Qt.rgba(
                        combo.palette.text.r, combo.palette.text.g,
                        combo.palette.text.b, 0.18
                    )
                    color: "#ffffff"
                }
            }
        }
    }
}
