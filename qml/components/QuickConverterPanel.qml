pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Item {
    id: panel

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softMuted
    signal resultsRequested()

    readonly property var backend: appBridge ? appBridge.converter : null
    implicitHeight: content.implicitHeight

    FileDialog {
        id: sourceDialog
        title: qsTr("Выберите субтитры для конвертации")
        fileMode: FileDialog.OpenFiles
        currentFolder: panel.appBridge.uiState.folderUrl("sourceFiles")
        onVisibleChanged: if (visible) currentFolder = panel.appBridge.uiState.folderUrl("sourceFiles")
        nameFilters: ["Субтитры (*.ass *.srt)", "Все файлы (*)"]
        onAccepted: {
            if (selectedFiles.length > 0)
                panel.appBridge.uiState.rememberFile("sourceFiles", selectedFiles[0].toString())
            if (panel.backend) panel.backend.convert(selectedFiles, false)
        }
    }

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            color: panel.softHeader
            border.color: panel.softBorder

            Label {
                anchors.fill: parent
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                text: qsTr("Быстрый конвертер")
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 2

            CheckBox {
                text: qsTr("HTML")
                checked: panel.backend ? panel.backend.exportHtml : false
                onToggled: if (panel.backend) panel.backend.setFormat("html", checked)
            }
            CheckBox {
                text: qsTr("DOCX")
                checked: panel.backend ? panel.backend.exportDocx : false
                onToggled: if (panel.backend) panel.backend.setFormat("docx", checked)
            }
            CheckBox {
                text: qsTr("PDF")
                checked: panel.backend ? panel.backend.exportPdf : false
                onToggled: if (panel.backend) panel.backend.setFormat("pdf", checked)
            }
        }

        Rectangle {
            id: dropSurface
            Layout.fillWidth: true
            Layout.preferredHeight: 82
            color: dropArea.containsDrag ? panel.softHeader : palette.base
            border.color: dropArea.containsDrag ? palette.highlight : panel.softBorder
            border.width: dropArea.containsDrag ? 2 : 1
            radius: 4

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3

                Label {
                    Layout.fillWidth: true
                    text: panel.backend && panel.backend.busy
                        ? panel.backend.summary
                        : "Перетащите или выберите ASS/SRT"
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    visible: !(panel.backend && panel.backend.busy)
                    text: qsTr("Option/Alt — сначала просмотр")
                    color: panel.softMuted
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                }
                ProgressBar {
                    Layout.fillWidth: true
                    visible: panel.backend && panel.backend.busy
                    value: panel.backend ? panel.backend.progress : 0
                }
            }

            DropArea {
                id: dropArea
                anchors.fill: parent

                onDropped: function(drop) {
                    if (!drop.hasUrls || !panel.backend) return
                    if (panel.backend.convertDropped(drop.urls)) {
                        drop.acceptProposedAction()
                    }
                }
            }

            TapHandler {
                enabled: !(panel.backend && panel.backend.busy)
                onTapped: sourceDialog.open()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: panel.backend
                && (panel.backend.busy || panel.backend.hasResults)
            spacing: 6

            Label {
                Layout.fillWidth: true
                text: panel.backend ? panel.backend.summary : ""
                color: panel.softMuted
                elide: Text.ElideRight
            }
            ToolButton {
                visible: panel.backend && panel.backend.busy
                text: qsTr("×")
                Accessible.name: qsTr("Отменить конвертацию")
                onClicked: panel.backend.cancel()
                ToolTip.visible: hovered
                ToolTip.text: Accessible.name
            }
            AdaptiveButton {
                visible: panel.backend && panel.backend.hasResults && !panel.backend.busy
                text: qsTr("Результаты")
                onClicked: panel.resultsRequested()
            }
        }
    }
}
