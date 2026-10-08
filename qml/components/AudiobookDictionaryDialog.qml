pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    required property var backend
    required property color softMuted
    title: qsTr("Словарь произношений")
    width: 680
    height: 560
    minimumWidth: 520
    minimumHeight: 430

    function openDictionary(word) {
        wordField.text = word || ""
        pronunciationField.text = ""
        noteField.text = ""
        open()
        if (word) pronunciationField.forceActiveFocus()
    }
    content: ColumnLayout {
        anchors.fill: parent
        spacing: 12
        Label { text: qsTr("Ударения и подсказки"); font.bold: true }
        Label { text: qsTr("Хранятся в проекте и доступны при подготовке к записи."); color: dialog.softMuted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        PersistentListView {
            id: entries
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: dialog.backend.pronunciations
            clip: true
            delegate: ItemDelegate {
                id: entry
                required property var modelData
                width: entries.viewportWidth
                height: 58
                onClicked: {
                    wordField.text = modelData.word
                    pronunciationField.text = modelData.pronunciation
                    noteField.text = modelData.note || ""
                }
                contentItem: RowLayout {
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: entry.modelData.word + "  →  " + entry.modelData.pronunciation; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: entry.modelData.note || qsTr("Без примечания"); color: dialog.softMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    RowAccessoryButton { iconSource: "../icons/trash.svg"; toolTipText: qsTr("Удалить произношение"); onClicked: dialog.backend.removePronunciation(entry.modelData.word) }
                }
            }
            Label { anchors.centerIn: parent; visible: entries.count === 0; text: qsTr("Добавьте первое слово"); color: dialog.softMuted }
        }
        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
        GridLayout {
            columns: 2
            Layout.fillWidth: true
            Label { text: qsTr("Слово:") }
            TextField { id: wordField; objectName: "audiobookDictionaryWord"; Layout.fillWidth: true; placeholderText: qsTr("Альдебаран"); selectByMouse: true }
            Label { text: qsTr("Произношение:") }
            TextField { id: pronunciationField; Layout.fillWidth: true; placeholderText: qsTr("Альдебара́н"); selectByMouse: true }
            Label { text: qsTr("Примечание:") }
            TextField { id: noteField; Layout.fillWidth: true; placeholderText: qsTr("Необязательно"); selectByMouse: true }
        }
        RowLayout {
            AdaptiveButton {
                text: qsTr("Вставить знак ударения")
                onClicked: { pronunciationField.insert(pronunciationField.cursorPosition, "\u0301"); pronunciationField.forceActiveFocus() }
            }
            Item { Layout.fillWidth: true }
            AdaptiveButton {
                text: qsTr("Сохранить слово")
                enabled: wordField.text.trim().length > 0 && pronunciationField.text.trim().length > 0
                onClicked: {
                    dialog.backend.savePronunciation(wordField.text, pronunciationField.text, noteField.text)
                    wordField.clear(); pronunciationField.clear(); noteField.clear()
                }
            }
        }
    }
    footer: RowLayout {
        anchors.fill: parent
        Item { Layout.fillWidth: true }
        AdaptiveButton { text: qsTr("Готово"); highlighted: true; onClicked: dialog.close() }
    }
}
