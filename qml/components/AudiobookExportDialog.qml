pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property var backend
    required property color softMuted
    modal: true
    title: qsTr("Экспорт размеченного PDF")
    standardButtons: Dialog.NoButton
    width: 560
    height: 620
    property var selection: ({})
    property int selectionRevision: 0
    property var pendingChapters: []
    readonly property bool studioLayout: studioRadio.checked

    function setAll(value) {
        var next = {}
        for (var i = 0; i < backend.chapterTitles.length; ++i)
            next[backend.chapterTitles[i]] = value
        selection = next
        selectionRevision++
    }

    function selectCurrent() {
        setAll(false)
        var next = Object.assign({}, selection)
        next[backend.currentChapter] = true
        selection = next
        selectionRevision++
    }

    function selectedTitles() {
        var result = []
        for (var i = 0; i < backend.chapterTitles.length; ++i) {
            var title = backend.chapterTitles[i]
            if (selection[title] === true) result.push(title)
        }
        return result
    }

    function openExporter() {
        setAll(true)
        combinedRadio.checked = true
        readerRadio.checked = true
        open()
    }

    FileDialog {
        id: saveDialog
        title: qsTr("Экспорт размеченной аудиокниги")
        fileMode: FileDialog.SaveFile
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        nameFilters: ["PDF (*.pdf)"]
        defaultSuffix: "pdf"
        onVisibleChanged: if (visible)
            currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        onAccepted: {
            dialog.appBridge.uiState.rememberFile(
                "exports", selectedFile.toString()
            )
            if (dialog.backend.exportPdf(
                dialog.pendingChapters,
                selectedFile.toString(),
                false,
                dialog.studioLayout
            )) dialog.close()
        }
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Папка для PDF по главам")
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible)
            currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        onAccepted: {
            dialog.appBridge.uiState.rememberFolder(
                "exports", selectedFolder.toString()
            )
            if (dialog.backend.exportPdf(
                dialog.pendingChapters,
                selectedFolder.toString(),
                true,
                dialog.studioLayout
            )) dialog.close()
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label { text: qsTr("Главы"); font.bold: true }
        RowLayout {
            AdaptiveButton {
                text: qsTr("Текущая")
                onClicked: dialog.selectCurrent()
            }
            AdaptiveButton {
                text: qsTr("Все")
                onClicked: dialog.setAll(true)
            }
            AdaptiveButton {
                text: qsTr("Снять выбор")
                onClicked: dialog.setAll(false)
            }
            Item { Layout.fillWidth: true }
            Label {
                text: qsTr("Выбрано: %1").arg(
                    dialog.selectedTitles().length
                )
                color: dialog.softMuted
            }
        }

        PersistentScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: parent.width
                Repeater {
                    model: dialog.backend.chapterTitles
                    delegate: CheckBox {
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        checked: {
                            dialog.selectionRevision
                            return dialog.selection[modelData] === true
                        }
                        onToggled: {
                            var next = Object.assign({}, dialog.selection)
                            next[modelData] = checked
                            dialog.selection = next
                            dialog.selectionRevision++
                        }
                    }
                }
            }
        }

        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
        RowLayout {
            Label { text: qsTr("Файлы:"); font.bold: true }
            RadioButton {
                id: combinedRadio
                text: qsTr("Один PDF")
            }
            RadioButton {
                id: separateRadio
                text: qsTr("Каждая глава отдельно")
            }
        }
        RowLayout {
            Label { text: qsTr("Вёрстка:"); font.bold: true }
            RadioButton {
                id: readerRadio
                text: qsTr("Книжная")
            }
            RadioButton {
                id: studioRadio
                text: qsTr("Студийная")
            }
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: qsTr("Отмена")
            onClicked: dialog.close()
        }
        AdaptiveButton {
            text: qsTr("Экспортировать")
            highlighted: true
            enabled: dialog.selectedTitles().length > 0
            onClicked: {
                dialog.pendingChapters = dialog.selectedTitles()
                if (separateRadio.checked) folderDialog.open()
                else saveDialog.open()
            }
        }
    }
}
