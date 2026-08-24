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
    property string pendingReviewText: ""

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

    AudiobookExportDialog {
        id: exportDialog
        ownerWindow: window
        appBridge: window.appBridge
        backend: window.backend
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
            AdaptiveButton {
                text: qsTr("Экспорт PDF")
                Layout.preferredWidth: 110
                enabled: window.backend.chapterTitles.length > 0
                onClicked: exportDialog.openExporter()
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
            PlatformComboBox {
                id: fontBox
                model: window.backend.fontFamilies
                Layout.preferredWidth: 180
                Component.onCompleted: currentIndex = Math.max(0, find(window.backend.fontFamily))
                onActivated: window.backend.setFontFamily(currentText)
            }
            ToolButton {
                id: zoomOutButton
                text: qsTr("−")
                enabled: window.backend.zoom > -5
                PlatformToolTip {
                    target: zoomOutButton
                    text: qsTr("Уменьшить текст")
                }
                onClicked: window.backend.setZoom(window.backend.zoom - 1)
            }
            Label {
                text: Math.round((1 + window.backend.zoom * 0.1) * 100) + "%"
                horizontalAlignment: Text.AlignHCenter
                Layout.preferredWidth: 46
            }
            ToolButton {
                id: zoomInButton
                text: qsTr("+")
                enabled: window.backend.zoom < 10
                PlatformToolTip {
                    target: zoomInButton
                    text: qsTr("Увеличить текст")
                }
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
                background: Rectangle {
                    color: window.macOSStyle ? "transparent" : palette.window
                    border.color: window.macOSStyle
                        ? "transparent" : window.softBorder
                }

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
                            height: window.macOSStyle ? 28 : 32
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
                border.color: window.macOSStyle
                    ? "transparent" : window.softBorder
                clip: true

                WebEngineView {
                    id: editorView
                    anchors.fill: parent
                    anchors.margins: window.macOSStyle ? 0 : 1
                    webChannel: editorChannel
                    backgroundColor: palette.base
                    onLoadingChanged: function(request) {
                        if (request.status === WebEngineView.LoadSucceededStatus) {
                            window.syncSlots()
                            if (window.pendingReviewText.length > 0) {
                                editorView.runJavaScript(
                                    "window.dmEditor && window.dmEditor.focusText("
                                    + JSON.stringify(window.pendingReviewText) + ")"
                                )
                                window.pendingReviewText = ""
                            }
                        }
                    }
                }
            }

            Pane {
                SplitView.preferredWidth: 330
                SplitView.minimumWidth: 285
                SplitView.maximumWidth: 430
                padding: 8
                background: Rectangle {
                    color: window.macOSStyle ? "transparent" : palette.window
                    border.color: window.macOSStyle
                        ? "transparent" : window.softBorder
                }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 7

                    TabBar {
                        id: sideTabs
                        Layout.fillWidth: true
                        TabButton { text: qsTr("Разметка") }
                        TabButton {
                            text: window.backend.reviewCount > 0
                                ? qsTr("Проверка (%1)").arg(
                                    window.backend.reviewCount
                                )
                                : qsTr("Проверка")
                        }
                    }

                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: sideTabs.currentIndex

                        AudiobookMarkupPane {
                            backend: window.backend
                            editorView: editorView
                            softMuted: window.softMuted
                            macOSStyle: window.macOSStyle
                        }
                        AudiobookReviewPane {
                            backend: window.backend
                            softMuted: window.softMuted
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
            visible: !window.macOSStyle
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
        function onReviewNavigationRequested(text) {
            window.pendingReviewText = text
            editorView.runJavaScript(
                "window.dmEditor && window.dmEditor.focusText("
                + JSON.stringify(text) + ")"
            )
        }
    }
}
