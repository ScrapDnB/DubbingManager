import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    property color currentColor: "#4F81BD"
    property color selectedColor: currentColor

    signal colorAccepted(color colorValue)

    modal: true
    title: qsTr("Выберите цвет")
    standardButtons: Dialog.Ok | Dialog.Cancel
    width: 300
    height: 250

    onOpened: selectedColor = currentColor
    onAccepted: colorAccepted(selectedColor)

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 10

        GridLayout {
            Layout.alignment: Qt.AlignHCenter
            columns: 5
            rowSpacing: 6
            columnSpacing: 6

            Repeater {
                model: dialog.appBridge ? dialog.appBridge.casting.actorPalette : []

                Rectangle {
                    id: swatch
                    required property string modelData
                    readonly property bool selected: dialog.selectedColor.toString().toUpperCase() === modelData.toUpperCase()
                    readonly property bool hovered: swatchHover.hovered

                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    radius: 4
                    color: modelData
                    border.width: selected ? 3 : 1
                    border.color: selected
                        ? palette.highlight
                        : Qt.rgba(palette.text.r, palette.text.g, palette.text.b, hovered ? 0.55 : 0.28)

                    HoverHandler {
                        id: swatchHover
                    }

                    TapHandler {
                        onTapped: dialog.selectedColor = swatch.modelData
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                radius: 4
                color: dialog.selectedColor
                border.color: Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.28)
            }

            Label {
                text: dialog.selectedColor.toString().toUpperCase()
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Button {
                text: qsTr("Другой...")
                onClicked: systemColorDialog.open()
            }
        }
    }

    ColorDialog {
        id: systemColorDialog
        title: qsTr("Другой цвет")
        selectedColor: dialog.selectedColor
        onAccepted: dialog.selectedColor = selectedColor
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }
}
