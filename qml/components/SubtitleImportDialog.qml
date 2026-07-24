pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softMuted
    readonly property var backend: appBridge ? appBridge.subtitleImport : null

    modal: true
    title: qsTr("Импорт субтитров")
    width: boundedWidth(720, 40)
    height: boundedHeight(
        Math.min(500, Math.max(260, 190 + (backend ? backend.count : 0) * 42)),
        50
    )

    function openForFiles(files) {
        if (backend && backend.prepare(files)) {
            open()
        }
    }

    onRejected: {
        if (backend) backend.reset()
    }
    onClosed: {
        if (backend) backend.reset()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Label {
            Layout.fillWidth: true
            text: dialog.backend ? dialog.backend.summary : ""
            color: dialog.softMuted
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: dialog.softHeader
            border.color: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 12

                Label { Layout.preferredWidth: 250; text: qsTr("Файл"); font.bold: true }
                Label { Layout.fillWidth: true; text: qsTr("Название серии"); font.bold: true }
                Label { Layout.preferredWidth: 130; text: qsTr("Статус"); font.bold: true }
            }
        }

        PersistentListView {
            id: importList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.backend ? dialog.backend.model : null
            boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                id: importRow
                required property int index
                required property string fileName
                required property string episode
                required property string status
                required property string statusKind

                width: importList.viewportWidth
                height: 42
                color: importRow.index % 2 === 0 ? "transparent" : dialog.softHeader

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 12

                    Label {
                        Layout.preferredWidth: 250
                        text: importRow.fileName
                        elide: Text.ElideMiddle
                    }
                    TextField {
                        Layout.fillWidth: true
                        text: importRow.episode
                        selectByMouse: true
                        Accessible.name: qsTr("Название серии для ") + importRow.fileName
                        onTextChanged: {
                            if (dialog.backend) dialog.backend.setEpisode(importRow.index, text)
                        }
                    }
                    Label {
                        Layout.preferredWidth: 130
                        text: importRow.status
                        color: importRow.statusKind === "error"
                            ? palette.brightText
                            : dialog.softMuted
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    footer: DialogButtonBox {
        AdaptiveButton {
            text: qsTr("Отмена")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
        }

        AdaptiveButton {
            text: qsTr("Импортировать")
            enabled: dialog.backend && dialog.backend.canImport
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }

        onAccepted: {
            if (dialog.backend && dialog.backend.importAll()) dialog.close()
        }
        onRejected: dialog.reject()
    }
}
