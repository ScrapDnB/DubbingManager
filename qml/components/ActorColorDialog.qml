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
    width: boundedWidth(macOSStyle ? 420 : 440, 36)
    height: boundedHeight(530, 36)

    onOpened: selectedColor = currentColor
    onAccepted: colorAccepted(selectedColor)

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        GridLayout {
            Layout.alignment: Qt.AlignHCenter
            columns: 10
            rowSpacing: 3
            columnSpacing: 3

            Repeater {
                model: dialog.appBridge ? dialog.appBridge.casting.actorPalette : []

                ActorColorSwatch {
                    id: swatch
                    required property string modelData

                    Layout.preferredWidth: implicitWidth
                    Layout.preferredHeight: implicitHeight
                    swatchColor: modelData
                    selected: dialog.selectedColor.toString().toUpperCase()
                        === modelData.toUpperCase()
                    well: true
                    compact: true
                    interactive: true
                    onClicked: dialog.selectedColor = swatch.modelData
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ActorColorSwatch {
                Layout.preferredWidth: 24
                Layout.preferredHeight: 24
                swatchColor: dialog.selectedColor
                well: true
                compact: true
            }

            Label {
                text: dialog.selectedColor.toString().toUpperCase()
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            AdaptiveButton {
                text: qsTr("Случайный")
                onClicked: {
                    var colors = dialog.appBridge
                        ? dialog.appBridge.casting.actorPalette : []
                    if (colors.length > 0)
                        dialog.selectedColor = colors[Math.floor(Math.random() * colors.length)]
                }
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
