import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root
    required property var appBridge
    readonly property var projectBackend: appBridge.project
    readonly property var uiState: appBridge.uiState

    width: uiState.intValue("main.width", 1350)
    height: uiState.intValue("main.height", 850)
    minimumWidth: 680
    minimumHeight: 620
    visible: true
    title: projectBackend.name + (projectBackend.dirty ? " *" : "") + " - Dubbing Manager"
    color: workspaceBackground
    property bool closeApproved: false
    property bool uiReady: false
    property string pendingRelinkEpisode: ""
    readonly property bool compactLayout: width < 980
    property string compactSection: "workspace"

    onCompactLayoutChanged: {
        if (!compactLayout)
            compactSection = "workspace"
    }

    function persistWindowState() {
        uiState.setBoolValue("main.maximized", visibility === Window.Maximized)
        if (visibility !== Window.Maximized && visibility !== Window.FullScreen) {
            uiState.setIntValue("main.x", x)
            uiState.setIntValue("main.y", y)
            uiState.setIntValue("main.width", width)
            uiState.setIntValue("main.height", height)
        }
        if (actorPanel.width > 0)
            uiState.setIntValue("main.actorPanelWidth", actorPanel.width)
        if (toolsSidebar.width > 0)
            uiState.setIntValue("main.toolsPanelWidth", toolsSidebar.width)
    }

    Component.onCompleted: {
        var savedX = uiState.intValue("main.x", -1)
        var savedY = uiState.intValue("main.y", -1)
        if (savedX >= 0 && savedY >= 0) {
            x = savedX
            y = savedY
        }
        if (uiState.boolValue("main.maximized", false))
            showMaximized()
        Qt.callLater(function() { root.uiReady = true })
    }

    onXChanged: if (uiReady) windowStateTimer.restart()
    onYChanged: if (uiReady) windowStateTimer.restart()
    onWidthChanged: if (uiReady) windowStateTimer.restart()
    onHeightChanged: if (uiReady) windowStateTimer.restart()
    onVisibilityChanged: if (uiReady) windowStateTimer.restart()

    Timer {
        id: windowStateTimer
        interval: 350
        onTriggered: root.persistWindowState()
    }

    Timer {
        id: panelStateTimer
        interval: 350
        onTriggered: root.persistWindowState()
    }

    onClosing: function(close) {
        root.persistWindowState()
        if (root.closeApproved) {
            return
        }
        close.accepted = false
        projectBackend.requestClose()
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    readonly property bool darkTheme: (
        palette.base.r * 0.2126
        + palette.base.g * 0.7152
        + palette.base.b * 0.0722
    ) < 0.5
    readonly property bool windowsStyle: Qt.platform.os === "windows"

    function mixColor(baseColor, tintColor, amount) {
        return Qt.rgba(
            baseColor.r * (1 - amount) + tintColor.r * amount,
            baseColor.g * (1 - amount) + tintColor.g * amount,
            baseColor.b * (1 - amount) + tintColor.b * amount,
            1
        )
    }

    function routeDroppedFiles(urls) {
        var projects = []
        var subtitles = []
        var documents = []
        for (var i = 0; i < urls.length; i++) {
            var value = urls[i].toString()
            var lower = value.toLowerCase()
            if (lower.endsWith(".dub") || lower.endsWith(".dub_backup")
                    || lower.endsWith(".json")) projects.push(value)
            else if (lower.endsWith(".ass") || lower.endsWith(".srt")) subtitles.push(value)
            else if (lower.endsWith(".docx")) documents.push(value)
        }
        if (projects.length > 0) root.projectBackend.open(projects[0])
        else if (subtitles.length > 0) subtitleImportWindow.openForFiles(subtitles)
        else if (documents.length > 0) docxImportWindow.openForFile(documents[0])
        else {
            errorDialog.message = "Перетащите проект, ASS, SRT или DOCX"
            errorDialog.open()
        }
    }

    property color softBorder: root.windowsStyle && !root.darkTheme
        ? "#d9dde3" : Qt.rgba(
            palette.text.r, palette.text.g, palette.text.b,
            root.darkTheme ? 0.09 : 0.10
        )
    property color hairlineBorder: Qt.rgba(
        palette.text.r,
        palette.text.g,
        palette.text.b,
        root.darkTheme ? 0.045 : 0.055
    )
    property color workspaceBackground: root.windowsStyle && !root.darkTheme
        ? "#f4f6f8" : root.mixColor(
            palette.window, palette.highlight, root.darkTheme ? 0.025 : 0.018
        )
    property color panelSurface: root.windowsStyle && !root.darkTheme
        ? "#ffffff" : root.mixColor(
            palette.base, palette.highlight, root.darkTheme ? 0.035 : 0.012
        )
    property color softHeader: root.windowsStyle && !root.darkTheme
        ? "#f8f9fb" : root.mixColor(
            palette.base, palette.highlight, root.darkTheme ? 0.095 : 0.045
        )
    property color softRow: root.windowsStyle && !root.darkTheme
        ? "#ffffff" : palette.base
    property color softAltRow: root.windowsStyle && !root.darkTheme
        ? "#fbfcfd" : root.mixColor(
            palette.base, palette.text, root.darkTheme ? 0.028 : 0.018
        )
    property color softHover: root.windowsStyle && !root.darkTheme
        ? "#eef5fc" : root.mixColor(
            palette.base, palette.highlight, root.darkTheme ? 0.14 : 0.10
        )
    property color softMuted: Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.58)

    FileDialog {
        id: openDialog
        title: qsTr("Открыть проект")
        currentFolder: root.uiState.folderUrl("projects")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("projects")
        nameFilters: ["Dubbing Manager Projects (*.dub *.dub_backup)", "Project backups (*.dub_backup)", "Legacy JSON Project (*.json)", "All files (*)"]
        onAccepted: {
            root.uiState.rememberFile("projects", selectedFile.toString())
            root.projectBackend.open(selectedFile.toString())
        }
    }

    FileDialog {
        id: saveAsDialog
        title: qsTr("Сохранить проект как")
        fileMode: FileDialog.SaveFile
        currentFolder: root.uiState.folderUrl("projects")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("projects")
        nameFilters: ["Dubbing Manager Project (*.dub)", "All files (*)"]
        defaultSuffix: "dub"
        onAccepted: {
            root.uiState.rememberFile("projects", selectedFile.toString())
            root.projectBackend.saveAs(selectedFile.toString())
        }
        onRejected: root.projectBackend.cancelPendingChanges()
    }

    FileDialog {
        id: relinkSourceDialog
        title: qsTr("Перепривязать исходный файл серии")
        currentFolder: root.uiState.folderUrl("sourceFiles")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("sourceFiles")
        nameFilters: ["Тексты серий (*.ass *.srt *.docx)", "Все файлы (*)"]
        onAccepted: {
            root.uiState.rememberFile("sourceFiles", selectedFile.toString())
            root.appBridge.projectFiles.relink(
                root.pendingRelinkEpisode,
                "source",
                selectedFile.toString()
            )
        }
    }

    FileDialog {
        id: importSubtitleDialog
        title: qsTr("Импорт субтитров")
        fileMode: FileDialog.OpenFiles
        currentFolder: root.uiState.folderUrl("sourceFiles")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("sourceFiles")
        nameFilters: ["Subtitle files (*.ass *.srt)", "ASS subtitles (*.ass)", "SRT subtitles (*.srt)", "All files (*)"]
        onAccepted: {
            if (selectedFiles.length > 0)
                root.uiState.rememberFile("sourceFiles", selectedFiles[0].toString())
            subtitleImportWindow.openForFiles(selectedFiles)
        }
    }

    SubtitleImportDialog {
        id: subtitleImportWindow
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softMuted: root.softMuted
    }

    FileDialog {
        id: importDocxDialog
        title: qsTr("Выберите DOCX")
        currentFolder: root.uiState.folderUrl("documents")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("documents")
        nameFilters: ["Word documents (*.docx)"]
        onAccepted: {
            root.uiState.rememberFile("documents", selectedFile.toString())
            docxImportWindow.openForFile(selectedFile.toString())
        }
    }

    FileDialog {
        id: exportGlobalActorsDialog
        title: qsTr("Экспорт глобальной базы актёров")
        fileMode: FileDialog.SaveFile
        currentFolder: root.uiState.folderUrl("actorData")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("actorData")
        nameFilters: ["JSON (*.json)"]
        defaultSuffix: "json"
        onAccepted: {
            root.uiState.rememberFile("actorData", selectedFile.toString())
            root.appBridge.actorLibrary.exportGlobalActorBase(selectedFile.toString())
        }
    }

    FileDialog {
        id: importGlobalActorsDialog
        title: qsTr("Импорт глобальной базы актёров")
        currentFolder: root.uiState.folderUrl("actorData")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("actorData")
        nameFilters: ["JSON (*.json)"]
        onAccepted: {
            root.uiState.rememberFile("actorData", selectedFile.toString())
            root.appBridge.actorLibrary.importGlobalActorBase(selectedFile.toString())
        }
    }

    FileDialog {
        id: exportAssignmentsDialog
        title: qsTr("Экспорт распределения актёров")
        fileMode: FileDialog.SaveFile
        currentFolder: root.uiState.folderUrl("actorData")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("actorData")
        nameFilters: ["JSON (*.json)"]
        defaultSuffix: "json"
        onAccepted: {
            root.uiState.rememberFile("actorData", selectedFile.toString())
            root.appBridge.actorLibrary.exportProjectAssignments(selectedFile.toString())
        }
    }

    FileDialog {
        id: importAssignmentsDialog
        title: qsTr("Импорт распределения актёров")
        currentFolder: root.uiState.folderUrl("actorData")
        onVisibleChanged: if (visible) currentFolder = root.uiState.folderUrl("actorData")
        nameFilters: ["JSON (*.json)"]
        onAccepted: {
            root.uiState.rememberFile("actorData", selectedFile.toString())
            root.appBridge.actorLibrary.importProjectAssignments(selectedFile.toString())
        }
    }

    NativeDialogWindow {
        id: errorDialog
        ownerWindow: root
        modal: true
        title: qsTr("Dubbing Manager")
        standardButtons: Dialog.Ok
        width: 420
        height: 180

        property string message: ""

        content: Label {
            anchors.fill: parent
            text: errorDialog.message
            wrapMode: Text.WordWrap
            width: 360
        }
    }

    NativeDialogWindow {
        id: saveChangesDialog
        ownerWindow: root
        modal: true
        title: qsTr("Несохранённые изменения")
        standardButtons: Dialog.NoButton
        width: 430
        height: 210
        property string message: ""

        content: Label {
            anchors.fill: parent
            text: saveChangesDialog.message
            wrapMode: Text.WordWrap
            width: 380
        }

        footer: Item {
            implicitHeight: root.windowsStyle ? 32 : nativeFooterLoader.item
                ? nativeFooterLoader.item.implicitHeight : 0

            Loader {
                id: nativeFooterLoader
                anchors.fill: parent
                sourceComponent: root.windowsStyle
                    ? saveChangesWindowsFooter : saveChangesNativeFooter
            }
        }

        Component {
            id: saveChangesNativeFooter

            DialogButtonBox {
                anchors.fill: parent
                Button {
                    text: qsTr("Сохранить")
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("save")
                    }
                }
                Button {
                    text: qsTr("Не сохранять")
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("discard")
                    }
                }
                Button {
                    text: qsTr("Отмена")
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("cancel")
                    }
                }
            }
        }

        Component {
            id: saveChangesWindowsFooter

            RowLayout {
                anchors.fill: parent
                implicitHeight: 32
                spacing: 8

                Item { Layout.fillWidth: true }
                FluentButton {
                    text: qsTr("Отмена")
                    Layout.preferredWidth: 100
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("cancel")
                    }
                }
                FluentButton {
                    text: qsTr("Не сохранять")
                    Layout.preferredWidth: 128
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("discard")
                    }
                }
                FluentButton {
                    text: qsTr("Сохранить")
                    primary: true
                    Layout.preferredWidth: 110
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("save")
                    }
                }
            }
        }
    }

    BackupBrowserDialog {
        id: backupBrowserDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softHover: root.softHover
        softMuted: root.softMuted
    }

    GlobalSearchDialog {
        id: globalSearchDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softHover: root.softHover
        softMuted: root.softMuted
    }

    SummaryDialog {
        id: summaryDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    MontagePreviewDialog {
        id: montagePreviewDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    ReaperExportDialog {
        id: reaperExportDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    AboutDialog {
        id: aboutDialog
        ownerWindow: root
        appBridge: root.appBridge
        softMuted: root.softMuted
    }

    VideoPreviewDialog {
        id: videoPreviewDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softHover: root.softHover
        softMuted: root.softMuted
    }

    ProjectFilesDialog {
        id: projectFilesDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softHover: root.softHover
        softMuted: root.softMuted
        onBackupsRequested: backupBrowserDialog.openBrowser()
    }

    DocxImportDialog {
        id: docxImportWindow
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    AudiobookWindow {
        id: audiobookWindow
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    QuickConverterPreviewDialog {
        id: quickConverterPreviewDialog
        ownerWindow: root
        appBridge: root.appBridge
    }

    QuickConverterResultsDialog {
        id: quickConverterResultsDialog
        ownerWindow: root
        appBridge: root.appBridge
        softHeader: root.softHeader
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    Connections {
        target: root.appBridge.converter
        function onPreviewRequested() {
            quickConverterPreviewDialog.openPreview()
        }
        function onFinished() {
            quickConverterResultsDialog.open()
        }
    }

    RolesDialog {
        id: rolesDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softHover: root.softHover
        softMuted: root.softMuted
    }

    ActorRolesDialog {
        id: actorRolesDialog
        ownerWindow: root
        appBridge: root.appBridge
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    ActorTransferDialog {
        id: actorTransferDialog
        ownerWindow: root
        appBridge: root.appBridge
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
    }

    ProjectSettingsDialog {
        id: projectSettingsDialog
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softMuted: root.softMuted
        onProjectFilesRequested: function(view) {
            projectFilesDialog.openFor(view)
        }
        onRolesRequested: rolesDialog.openForProject()
        onAssignmentExportRequested: exportAssignmentsDialog.open()
        onAssignmentImportRequested: importAssignmentsDialog.open()
    }

    GlobalSettingsDialog {
        id: globalSettingsDialog
        ownerWindow: root
        appBridge: root.appBridge
        softMuted: root.softMuted
        onActorBaseExportRequested: exportGlobalActorsDialog.open()
        onActorBaseImportRequested: importGlobalActorsDialog.open()
    }

    TeleprompterWindow {
        id: teleprompterWindow
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softMuted: root.softMuted
    }

    Shortcut { sequences: [StandardKey.Undo]; onActivated: root.projectBackend.undo() }
    Shortcut { sequences: [StandardKey.Redo]; onActivated: root.projectBackend.redo() }

    Connections {
        target: root.appBridge
        function onErrorOccurred(message) {
            errorDialog.message = message
            errorDialog.open()
        }
    }

    Connections {
        target: root.projectBackend
        function onSaveChangesRequested(message) {
            saveChangesDialog.message = message
            saveChangesDialog.open()
        }
        function onSavePathRequested() {
            saveAsDialog.open()
        }
        function onCloseApproved() {
            root.closeApproved = true
            Qt.callLater(root.close)
        }
    }

    menuBar: MenuBar {
        visible: !root.windowsStyle
        height: visible ? implicitHeight : 0

        Menu {
            title: qsTr("Файл")
            Action {
                text: qsTr("Новый")
                shortcut: StandardKey.New
                onTriggered: root.projectBackend.create()
            }
            Action {
                text: qsTr("Открыть...")
                shortcut: StandardKey.Open
                onTriggered: openDialog.open()
            }
            Action {
                text: qsTr("Сохранить")
                shortcut: StandardKey.Save
                enabled: root.projectBackend.path.length > 0
                onTriggered: root.projectBackend.save()
            }
            Action {
                text: qsTr("Сохранить как...")
                shortcut: StandardKey.SaveAs
                onTriggered: saveAsDialog.open()
            }
            Action {
                text: qsTr("Резервные копии...")
                enabled: root.projectBackend.path.length > 0
                onTriggered: backupBrowserDialog.openBrowser()
            }
            MenuSeparator {}
            Action { text: qsTr("Файлы проекта..."); onTriggered: projectFilesDialog.openFor("files") }
            Action { text: qsTr("Проверка проекта..."); onTriggered: projectFilesDialog.openFor("health") }
            Action { text: qsTr("Настройки проекта..."); onTriggered: projectSettingsDialog.openFor(0) }
            MenuSeparator {}
            Action { text: qsTr("Настройки..."); onTriggered: globalSettingsDialog.openSettings() }
        }

        Menu {
            title: qsTr("Правка")
            Action {
                text: qsTr("Отменить")
                shortcut: StandardKey.Undo
                enabled: root.projectBackend.canUndo
                onTriggered: root.projectBackend.undo()
            }
            Action {
                text: qsTr("Повторить")
                shortcut: StandardKey.Redo
                enabled: root.projectBackend.canRedo
                onTriggered: root.projectBackend.redo()
            }
        }

        Menu {
            title: qsTr("Вид")
            Action { text: qsTr("Обновить"); shortcut: StandardKey.Refresh; onTriggered: root.projectBackend.refresh() }
        }

        Menu {
            title: qsTr("Справка")
            Action { text: qsTr("О программе..."); onTriggered: aboutDialog.open() }
        }
    }

    header: Column {
        width: root.width

        ToolBar {
            width: parent.width
            height: 32
            visible: root.windowsStyle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 6
                anchors.rightMargin: 6
                spacing: 2

                    WinUiMenuBarButton {
                        objectName: "windowsFileMenuButton"
                        text: qsTr("Файл")
                        entries: [
                            { text: qsTr("Новый") },
                            { text: qsTr("Открыть...") },
                            { text: qsTr("Сохранить"), enabled: root.projectBackend.path.length > 0 },
                            { text: qsTr("Сохранить как...") },
                            { text: qsTr("Резервные копии..."), enabled: root.projectBackend.path.length > 0 },
                            { separator: true },
                            { text: qsTr("Файлы проекта...") },
                            { text: qsTr("Проверка проекта...") },
                            { text: qsTr("Настройки проекта...") },
                            { separator: true },
                            { text: qsTr("Настройки...") }
                        ]
                        onItemTriggered: function(index) {
                            if (index === 0) root.projectBackend.create()
                            else if (index === 1) openDialog.open()
                            else if (index === 2) root.projectBackend.save()
                            else if (index === 3) saveAsDialog.open()
                            else if (index === 4) backupBrowserDialog.openBrowser()
                            else if (index === 6) projectFilesDialog.openFor("files")
                            else if (index === 7) projectFilesDialog.openFor("health")
                            else if (index === 8) projectSettingsDialog.openFor(0)
                            else if (index === 10) globalSettingsDialog.openSettings()
                        }
                    }

                WinUiMenuBarButton {
                    text: qsTr("Правка")
                    entries: [
                        { text: qsTr("Отменить"), enabled: root.projectBackend.canUndo },
                        { text: qsTr("Повторить"), enabled: root.projectBackend.canRedo }
                    ]
                    onItemTriggered: function(index) {
                        if (index === 0) root.projectBackend.undo()
                        else if (index === 1) root.projectBackend.redo()
                    }
                }

                WinUiMenuBarButton {
                    text: qsTr("Вид")
                    entries: [{ text: qsTr("Обновить") }]
                    onItemTriggered: function(index) { root.projectBackend.refresh() }
                }

                WinUiMenuBarButton {
                    text: qsTr("Справка")
                    entries: [{ text: qsTr("О программе...") }]
                    onItemTriggered: function(index) { aboutDialog.open() }
                }

                Item { Layout.fillWidth: true }
            }
        }

        ProjectToolbar {
            width: parent.width
            appBridge: root.appBridge
            softMuted: root.softMuted
            rootWidth: root.width
            onOpenProjectRequested: openDialog.open()
            onSaveProjectAsRequested: saveAsDialog.open()
            onGlobalSettingsRequested: globalSettingsDialog.openSettings()
            onProjectSettingsRequested: projectSettingsDialog.openFor(0)
            onHealthRequested: projectFilesDialog.openFor("health")
            onAboutRequested: aboutDialog.open()
        }
    }

    footer: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 8

            Label {
                text: root.appBridge.statusText
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 6

        TabBar {
            id: compactSections
            objectName: "compactSections"
            visible: root.compactLayout
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            currentIndex: root.compactSection === "actors"
                ? 0 : root.compactSection === "tools" ? 2 : 1

            onCurrentIndexChanged: {
                root.compactSection = currentIndex === 0
                    ? "actors" : currentIndex === 2 ? "tools" : "workspace"
            }

            TabButton { text: qsTr("Актёры") }
            TabButton { text: qsTr("Реплики") }
            TabButton { text: qsTr("Сценарии") }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            ActorPanel {
                id: actorPanel
                appBridge: root.appBridge
                visible: !root.compactLayout || root.compactSection === "actors"
                SplitView.fillWidth: root.compactLayout
                SplitView.preferredWidth: root.uiState.intValue("main.actorPanelWidth", 330)
                onWidthChanged: if (root.uiReady) panelStateTimer.restart()
                softBorder: root.softBorder
                softHeader: root.softHeader
                softRow: root.softRow
                softAltRow: root.softAltRow
                softHover: root.softHover
                softMuted: root.softMuted
                panelSurface: root.panelSurface
                onProjectSummaryRequested: summaryDialog.openFor("")
                onActorRolesRequested: function(actorId) {
                    actorRolesDialog.openFor(actorId)
                }
                onBulkTransferRequested: actorTransferDialog.openForProject()
            }

            SplitView {
                visible: !root.compactLayout || root.compactSection !== "actors"
                SplitView.fillWidth: true
                orientation: Qt.Horizontal

                Item {
                    visible: !root.compactLayout || root.compactSection === "workspace"
                    SplitView.fillWidth: true

                    Rectangle {
                        anchors.fill: parent
                        color: root.panelSurface
                        border.color: root.softBorder
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 6

                        EpisodeControls {
                            appBridge: root.appBridge
                            onImportRequested: importSubtitleDialog.open()
                            onImportDocxRequested: importDocxDialog.open()
                            onGlobalSearchRequested: globalSearchDialog.open()
                        }

                        CharacterTable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            framed: false
                            appBridge: root.appBridge
                            softBorder: root.softBorder
                            softHeader: root.softHeader
                            softRow: root.softRow
                            softAltRow: root.softAltRow
                            softHover: root.softHover
                            softMuted: root.softMuted
                            onRelinkSourceRequested: function(episode) {
                                root.pendingRelinkEpisode = episode
                                relinkSourceDialog.open()
                            }
                            onVideoPreviewRequested: function(character) {
                                videoPreviewDialog.openFor(character)
                            }
                            onFilesDropped: function(urls) {
                                root.routeDroppedFiles(urls)
                            }
                        }
                    }
                }

                ToolsSidebar {
                    id: toolsSidebar
                    appBridge: root.appBridge
                    visible: !root.compactLayout || root.compactSection === "tools"
                    SplitView.fillWidth: root.compactLayout
                    SplitView.preferredWidth: root.uiState.intValue("main.toolsPanelWidth", 235)
                    onWidthChanged: if (root.uiReady) panelStateTimer.restart()
                    softBorder: root.softBorder
                    softHeader: root.softHeader
                    softMuted: root.softMuted
                    panelSurface: root.panelSurface
                    onMontagePreviewRequested: montagePreviewDialog.openFor(root.projectBackend.currentEpisode)
                    onReaperExportRequested: reaperExportDialog.openForCurrentEpisode()
                    onEpisodeSummaryRequested: summaryDialog.openFor(root.projectBackend.currentEpisode)
                    onTeleprompterRequested: teleprompterWindow.openFor(root.projectBackend.currentEpisode)
                    onAudiobookRequested: audiobookWindow.openWorkspace()
                    onRolesRequested: rolesDialog.openForProject()
                    onConverterResultsRequested: quickConverterResultsDialog.open()
                }
            }
        }
    }
}
