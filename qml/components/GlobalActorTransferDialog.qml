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

    title: qsTr("Добавить актёров из глобальной базы")
    modal: true
    standardButtons: Dialog.Close
    width: boundedWidth(560, 36)
    height: boundedHeight(500, 36)

    function openForProject() {
        selectedIds = ({})
        actorLibraryBackend.refresh()
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
                ? dialog.actorLibraryBackend.globalActorsModel : null
            delegate: Rectangle {
                required property int index
                required property string id
                required property string name
                required property bool inProject
                width: transferView.viewportWidth
                height: dialog.regularRowHeight
                color: index % 2 === 0 ? dialog.softRow : dialog.softAltRow

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8

                    CheckBox {
                        enabled: !inProject
                        checked: dialog.selectedIds[id] === true
                        onToggled: {
                            var next = Object.assign({}, dialog.selectedIds)
                            if (checked) next[id] = true
                            else delete next[id]
                            dialog.selectedIds = next
                        }
                    }

                    Label {
                        text: inProject
                            ? name + qsTr(" (уже в проекте)") : name
                        color: inProject ? dialog.softMuted : palette.text
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
                    dialog.actorLibraryBackend.addGlobalActorsToProject(
                        Object.keys(dialog.selectedIds)
                    )
                    dialog.close()
                }
            }
        }
    }
}
