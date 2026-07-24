import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    required property var appBridge
    readonly property var actorLibraryBackend: appBridge
        ? appBridge.actorLibrary : null
    required property color softRow
    required property color softAltRow
    required property color softMuted
    property var selectedIds: ({})

    title: qsTr("Добавить актёров в глобальную базу")
    modal: true
    standardButtons: Dialog.Close
    width: boundedWidth(560, 36)
    height: boundedHeight(500, 36)

    function openForProject() {
        selectedIds = ({})
        actorLibraryBackend.refreshProjectActorTransfer()
        open()
    }

    content: ColumnLayout {
        anchors.fill: parent
        PersistentListView {
            id: transferView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.actorLibraryBackend
                ? dialog.actorLibraryBackend.projectActorTransferModel : null
            delegate: Rectangle {
                required property int index
                required property string actorId
                required property string label
                required property bool exists
                width: transferView.viewportWidth
                height: 36
                color: index % 2 === 0 ? dialog.softRow : dialog.softAltRow
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    CheckBox {
                        enabled: !exists
                        checked: dialog.selectedIds[actorId] === true
                        onToggled: {
                            var next = Object.assign({}, dialog.selectedIds)
                            if (checked) next[actorId] = true
                            else delete next[actorId]
                            dialog.selectedIds = next
                        }
                    }
                    Label {
                        text: label
                        color: exists ? dialog.softMuted : palette.text
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: qsTr("Выбрано: ") + Object.keys(dialog.selectedIds).length
                color: dialog.softMuted
                Layout.fillWidth: true
            }
            AdaptiveButton {
                text: qsTr("Добавить")
                enabled: Object.keys(dialog.selectedIds).length > 0
                onClicked: {
                    dialog.actorLibraryBackend.addProjectActorsToGlobal(
                        Object.keys(dialog.selectedIds)
                    )
                    dialog.selectedIds = ({})
                }
            }
        }
    }
}
