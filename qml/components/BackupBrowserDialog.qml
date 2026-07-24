pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    readonly property var backend: appBridge ? appBridge.project : null
    property string selectedPath: ""
    property string selectedName: ""

    modal: true
    title: qsTr("Резервные копии проекта")
    standardButtons: Dialog.NoButton
    width: boundedWidth(680, 36)
    height: boundedHeight(480, 36)

    function openBrowser() {
        selectedPath = ""
        selectedName = ""
        backupsView.currentIndex = -1
        backend.refreshBackups()
        open()
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        AdaptiveButton {
            text: qsTr("Обновить")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: dialog.backend.refreshBackups()
        }
        AdaptiveButton {
            text: qsTr("Восстановить")
            enabled: dialog.selectedPath.length > 0
            highlighted: dialog.macOSStyle
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: restoreDialog.open()
        }
        AdaptiveButton {
            text: qsTr("Закрыть")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Label {
            Layout.fillWidth: true
            text: qsTr("Перед восстановлением текущая версия проекта будет сохранена отдельно.")
            wrapMode: Text.WordWrap
            color: dialog.softMuted
        }

        TableHeaderSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: dialog.tableHeaderHeight
            softHeader: dialog.softHeader
            softBorder: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                TableHeaderLabel { text: qsTr("Копия"); Layout.fillWidth: true }
                TableHeaderLabel { text: qsTr("Изменена"); Layout.preferredWidth: 140 }
                TableHeaderLabel { text: qsTr("Размер"); Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
            }
        }

        PersistentListView {
            id: backupsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.backend ? dialog.backend.backupsModel : null
            activeFocusOnTab: true
            Accessible.name: qsTr("Резервные копии проекта")

            delegate: Rectangle {
                id: backupRow
                required property int index
                required property var model
                width: backupsView.viewportWidth
                height: dialog.compactRowHeight
                color: dialog.selectedPath === model.path
                    ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)
                    : (hover.hovered ? dialog.softHover
                        : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow))

                SystemPalette { id: palette }
                HoverHandler { id: hover }
                TapHandler {
                    onTapped: {
                        backupsView.currentIndex = backupRow.index
                        dialog.selectedPath = backupRow.model.path
                        dialog.selectedName = backupRow.model.name
                    }
                    onDoubleTapped: restoreDialog.open()
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    Label { text: backupRow.model.name; elide: Text.ElideMiddle; Layout.fillWidth: true }
                    Label { text: backupRow.model.modified; Layout.preferredWidth: 140 }
                    Label { text: backupRow.model.size; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: backupsView.count === 0
                text: qsTr("Резервных копий пока нет")
                color: dialog.softMuted
            }
        }
    }

    NativeDialogWindow {
        id: restoreDialog
        ownerWindow: dialog
        modal: true
        title: qsTr("Восстановить проект")
        standardButtons: Dialog.NoButton
        width: 440
        height: 190

        footer: DialogButtonBox {
            anchors.fill: parent
            AdaptiveButton {
                text: qsTr("Восстановить")
                highlighted: restoreDialog.macOSStyle
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                onClicked: {
                    restoreDialog.close()
                    dialog.close()
                    dialog.backend.restoreBackup(dialog.selectedPath)
                }
            }
            AdaptiveButton {
                text: qsTr("Отмена")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: restoreDialog.close()
            }
        }

        content: Label {
            anchors.fill: parent
            text: qsTr("Восстановить «") + dialog.selectedName
                + "» вместо текущей версии проекта?"
            wrapMode: Text.WordWrap
        }
    }
}
