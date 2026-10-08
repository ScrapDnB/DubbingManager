pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

CollapsibleSection {
    id: section
    required property var appBridge
    required property var ownerWindow
    required property color softMuted
    readonly property var book: appBridge.audiobook
    readonly property var prompter: appBridge.teleprompter
    property string episode: prompter.episode
    readonly property var currentRow: prompter.currentIndex >= 0 ? prompter.model.get(prompter.currentIndex) : ({})
    readonly property var chapterRetakes: book.retakes.filter(function(row) { return row.chapter === section.episode })
    title: qsTr("Аудиокнига · запись")
    expanded: true
    sidebarStyle: true
    visible: book.hasChapter(episode)

    function markRetake() {
        if (currentRow.sourceIds && currentRow.sourceIds.length)
            book.addRetake(episode, currentRow.sourceIds, currentRow.replicaText || "", reasonField.text)
    }
    function jumpToRun(ids) {
        for (var i = 0; i < prompter.model.rowCount(); ++i) {
            var row = prompter.model.get(i)
            if ((row.sourceIds || []).some(function(id) { return ids.indexOf(String(id)) >= 0 })) {
                prompter.jumpToIndex(i)
                return
            }
        }
    }
    Shortcut { sequence: "F8"; enabled: section.ownerWindow.visible && section.visible; onActivated: section.markRetake() }
    FileDialog {
        id: csvDialog
        title: qsTr("Список перезаписей")
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV (*.csv)"]
        defaultSuffix: "csv"
        currentFolder: section.appBridge.uiState.folderUrl("exports")
        onAccepted: {
            section.appBridge.uiState.rememberFile("exports", selectedFile.toString())
            section.book.exportRetakes(selectedFile.toString())
        }
    }
    Label {
        text: qsTr("Текущий фрагмент: %1").arg(section.currentRow.character || "—")
        Layout.fillWidth: true
        elide: Text.ElideRight
    }
    Repeater {
        model: section.book.pronunciations.filter(function(entry) { return String(section.currentRow.replicaText || "").toLowerCase().indexOf(entry.word.toLowerCase()) >= 0 })
        delegate: Label {
            required property var modelData
            text: modelData.pronunciation + (modelData.note ? " · " + modelData.note : "")
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: section.softMuted
        }
    }
    TextField { id: reasonField; placeholderText: qsTr("Причина перезаписи (необязательно)"); Layout.fillWidth: true }
    AdaptiveButton {
        text: qsTr("На перезапись · F8")
        enabled: (section.currentRow.sourceIds || []).length > 0
        onClicked: section.markRetake()
    }
    Label { text: qsTr("На перезапись: %1").arg(section.chapterRetakes.length); color: section.softMuted }
    Repeater {
        model: section.chapterRetakes
        delegate: RowLayout {
            id: retakeRow
            required property var modelData
            Layout.fillWidth: true
            ToolButton {
                text: retakeRow.modelData.note
                Layout.fillWidth: true
                Layout.maximumWidth: section.width - 40
                Accessible.name: retakeRow.modelData.note + ": " + retakeRow.modelData.text
                onClicked: section.jumpToRun(retakeRow.modelData.runIds)
                PlatformToolTip { target: parent; text: retakeRow.modelData.text }
            }
            RowAccessoryButton {
                iconSource: "../icons/clipboard-check.svg"
                toolTipText: qsTr("Перезапись выполнена")
                onClicked: section.book.removeRetake(section.episode, retakeRow.modelData.runIds)
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        AdaptiveButton { text: qsTr("Экспорт CSV…"); enabled: section.book.retakes.length > 0; onClicked: csvDialog.open() }
        Item { Layout.fillWidth: true }
    }
    AdaptiveButton {
        text: section.book.recordedChapters.indexOf(section.episode) >= 0 ? qsTr("Глава записана") : qsTr("Завершить главу")
        enabled: section.chapterRetakes.length === 0 && section.book.recordedChapters.indexOf(section.episode) < 0
        onClicked: { section.book.markChapterRecorded(section.episode); section.book.flush() }
    }
    Label {
        text: qsTr("Аудио записывается в Reaper. Здесь сохраняются отметки и позиция чтения.")
        color: section.softMuted
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
}
