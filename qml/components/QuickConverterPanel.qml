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
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    implicitHeight: content.implicitHeight
    // The sidebar owns the available width. In particular, Fluent metrics on
    // Windows 10 can make three check boxes wider than a narrow sidebar.
    implicitWidth: 0
    Layout.minimumWidth: 0

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
            Layout.preferredHeight: panel.macOSStyle ? 24 : 28
            color: panel.macOSStyle ? "transparent" : panel.softHeader
            border.color: panel.macOSStyle ? "transparent" : panel.softBorder

            Label {
                anchors.fill: parent
                anchors.leftMargin: panel.macOSStyle ? 0 : 6
                anchors.rightMargin: panel.macOSStyle ? 0 : 6
                text: qsTr("Быстрый конвертер")
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }
        }

        Flow {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 4

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
            CheckBox {
                text: qsTr("Построчно")
                checked: panel.backend ? panel.backend.lineByLine : false
                onToggled: if (panel.backend) panel.backend.setLineByLine(checked)
                Accessible.description: qsTr("Не объединять соседние реплики")
            }
        }

        Rectangle {
            id: dropSurface
            Layout.fillWidth: true
            Layout.preferredHeight: 82
            color: dropArea.containsDrag
                ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.10)
                : (panel.macOSStyle
                    ? Qt.rgba(palette.base.r, palette.base.g, palette.base.b, 0.45)
                    : palette.base)
            border.color: dropArea.containsDrag
                ? palette.highlight
                : (panel.macOSStyle
                    ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.14)
                    : panel.softBorder)
            border.width: dropArea.containsDrag ? 2 : 1
            radius: panel.macOSStyle ? 8 : 4

            HoverHandler {
                id: dropHover
            }

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
                    text: Qt.platform.os === "osx"
                        ? qsTr("С зажатым Option — сначала просмотр")
                        : qsTr("С зажатым Alt — сначала просмотр")
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

            CompactToolButton {
                id: settingsPreviewButton
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.margins: 5
                buttonSize: 38
                glyphSize: 23
                visible: dropHover.hovered
                    && !dropArea.containsDrag
                    && !(panel.backend && panel.backend.busy)
                iconSource: Qt.resolvedUrl("../icons/settings.svg")
                toolTipText: qsTr("Настройки быстрого конвертера")
                onClicked: if (panel.backend) {
                    panel.backend.openSettingsPreview()
                }
            }

            TapHandler {
                enabled: !(panel.backend && panel.backend.busy)
                    && !settingsPreviewButton.hovered
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
                id: cancelConversionButton
                visible: panel.backend && panel.backend.busy
                text: qsTr("×")
                Accessible.name: qsTr("Отменить конвертацию")
                onClicked: panel.backend.cancel()
                PlatformToolTip {
                    target: cancelConversionButton
                    text: cancelConversionButton.Accessible.name
                }
            }
            AdaptiveButton {
                visible: panel.backend && panel.backend.hasResults && !panel.backend.busy
                text: qsTr("Результаты")
                onClicked: panel.resultsRequested()
            }
        }
    }
}
