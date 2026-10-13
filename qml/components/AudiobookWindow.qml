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
    property int workflow: 0
    property bool sidebarVisible: true
    property bool inspectorVisible: true
    property bool editorLoaded: false
    property string pendingFocusId: ""
    property string pendingFocusText: ""
    property string pendingImport: ""
    signal recordingRequested(string chapter)

    title: appBridge.project.name + qsTr(" — Аудиокнига")
    modal: false
    width: 1420
    height: 900
    minimumWidth: 1000
    minimumHeight: 680
    contentMargin: 0
    standardButtons: Dialog.NoButton

    function openWorkspace() {
        backend.prepare()
        workflow = 0
        open()
    }
    function syncEditor() {
        if (!editorLoaded) return
        editorView.runJavaScript("window.dmEditor && window.dmEditor.setSlots(" + JSON.stringify(backend.slots) + "," + JSON.stringify(backend.roles) + ")")
        editorView.runJavaScript("window.dmEditor && window.dmEditor.setPresentation(" + JSON.stringify(backend.fontFamily) + "," + backend.zoom + "," + darkPalette + ")")
    }
    function reloadEditor() {
        editorLoaded = false
        editorView.url = backend.editorUrl
    }
    function focusPending() {
        if (!editorLoaded || !pendingFocusId.length && !pendingFocusText.length) return
        editorView.runJavaScript("window.dmEditor && window.dmEditor.focusRun(" + JSON.stringify(pendingFocusId) + "," + JSON.stringify(pendingFocusText) + ")")
        pendingFocusId = ""; pendingFocusText = ""
    }
    function saveProject() { backend.flush(); appBridge.project.save() }
    function startRecording() {
        backend.flush()
        if (backend.currentChapter.length > 0) recordingRequested(backend.currentChapter)
    }
    onDarkPaletteChanged: syncEditor()
    onClosing: backend.flush()
    onActiveChanged: if (!active && visible) backend.flush()

    Shortcut { sequences: [StandardKey.Save]; enabled: window.visible; onActivated: window.saveProject() }
    Shortcut { sequences: [StandardKey.Find]; enabled: window.visible; onActivated: { bookSearch.forceActiveFocus(); bookSearch.selectAll() } }

    FileDialog {
        id: importDialog
        title: qsTr("Импорт книги")
        currentFolder: window.appBridge.uiState.folderUrl("documents")
        nameFilters: [qsTr("Книги (*.pdf *.docx *.epub *.txt)"), "PDF (*.pdf)", "DOCX (*.docx)", "EPUB (*.epub)", "TXT (*.txt)"]
        onVisibleChanged: if (visible) currentFolder = window.appBridge.uiState.folderUrl("documents")
        onAccepted: {
            window.appBridge.uiState.rememberFile("documents", selectedFile.toString())
            window.pendingImport = selectedFile.toString()
            if (window.backend.chapterTitles.length > 0) replaceDialog.open()
            else window.backend.importBook(window.pendingImport)
        }
    }
    NativeDialogWindow {
        id: replaceDialog
        ownerWindow: window
        title: qsTr("Заменить книгу?")
        width: 460; height: 210
        content: Label { anchors.fill: parent; text: qsTr("Текущий текст и структура глав будут заменены. Замену можно отменить через меню Правка."); wrapMode: Text.WordWrap }
        footer: RowLayout {
            anchors.fill: parent
            Item { Layout.fillWidth: true }
            AdaptiveButton { text: qsTr("Отмена"); onClicked: replaceDialog.close() }
            AdaptiveButton { text: qsTr("Заменить"); highlighted: true; onClicked: { window.backend.importBook(window.pendingImport); replaceDialog.close() } }
        }
    }

    QtObject {
        id: audiobookPage
        WebChannel.id: "audiobookPage"
        function updateState(html, segments, chapter) {
            if (String(chapter) === window.backend.editorToken)
                window.backend.updateEditorState(String(html), String(segments))
        }
        function updateSelection(payload, chapter) {
            if (String(chapter) === window.backend.editorToken) window.backend.updateSelection(String(payload))
        }
        function editorReady(chapter) {
            if (String(chapter) !== window.backend.editorToken) return
            window.editorLoaded = true
            window.syncEditor()
            window.focusPending()
        }
        function saveProject() { window.saveProject() }
        function addPronunciation(word) { dictionaryDialog.openDictionary(String(word)) }
    }
    WebChannel { id: editorChannel; registeredObjects: [audiobookPage] }

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
    AudiobookDictionaryDialog { id: dictionaryDialog; ownerWindow: window; backend: window.backend; softMuted: window.softMuted }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 0
        MenuBar {
            visible: window.windowsStyle
            Layout.fillWidth: true
            Menu {
                title: qsTr("Файл")
                MenuItem { text: qsTr("Автосохранение"); checkable: true; checked: window.backend.autoSave; onTriggered: window.backend.setAutoSave(checked) }
                MenuItem { text: qsTr("Импорт книги…"); enabled: !window.backend.importing; onTriggered: importDialog.open() }
                MenuItem { text: qsTr("Сохранить проект"); onTriggered: window.saveProject() }
                MenuItem { text: qsTr("Экспорт PDF…"); enabled: window.backend.chapterTitles.length > 0; onTriggered: exportDialog.openExporter() }
            }
            Menu {
                title: qsTr("Правка")
                MenuItem { text: qsTr("Отменить в проекте"); enabled: window.appBridge.project.canUndo; onTriggered: { window.backend.flush(); window.appBridge.project.undo() } }
                MenuItem { text: qsTr("Повторить в проекте"); enabled: window.appBridge.project.canRedo; onTriggered: window.appBridge.project.redo() }
            }
            Menu {
                title: qsTr("Вид")
                MenuItem { text: qsTr("Главы"); checkable: true; checked: window.sidebarVisible; onTriggered: window.sidebarVisible = !window.sidebarVisible }
                MenuItem { text: qsTr("Инспектор"); checkable: true; checked: window.inspectorVisible; onTriggered: window.inspectorVisible = !window.inspectorVisible }
            }
            Menu {
                title: qsTr("Инструменты")
                MenuItem { text: qsTr("Структура глав…"); enabled: window.backend.canEditMarkup; onTriggered: { window.backend.flush(); markupWindow.openEditor() } }
                MenuItem { text: qsTr("Словарь произношений…"); onTriggered: dictionaryDialog.openDictionary("") }
                MenuItem { text: qsTr("Запись в телесуфлёре"); enabled: window.backend.chapterTitles.length > 0; onTriggered: window.startRecording() }
            }
        }
        Pane {
            Layout.fillWidth: true
            padding: window.macOSStyle ? 12 : 8
            background: Rectangle { color: window.macOSStyle ? "transparent" : window.palette.window }
            contentItem: Item {
                implicitHeight: Math.max(bookProjectControls.implicitHeight,
                    workflowTabs.implicitHeight, bookToolControls.implicitHeight)
                RowLayout {
                    id: bookProjectControls
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(240, (parent.width - workflowTabs.width) / 2 - 12)
                    spacing: 12
                    CompactToolButton {
                        iconSource: "../icons/audiobook.svg"
                        toolTipText: qsTr("Показать или скрыть главы")
                        onClicked: window.sidebarVisible = !window.sidebarVisible
                    }
                    Label {
                        text: window.appBridge.project.name
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        elide: Text.ElideRight
                    }
                }
                NavigationTabBar {
                    id: workflowTabs
                    objectName: "audiobookWorkflowTabs"
                    anchors.centerIn: parent
                    model: [qsTr("Подготовка"), qsTr("Проверка"), qsTr("Запись")]
                    tabWidth: window.macOSStyle ? 105 : 115
                    currentIndex: window.workflow
                    softMuted: window.softMuted
                    onActivated: function(index) {
                        if (index === 2) { window.startRecording(); currentIndex = window.workflow }
                        else { window.workflow = index; if (index === 1) window.backend.openNextReviewItem() }
                    }
                }
                RowLayout {
                    id: bookToolControls
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12
                    CompactToolButton { iconSource: "../icons/folder-open.svg"; toolTipText: qsTr("Импорт книги"); enabled: !window.backend.importing; onClicked: importDialog.open() }
                    CompactToolButton { iconSource: "../icons/save.svg"; toolTipText: qsTr("Сохранить проект"); onClicked: window.saveProject() }
                    CompactToolButton { iconSource: "../icons/save-as.svg"; toolTipText: qsTr("Экспорт PDF"); enabled: window.backend.chapterTitles.length > 0; onClicked: exportDialog.openExporter() }
                    CompactToolButton { iconSource: "../icons/settings.svg"; toolTipText: qsTr("Показать или скрыть инспектор"); onClicked: window.inspectorVisible = !window.inspectorVisible }
                }
            }
        }
        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true; Layout.preferredHeight: 1 }
        Pane {
            Layout.fillWidth: true
            padding: window.macOSStyle ? 6 : 8
            contentItem: RowLayout {
                spacing: 8
                CompactToolButton {
                    iconSource: "../icons/undo.svg"; toolTipText: qsTr("Отменить правку текста")
                    enabled: Boolean(window.backend.selection.canUndo)
                    onClicked: editorView.runJavaScript("window.dmEditor && window.dmEditor.undo()")
                }
                CompactToolButton {
                    iconSource: "../icons/redo.svg"; toolTipText: qsTr("Повторить правку текста")
                    enabled: Boolean(window.backend.selection.canRedo)
                    onClicked: editorView.runJavaScript("window.dmEditor && window.dmEditor.redo()")
                }
                ToolSeparator { orientation: Qt.Vertical; Layout.preferredHeight: 22 }
                PlatformComboBox {
                    id: fontBox
                    model: window.backend.fontFamilies
                    Layout.preferredWidth: 150
                    currentIndex: Math.max(0, find(window.backend.fontFamily))
                    onActivated: window.backend.setFontFamily(currentText)
                    Accessible.name: qsTr("Шрифт текста книги")
                }
                PlatformComboBox {
                    model: ["70%", "80%", "90%", "100%", "110%", "120%", "130%", "140%", "150%", "160%", "170%", "180%"]
                    currentIndex: Math.max(0, window.backend.zoom + 3)
                    Layout.preferredWidth: 90
                    onActivated: window.backend.setZoom(currentIndex - 3)
                    Accessible.name: qsTr("Размер текста")
                }
                Item { Layout.fillWidth: true }
                ProgressBar {
                    visible: window.backend.importing
                    Layout.preferredWidth: 100
                    from: 0; to: Math.max(1, window.backend.importTotal)
                    value: window.backend.importCurrent
                    indeterminate: window.backend.importTotal <= 0
                }
                TextField {
                    id: bookSearch
                    objectName: "audiobookBookSearch"
                    Layout.preferredWidth: Math.min(280, window.width * 0.23)
                    placeholderText: qsTr("Найти в книге")
                    selectByMouse: true
                    onTextChanged: window.backend.searchBook(text)
                    onAccepted: if (window.backend.searchModel.rowCount() > 0) window.backend.openReviewItem(window.backend.searchModel.get(0).itemId)
                    Accessible.name: qsTr("Поиск по всей книге")
                }
            }
        }
        SplitView {
            id: workspace
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            Pane {
                objectName: "audiobookChapterSidebar"
                clip: true
                visible: window.sidebarVisible
                SplitView.preferredWidth: 215
                SplitView.minimumWidth: 170
                SplitView.maximumWidth: 300
                padding: 10
                background: Rectangle { color: window.macOSStyle ? "transparent" : window.palette.window }
                contentItem: ColumnLayout {
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Label { text: bookSearch.text.length ? qsTr("Результаты поиска") : qsTr("Главы"); font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                        RowAccessoryButton {
                            iconSource: "../icons/ellipsis.svg"
                            toolTipText: qsTr("Структура глав")
                            enabled: window.backend.canEditMarkup
                            onClicked: { window.backend.flush(); markupWindow.openEditor() }
                        }
                    }
                    PersistentListView {
                        id: chaptersView
                        objectName: "audiobookChaptersView"
                        visible: bookSearch.text.length === 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: window.backend.chaptersModel
                        clip: true
                        delegate: ItemDelegate {
                            id: chapterRow
                            required property string title
                            required property bool selected
                            required property int issues
                            required property bool ready
                            width: chaptersView.viewportWidth
                            height: window.macOSStyle ? 38 : 42
                            highlighted: selected
                            background: Rectangle {
                                radius: 5
                                color: chapterRow.selected ? Qt.rgba(chapterRow.palette.highlight.r, chapterRow.palette.highlight.g, chapterRow.palette.highlight.b, window.macOSStyle ? 0.15 : 0.09) : chapterRow.hovered ? Qt.rgba(chapterRow.palette.text.r, chapterRow.palette.text.g, chapterRow.palette.text.b, 0.04) : "transparent"
                            }
                            onClicked: window.backend.selectChapter(title)
                            contentItem: RowLayout {
                                spacing: 8
                                Label { text: chapterRow.title; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { visible: chapterRow.issues > 0; text: chapterRow.issues; color: "#bd832b"; font.pixelSize: 11 }
                                Rectangle { implicitWidth: 6; implicitHeight: 6; radius: 3; color: chapterRow.ready ? "#42956a" : window.softMuted; opacity: chapterRow.ready ? 1 : 0.45 }
                            }
                            Rectangle { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; width: 3; height: 18; radius: 1; color: chapterRow.palette.highlight; visible: window.windowsStyle && chapterRow.selected }
                        }
                    }
                    PersistentListView {
                        id: searchResults
                        visible: bookSearch.text.length > 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: window.backend.searchModel
                        clip: true
                        delegate: ItemDelegate {
                            id: searchRow
                            required property string itemId
                            required property string chapter
                            required property string snippet
                            width: searchResults.viewportWidth
                            height: 92
                            onClicked: window.backend.openReviewItem(itemId)
                            contentItem: ColumnLayout {
                                Label { text: searchRow.chapter; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: searchRow.snippet; Layout.fillWidth: true; maximumLineCount: 3; wrapMode: Text.WordWrap; elide: Text.ElideRight; color: window.softMuted }
                            }
                        }
                        Label { anchors.centerIn: parent; visible: parent.count === 0; text: qsTr("Ничего не найдено"); color: window.softMuted }
                    }
                    Label { text: qsTr("%1 глав · %2 слов").arg(window.backend.chapterTitles.length).arg(window.backend.bookWords); color: window.softMuted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Label { text: window.backend.bookDuration; color: window.softMuted }
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        columns: width < readingSpeedLabel.implicitWidth + readingSpeedControl.minimumControlWidth + columnSpacing ? 1 : 2
                        columnSpacing: 8
                        rowSpacing: 4
                        Label {
                            id: readingSpeedLabel
                            text: qsTr("Слов/мин:")
                            color: window.softMuted
                            font.pixelSize: 11
                        }
                        SpinBox {
                            id: readingSpeedControl
                            objectName: "audiobookReadingSpeed"
                            readonly property real minimumControlWidth: Math.ceil(readingSpeedMetrics.advanceWidth("300")) + leftPadding + rightPadding + 8
                            from: 60
                            to: 300
                            stepSize: 10
                            value: window.backend.readingSpeed
                            editable: true
                            Layout.fillWidth: true
                            Layout.minimumWidth: minimumControlWidth
                            onValueModified: window.backend.setReadingSpeed(value)
                            FontMetrics { id: readingSpeedMetrics; font: readingSpeedControl.font }
                        }
                    }
                    AdaptiveButton { text: qsTr("Структура глав…"); flat: true; Layout.fillWidth: true; Layout.minimumWidth: 0; enabled: window.backend.canEditMarkup; onClicked: { window.backend.flush(); markupWindow.openEditor() } }
                }
            }
            Pane {
                visible: window.workflow === 1 && window.backend.chapterTitles.length > 0
                SplitView.preferredWidth: 310
                SplitView.minimumWidth: 240
                SplitView.maximumWidth: 420
                padding: 12
                AudiobookReviewPane { anchors.fill: parent; backend: window.backend; softMuted: window.softMuted }
            }
            Rectangle {
                objectName: "audiobookEditorArea"
                SplitView.fillWidth: true
                SplitView.minimumWidth: 360
                color: window.palette.base
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    WebEngineView {
                        id: editorView
                        objectName: "audiobookEditorView"
                        visible: window.backend.chapterTitles.length > 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        webChannel: editorChannel
                        backgroundColor: window.palette.base
                        settings.localContentCanAccessRemoteUrls: false
                        settings.localContentCanAccessFileUrls: false
                        onNavigationRequested: function(request) {
                            if (request.url.toString() === window.backend.editorUrl.toString()) request.accept()
                            else request.reject()
                        }
                    }
                    Item {
                        id: emptyBookState
                        objectName: "audiobookEmptyState"
                        visible: window.backend.chapterTitles.length === 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            objectName: "audiobookEmptyContent"
                            anchors.centerIn: parent
                            width: Math.min(480, Math.max(0, parent.width - 48))
                            spacing: 14
                            Label {
                                text: qsTr("Подготовьте книгу к записи")
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                            }
                            Label {
                                text: qsTr("Импортируйте текст, проверьте главы и назначьте роли.")
                                color: window.softMuted
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                            }
                            AdaptiveButton {
                                text: window.backend.importing ? qsTr("Импорт…") : qsTr("Импортировать книгу…")
                                enabled: !window.backend.importing
                                highlighted: true
                                Layout.alignment: Qt.AlignHCenter
                                onClicked: importDialog.open()
                            }
                            Label {
                                text: qsTr("PDF с текстовым слоем · DOCX · EPUB · TXT")
                                color: window.softMuted
                                font.pixelSize: 12
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                    AudiobookReviewActions { visible: window.workflow === 1 && window.backend.chapterTitles.length > 0; Layout.fillWidth: true; backend: window.backend; softMuted: window.softMuted }
                }
            }
            Pane {
                visible: window.inspectorVisible && window.workflow === 0 && window.backend.chapterTitles.length > 0
                SplitView.preferredWidth: 300
                SplitView.minimumWidth: 275
                SplitView.maximumWidth: 380
                padding: 14
                background: Rectangle { color: window.macOSStyle ? "transparent" : window.palette.window }
                PersistentScrollView {
                    id: inspectorScroll
                    anchors.fill: parent
                    contentWidth: availableWidth
                    AudiobookMarkupPane {
                        width: inspectorScroll.availableWidth
                        height: Math.max(implicitHeight, inspectorScroll.availableHeight)
                        backend: window.backend
                        editorView: editorView
                        appBridge: window.appBridge
                        ownerWindow: window
                        softMuted: window.softMuted
                        macOSStyle: window.macOSStyle
                        onDictionaryRequested: function(word) { dictionaryDialog.openDictionary(word) }
                    }
                }
            }
        }
    }
    footer: RowLayout {
        anchors.fill: parent
        implicitHeight: 32
        spacing: 10
        Label { text: qsTr("Глава %1 из %2").arg(window.backend.chapterIndex).arg(window.backend.chapterTitles.length); color: window.softMuted; visible: window.backend.chapterTitles.length > 0 }
        Label { text: window.backend.chapterWords + qsTr(" слов · ") + window.backend.chapterDuration; color: window.softMuted; visible: window.backend.chapterTitles.length > 0 }
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: window.backend.currentChapterIssues > 0 ? qsTr("%1 замечаний").arg(window.backend.currentChapterIssues) : window.backend.currentChapterReady ? qsTr("Глава проверена") : qsTr("Отметить проверенной")
            flat: true
            visible: window.backend.chapterTitles.length > 0
            enabled: !window.backend.currentChapterReady
            onClicked: {
                if (window.backend.currentChapterIssues > 0) { window.workflow = 1; window.backend.openNextReviewItem() }
                else window.backend.markChapterReviewed()
            }
        }
        CheckBox {
            text: qsTr("Автосохранение")
            checked: window.backend.autoSave
            onToggled: window.backend.setAutoSave(checked)
            Accessible.name: qsTr("Автосохранение проекта после паузы в редактировании")
        }
        Label { text: window.backend.pending ? qsTr("Применение…") : !window.appBridge.project.path ? qsTr("Сохраните проект впервые") : window.appBridge.project.dirty ? qsTr("Есть изменения") : qsTr("Сохранено"); color: window.softMuted; font.pixelSize: 11 }
    }
    Connections {
        target: window.backend
        function onEditorChanged() { window.reloadEditor() }
        function onChanged() { window.syncEditor() }
        function onEditorFocusRequested(runId, text) {
            window.pendingFocusId = runId; window.pendingFocusText = text
            window.focusPending()
        }
    }
}
