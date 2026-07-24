pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtWebChannel
import QtWebEngine

NativeDialogWindow {
    id: window
    objectName: "audiobookWindow"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    readonly property var backend: appBridge.audiobook

    title: qsTr("Аудиокнига")
    modal: false
    width: boundedWidth(1420, 20)
    height: boundedHeight(900, 20)
    minimumWidth: 940
    minimumHeight: 650
    standardButtons: Dialog.NoButton

    function openWorkspace() {
        backend.prepare()
        open()
    }

    function syncSlots() {
        editorView.runJavaScript(
            "window.dmEditor && window.dmEditor.setSlots(" + JSON.stringify(backend.slots) + ")"
        )
    }

    function reloadEditor() {
        editorView.url = backend.editorUrl
    }

    FileDialog {
        id: pdfDialog
        title: qsTr("Импорт PDF книги")
        currentFolder: window.appBridge.uiState.folderUrl("documents")
        onVisibleChanged: if (visible) currentFolder = window.appBridge.uiState.folderUrl("documents")
        nameFilters: ["PDF (*.pdf)"]
        onAccepted: {
            window.appBridge.uiState.rememberFile("documents", selectedFile.toString())
            window.backend.importPdf(selectedFile.toString())
        }
    }

    QtObject {
        id: audiobookPage
        WebChannel.id: "audiobookPage"
        function updateState(html, segments) {
            window.backend.updateEditorState(String(html), String(segments))
        }
    }

    WebChannel {
        id: editorChannel
        registeredObjects: [audiobookPage]
    }

    ChapterMarkupWindow {
        id: markupWindow
        ownerWindow: window
        backend: window.backend
        softBorder: window.softBorder
        softHeader: window.softHeader
        softMuted: window.softMuted
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            AdaptiveButton {
                text: qsTr("Импорт PDF")
                Layout.preferredWidth: 105
                enabled: !window.backend.importing
                onClicked: pdfDialog.open()
            }
            AdaptiveButton {
                text: qsTr("Структура глав")
                Layout.preferredWidth: 120
                enabled: window.backend.canEditMarkup && !window.backend.importing
                onClicked: markupWindow.openEditor()
            }
            Label {
                text: window.backend.sourceName
                color: window.softMuted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            ProgressBar {
                visible: window.backend.importing
                from: 0
                to: Math.max(1, window.backend.importTotal)
                value: window.backend.importCurrent
                indeterminate: window.backend.importTotal <= 0
                Layout.preferredWidth: 180
            }
            ComboBox {
                id: fontBox
                model: window.backend.fontFamilies
                Layout.preferredWidth: 180
                Component.onCompleted: currentIndex = Math.max(0, find(window.backend.fontFamily))
                onActivated: window.backend.setFontFamily(currentText)
            }
            ToolButton {
                text: qsTr("−")
                enabled: window.backend.zoom > -5
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Уменьшить текст")
                onClicked: window.backend.setZoom(window.backend.zoom - 1)
            }
            Label {
                text: Math.round((1 + window.backend.zoom * 0.1) * 100) + "%"
                horizontalAlignment: Text.AlignHCenter
                Layout.preferredWidth: 46
            }
            ToolButton {
                text: qsTr("+")
                enabled: window.backend.zoom < 10
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Увеличить текст")
                onClicked: window.backend.setZoom(window.backend.zoom + 1)
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Pane {
                SplitView.preferredWidth: 230
                SplitView.minimumWidth: 180
                SplitView.maximumWidth: 330
                padding: 6

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 6
                    Label { text: qsTr("Главы"); font.bold: true }
                    PersistentListView {
                        id: chaptersView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: window.backend.chaptersModel
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        delegate: ItemDelegate {
                            required property string title
                            required property bool selected
                            width: chaptersView.viewportWidth
                            height: 32
                            text: title
                            highlighted: selected
                            onClicked: window.backend.selectChapter(title)
                        }
                        Label {
                            anchors.centerIn: parent
                            visible: parent.count === 0
                            text: qsTr("Импортируйте PDF")
                            color: window.softMuted
                        }
                    }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 400
                color: palette.base
                border.color: window.softBorder
                clip: true

                WebEngineView {
                    id: editorView
                    anchors.fill: parent
                    anchors.margins: 1
                    webChannel: editorChannel
                    backgroundColor: "#ecebea"
                    onLoadingChanged: function(request) {
                        if (request.status === WebEngineView.LoadSucceededStatus)
                            window.syncSlots()
                    }
                }
            }

            Pane {
                SplitView.preferredWidth: 330
                SplitView.minimumWidth: 285
                SplitView.maximumWidth: 430
                padding: 8

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 7

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: qsTr("Разметка ролей"); font.bold: true; Layout.fillWidth: true }
                        Label { text: qsTr("Клавиши 1–9"); color: window.softMuted }
                    }

                    PersistentScrollView {
                        id: slotsScroll
                        Layout.fillWidth: true
                        Layout.preferredHeight: 330
                        clip: true
                        contentWidth: availableWidth

                        ColumnLayout {
                            width: slotsScroll.availableWidth
                            spacing: 5

                            Repeater {
                                model: window.backend.slotsModel
                                delegate: RowLayout {
                                    id: slotRow
                                    required property int slotIndex
                                    required property string character
                                    required property int actorIndex
                                    Layout.fillWidth: true
                                    spacing: 5

                                    Label {
                                        text: String(slotRow.slotIndex + 1)
                                        horizontalAlignment: Text.AlignHCenter
                                        Layout.preferredWidth: 18
                                    }
                                    ComboBox {
                                        id: characterBox
                                        editable: true
                                        model: window.backend.characterNames
                                        Component.onCompleted: currentIndex = Math.max(0, find(slotRow.character))
                                        Layout.fillWidth: true
                                        Layout.preferredWidth: 120
                                        onAccepted: {
                                            var actor = window.backend.actorsModel.get(actorBox.currentIndex)
                                            window.backend.setSlot(slotRow.slotIndex, editText, actor.actorId || "")
                                            window.syncSlots()
                                        }
                                    }
                                    ComboBox {
                                        id: actorBox
                                        model: window.backend.actorsModel
                                        textRole: "name"
                                        Component.onCompleted: currentIndex = slotRow.actorIndex
                                        Layout.fillWidth: true
                                        Layout.preferredWidth: 120
                                        onActivated: function(comboIndex) {
                                            var actor = window.backend.actorsModel.get(currentIndex)
                                            var character = characterBox.editText
                                            var actorId = actor.actorId || ""
                                            var color = window.backend.actorColor(actorId)
                                            editorView.runJavaScript(
                                                "window.dmEditor.recolor(" + JSON.stringify(character)
                                                + "," + JSON.stringify(actorId) + ","
                                                + JSON.stringify(color) + ")"
                                            )
                                            window.backend.setSlot(slotRow.slotIndex, character, actorId)
                                        }
                                    }
                                    ToolButton {
                                        text: qsTr("✓")
                                        enabled: characterBox.editText.trim().length > 0
                                        ToolTip.visible: hovered
                                        ToolTip.text: qsTr("Разметить выделение")
                                        onClicked: {
                                            var actor = window.backend.actorsModel.get(actorBox.currentIndex)
                                            var character = characterBox.editText
                                            var actorId = actor.actorId || ""
                                            var color = window.backend.actorColor(actorId)
                                            editorView.runJavaScript(
                                                "window.dmEditor.applyMarkup(" + JSON.stringify(character)
                                                + "," + JSON.stringify(actorId) + ","
                                                + JSON.stringify(color) + ")"
                                            )
                                            window.backend.setSlot(slotRow.slotIndex, character, actorId)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    AdaptiveButton {
                        text: qsTr("Снять разметку с выделения")
                        Layout.fillWidth: true
                        onClicked: editorView.runJavaScript("window.dmEditor.clearMarkup()")
                    }

                    ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: qsTr("В главе"); font.bold: true; Layout.fillWidth: true }
                        Label { text: window.backend.statsSummary; color: window.softMuted }
                    }
                    PersistentListView {
                        id: markedItemsView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: window.backend.markedModel
                        clip: true
                        delegate: ItemDelegate {
                            id: markedRow
                            required property string character
                            required property string summary
                            width: markedItemsView.viewportWidth
                            height: 32
                            contentItem: RowLayout {
                                Label { text: markedRow.character; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: markedRow.summary; color: window.softMuted }
                            }
                        }
                    }
                }
            }
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        implicitHeight: 32
        spacing: 8
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: qsTr("Закрыть")
            Layout.preferredWidth: 100
            onClicked: window.close()
        }
        AdaptiveButton {
            text: qsTr("Сохранить главу")
            Layout.preferredWidth: 130
            enabled: window.backend.currentChapter.length > 0
            onClicked: window.backend.saveCurrent()
        }
        AdaptiveButton {
            text: qsTr("Сохранить всё")
            highlighted: true
            Layout.preferredWidth: 120
            enabled: window.backend.currentChapter.length > 0
            onClicked: window.backend.saveAll()
        }
    }

    Connections {
        target: window.backend
        function onEditorChanged() { window.reloadEditor() }
        function onChanged() { window.syncSlots() }
    }
}
