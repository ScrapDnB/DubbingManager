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

                ActorColorSwatch {
                    id: swatch
                    required property string modelData

                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    swatchColor: modelData
                    selected: dialog.selectedColor.toString().toUpperCase()
                        === modelData.toUpperCase()
                    well: true
                    interactive: true
                    onClicked: dialog.selectedColor = swatch.modelData
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ActorColorSwatch {
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                swatchColor: dialog.selectedColor
                well: true
            }

            Label {
                text: dialog.selectedColor.toString().toUpperCase()
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            AdaptiveButton {
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
