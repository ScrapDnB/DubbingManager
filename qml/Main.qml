pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root
    required property var appBridge
    property var macOSIntegration: null
    readonly property var projectBackend: appBridge.project
    readonly property var uiState: appBridge.uiState

    width: uiState.intValue("main.width", 1350)
    height: uiState.intValue("main.height", 850)
    // AppKit expands the native frame when the unified toolbar settles. Keep
    // that chrome delta out of the persisted QML height, otherwise it is
    // added again every time the application starts.
    readonly property int restoredWindowHeight: uiState.intValue("main.height", 850)
    property int macOSChromeHeightDelta: 0
    minimumWidth: 680
    minimumHeight: 620
    visible: false
    title: projectBackend.name + (projectBackend.dirty ? " *" : "") + " - Dubbing Manager"
    color: macOSStyle ? "transparent" : workspaceBackground
    property bool closeApproved: false
    property bool uiReady: false
    // AppKit adds native toolbar chrome to the main window on macOS. Wait for
    // that step before the first show, otherwise the adjusted frame height is
    // persisted and grows again on the next launch.
    property bool startupChromeReady: !macOSStyle
    property bool startupShown: false
    property string pendingRelinkEpisode: ""
    readonly property bool compactLayout: width < 980
    property string compactSection: "workspace"
    property string actorColorDisplayMode:
        uiState.boolValue("actorColorCellFill", false) ? "cell" : "marker"
    property int actorColorMuteLevel: uiState.intValue(
        "actorColorCellMuteLevel",
        uiState.boolValue("actorColorCellMuted", true) ? 2 : 0
    )
    property bool actorColorCellFillFullHeight: uiState.boolValue(
        "actorColorCellFillFullHeight", false
    )
    property int actorMarkerShape: uiState.intValue("actorMarkerShape", 0)
    property int actorMarkerSize: uiState.intValue("actorMarkerSize", 0)
    property int uiScalePercent: uiState.intValue("main.uiScalePercent", 75)
    property string characterColumnsOrderJson: uiState.stringValue(
        "main.characterColumnsOrder",
        "[\"character\",\"lines\",\"rings\",\"words\",\"scope\",\"actor\",\"preview\"]"
    )
    property string characterColumnsHiddenJson: uiState.stringValue(
        "main.characterColumnsHidden", "[]"
    )
    property string characterColumnWidthsJson: uiState.stringValue(
        "main.characterColumnWidths", "{}"
    )
    property bool characterCompactRows: uiState.boolValue(
        "main.characterCompactRows", false
    )
    property bool episodeTimelineVisible: uiState.boolValue(
        "main.episodeTimelineVisible", true
    )
    property bool episodeTimelineActorColors: uiState.boolValue(
        "main.episodeTimelineActorColors", true
    )
    property int episodeTimelineColorMuteLevel: uiState.intValue(
        "main.episodeTimelineColorMuteLevel", 2
    )
    property string episodeTimelinePlacement: uiState.stringValue(
        "main.episodeTimelinePlacement", "table"
    )
    property int episodeTimelineHeight: uiState.intValue(
        "main.episodeTimelineHeight", 180
    )
    property string episodeTimelineSortMode: uiState.stringValue(
        "main.episodeTimelineSortMode", "appearance"
    )
    property bool quickConverterVisible: uiState.boolValue(
        "main.quickConverterVisible", true
    )

    function setQuickConverterVisible(visible, syncNative) {
        quickConverterVisible = visible
        uiState.setBoolValue("main.quickConverterVisible", visible)
        if (syncNative && macOSStyle)
            macOSIntegration.setQuickConverterVisible(visible)
    }

    function jsonArray(value, fallback) {
        try {
            var result = JSON.parse(value)
            return Array.isArray(result) ? result : fallback
        } catch (error) {
            return fallback
        }
    }

    function jsonObject(value, fallback) {
        try {
            var result = JSON.parse(value)
            return result && typeof result === "object" && !Array.isArray(result)
                ? result : fallback
        } catch (error) {
            return fallback
        }
    }

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
            uiState.setIntValue(
                "main.height",
                macOSStyle && !uiReady
                    ? restoredWindowHeight
                    : Math.round(Math.max(
                        minimumHeight, height - macOSChromeHeightDelta
                    ))
            )
        }
        if (actorPanel.width > 0)
            uiState.setIntValue("main.actorPanelWidth", actorPanel.width)
        if (toolsSidebar.width > 0)
            uiState.setIntValue("main.toolsPanelWidth", toolsSidebar.width)
    }

    function showInitialWindow() {
        if (startupShown)
            return
        startupShown = true
        if (uiState.boolValue("main.maximized", false)) {
            showMaximized()
        } else {
            show()
        }
        if (root.windowsStyle)
            windowsMenuResetTimer.restart()
        startupGeometryTimer.restart()
    }

    Component.onCompleted: {
        appBridge.casting.setTimelineSortMode(episodeTimelineSortMode)
        var savedX = uiState.intValue("main.x", -1)
        var savedY = uiState.intValue("main.y", -1)
        if (savedX >= 0 && savedY >= 0) {
            x = savedX
            y = savedY
        }
        if (startupChromeReady)
            showInitialWindow()
    }

    onStartupChromeReadyChanged: if (startupChromeReady) showInitialWindow()

    function dismissStartupMenus() {
        fileMenu.close()
        editMenu.close()
        viewMenu.close()
        toolsMenu.close()
        helpMenu.close()
        mainMenuBar.currentIndex = -1
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
        id: startupGeometryTimer
        interval: root.macOSStyle ? 700 : 0
        repeat: false
        onTriggered: {
            if (root.macOSStyle) {
                root.macOSChromeHeightDelta = Math.max(
                    0,
                    Math.round(root.height - root.restoredWindowHeight)
                )
            }
            root.uiReady = true
        }
    }

    Timer {
        id: windowsMenuResetTimer
        interval: 120
        repeat: false
        onTriggered: {
            root.dismissStartupMenus()
            // Qt's Windows MenuBar may choose an initial item while handling
            // the first expose event. Clear it once more on the next turn.
            Qt.callLater(root.dismissStartupMenus)
        }
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
    readonly property bool macOSStyle: Qt.platform.os === "osx"

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

    property color softBorder: Qt.rgba(
        palette.text.r, palette.text.g, palette.text.b,
        root.darkTheme ? 0.09 : 0.10
    )
    property color hairlineBorder: Qt.rgba(
        palette.text.r,
        palette.text.g,
        palette.text.b,
        root.darkTheme ? 0.045 : 0.055
    )
    property color workspaceBackground: root.mixColor(
        palette.window,
        palette.highlight,
        root.macOSStyle ? 0 : (root.darkTheme ? 0.025 : 0.018)
    )
    property color panelSurface: root.mixColor(
        palette.base,
        palette.highlight,
        root.macOSStyle ? 0 : (root.darkTheme ? 0.035 : 0.012)
    )
    property color softHeader: root.mixColor(
        palette.base,
        palette.highlight,
        root.macOSStyle
            ? (root.darkTheme ? 0.035 : 0.018)
            : (root.darkTheme ? 0.095 : 0.045)
    )
    property color softRow: palette.base
    property color softAltRow: root.mixColor(
        palette.base, palette.text, root.darkTheme ? 0.028 : 0.018
    )
    property color softHover: root.mixColor(
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
                ? (nativeFooterLoader.item as Item).implicitHeight : 0

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
                AdaptiveButton {
                    text: qsTr("Сохранить")
                    highlighted: root.macOSStyle
                    DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("save")
                    }
                }
                AdaptiveButton {
                    text: qsTr("Не сохранять")
                    DialogButtonBox.buttonRole: DialogButtonBox.DestructiveRole
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("discard")
                    }
                }
                AdaptiveButton {
                    text: qsTr("Отмена")
                    DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
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
                AdaptiveButton {
                    text: qsTr("Отмена")
                    Layout.preferredWidth: 100
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("cancel")
                    }
                }
                AdaptiveButton {
                    text: qsTr("Не сохранять")
                    Layout.preferredWidth: 128
                    onClicked: {
                        saveChangesDialog.close()
                        root.projectBackend.resolvePendingChanges("discard")
                    }
                }
                AdaptiveButton {
                    text: qsTr("Сохранить")
                    highlighted: true
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
        actorMarkerShape: root.actorMarkerShape
        actorMarkerSize: root.actorMarkerSize
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
        actorMarkerShape: root.actorMarkerShape
        actorMarkerSize: root.actorMarkerSize
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
        softBorder: root.softBorder
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

    GlobalActorTransferDialog {
        id: globalActorTransferDialog
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
        actorColorDisplayMode: root.actorColorDisplayMode
        actorColorMuteLevel: root.actorColorMuteLevel
        actorColorCellFillFullHeight: root.actorColorCellFillFullHeight
        actorMarkerShape: root.actorMarkerShape
        actorMarkerSize: root.actorMarkerSize
        uiScalePercent: root.uiScalePercent
        characterColumnsOrder: root.characterColumnsOrderJson
        characterColumnsHidden: root.characterColumnsHiddenJson
        characterColumnWidths: root.characterColumnWidthsJson
        characterCompactRows: root.characterCompactRows
        episodeTimelineVisible: root.episodeTimelineVisible
        episodeTimelineActorColors: root.episodeTimelineActorColors
        episodeTimelineColorMuteLevel: root.episodeTimelineColorMuteLevel
        episodeTimelinePlacement: root.episodeTimelinePlacement
        episodeTimelineHeight: root.episodeTimelineHeight
        episodeTimelineSortMode: root.episodeTimelineSortMode
        onActorBaseExportRequested: exportGlobalActorsDialog.open()
        onActorBaseImportRequested: importGlobalActorsDialog.open()
        onActorColorDisplayModeAccepted: function(
            mode, muteLevel, fullHeight, markerShape, markerSize
        ) {
            root.actorColorDisplayMode = mode
            root.actorColorMuteLevel = muteLevel
            root.actorColorCellFillFullHeight = fullHeight
            root.actorMarkerShape = markerShape
            root.actorMarkerSize = markerSize
        }
        onCharacterTableConfigurationAccepted: function(
            order, hidden, widths, compact, timelineVisible,
            timelineActorColors, timelineColorMuteLevel,
            timelinePlacement, timelineHeight, timelineSortMode
        ) {
            root.characterColumnsOrderJson = order
            root.characterColumnsHiddenJson = hidden
            root.characterColumnWidthsJson = widths
            root.characterCompactRows = compact
            root.episodeTimelineVisible = timelineVisible
            root.episodeTimelineActorColors = timelineActorColors
            root.episodeTimelineColorMuteLevel = timelineColorMuteLevel
            root.episodeTimelinePlacement = timelinePlacement
            root.episodeTimelineHeight = timelineHeight
            root.episodeTimelineSortMode = timelineSortMode
            root.appBridge.casting.setTimelineSortMode(timelineSortMode)
        }
    }

    TeleprompterWindow {
        id: teleprompterWindow
        ownerWindow: root
        appBridge: root.appBridge
        softBorder: root.softBorder
        softHeader: root.softHeader
        softRow: root.softRow
        softAltRow: root.softAltRow
        softMuted: root.softMuted
        actorMarkerShape: root.actorMarkerShape
        actorMarkerSize: root.actorMarkerSize
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

    Connections {
        target: root.macOSIntegration
        ignoreUnknownSignals: true
        function onNativeToolbarActiveChanged() {
            if (root.macOSIntegration.nativeToolbarActive)
                root.macOSIntegration.setQuickConverterVisible(
                    root.quickConverterVisible
                )
        }
        function onOpenProjectRequested() { openDialog.open() }
        function onSaveProjectAsRequested() { saveAsDialog.open() }
        function onGlobalSettingsRequested() { globalSettingsDialog.openSettings() }
        function onProjectSettingsRequested() { projectSettingsDialog.openFor(0) }
        function onHealthRequested() { projectFilesDialog.openFor("files") }
        function onAboutRequested() { aboutDialog.open() }
        function onTeleprompterRequested() {
            teleprompterWindow.openFor(root.projectBackend.currentEpisode)
        }
        function onMontagePreviewRequested() {
            montagePreviewDialog.openFor(root.projectBackend.currentEpisode)
        }
        function onReaperExportRequested() {
            reaperExportDialog.openForCurrentEpisode()
        }
        function onAudiobookRequested() { audiobookWindow.openWorkspace() }
        function onEpisodeSummaryRequested() {
            summaryDialog.openFor(root.projectBackend.currentEpisode)
        }
        function onRolesRequested() { rolesDialog.openForProject() }
        function onQuickConverterVisibilityRequested(visible) {
            root.setQuickConverterVisible(visible, false)
        }
    }

    menuBar: MenuBar {
        id: mainMenuBar
        height: root.windowsStyle ? 40 : implicitHeight
        topPadding: root.windowsStyle ? 4 : 0
        bottomPadding: root.windowsStyle ? 4 : 0
        leftPadding: root.windowsStyle ? 8 : 0
        rightPadding: 0

        Menu {
            id: fileMenu
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
            MenuItem {
                visible: !root.macOSStyle
                action: Action {
                    text: root.macOSStyle
                        ? qsTr("Параметры...") : qsTr("Настройки...")
                    shortcut: StandardKey.Preferences
                    onTriggered: globalSettingsDialog.openSettings()
                }
            }
        }

        Menu {
            id: editMenu
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
            id: viewMenu
            title: qsTr("Вид")
            Action { text: qsTr("Обновить"); shortcut: StandardKey.Refresh; onTriggered: root.projectBackend.refresh() }
        }

        Menu {
            id: toolsMenu
            title: qsTr("Инструменты")

            Action {
                text: qsTr("Телесуфлёр")
                enabled: root.projectBackend.currentEpisode.length > 0
                onTriggered: teleprompterWindow.openFor(
                    root.projectBackend.currentEpisode
                )
            }
            Action {
                text: qsTr("Монтажный лист")
                enabled: root.projectBackend.currentEpisode.length > 0
                onTriggered: montagePreviewDialog.openFor(
                    root.projectBackend.currentEpisode
                )
            }
            Action {
                text: qsTr("Экспорт в Reaper")
                enabled: root.projectBackend.currentEpisode.length > 0
                onTriggered: reaperExportDialog.openForCurrentEpisode()
            }
            Action {
                text: qsTr("Аудиокнига")
                enabled: root.appBridge !== null
                onTriggered: audiobookWindow.openWorkspace()
            }
            Action {
                text: qsTr("Отчёт серии")
                enabled: root.projectBackend.currentEpisode.length > 0
                onTriggered: summaryDialog.openFor(
                    root.projectBackend.currentEpisode
                )
            }
            Action {
                text: qsTr("Назначить роли")
                enabled: root.appBridge && root.appBridge.casting
                onTriggered: rolesDialog.openForProject()
            }

            MenuSeparator { }

            MenuItem {
                text: qsTr("Быстрый конвертер")
                checkable: true
                checked: root.quickConverterVisible
                onTriggered: root.setQuickConverterVisible(checked, true)
            }
        }

        Menu {
            id: helpMenu
            title: qsTr("Справка")
            visible: !root.macOSStyle
            Action { text: qsTr("О программе..."); onTriggered: aboutDialog.open() }
        }
    }

    header: Column {
        width: root.width

        ProjectToolbar {
            width: parent.width
            visible: !(root.macOSIntegration
                && root.macOSIntegration.nativeToolbarActive)
            height: visible ? implicitHeight : 0
            appBridge: root.appBridge
            softMuted: root.softMuted
            rootWidth: root.width
            quickConverterVisible: root.quickConverterVisible
            onOpenProjectRequested: openDialog.open()
            onSaveProjectAsRequested: saveAsDialog.open()
            onGlobalSettingsRequested: globalSettingsDialog.openSettings()
            onProjectSettingsRequested: projectSettingsDialog.openFor(0)
            onHealthRequested: projectFilesDialog.openFor("files")
            onAboutRequested: aboutDialog.open()
            onTeleprompterRequested: teleprompterWindow.openFor(
                root.projectBackend.currentEpisode
            )
            onMontagePreviewRequested: montagePreviewDialog.openFor(
                root.projectBackend.currentEpisode
            )
            onReaperExportRequested: reaperExportDialog.openForCurrentEpisode()
            onAudiobookRequested: audiobookWindow.openWorkspace()
            onEpisodeSummaryRequested: summaryDialog.openFor(
                root.projectBackend.currentEpisode
            )
            onRolesRequested: rolesDialog.openForProject()
            onQuickConverterVisibilityRequested: function(visible) {
                root.setQuickConverterVisible(visible, true)
            }
        }
    }

    footer: ToolBar {
        visible: !root.macOSStyle
        height: visible ? implicitHeight : 0
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
        anchors.margins: root.macOSStyle ? 0 : 6
        spacing: root.macOSStyle ? 0 : 6

        NavigationTabBar {
            id: compactSections
            objectName: "compactSections"
            visible: root.compactLayout
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            model: [qsTr("Актёры"), qsTr("Реплики")]
            tabWidth: width / Math.max(1, model.length)
            currentIndex: root.compactSection === "actors" ? 0 : 1

            onActivated: function(index) {
                root.compactSection = index === 0 ? "actors" : "workspace"
            }
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
                actorMarkerShape: root.actorMarkerShape
                actorMarkerSize: root.actorMarkerSize
                compactRows: root.characterCompactRows
                onProjectSummaryRequested: summaryDialog.openFor("")
                onActorRolesRequested: function(actorId) {
                    actorRolesDialog.openFor(actorId)
                }
                onBulkTransferRequested: actorTransferDialog.openForProject()
                onGlobalBulkTransferRequested: globalActorTransferDialog.openForProject()
            }

            SplitView {
                visible: !root.compactLayout || root.compactSection !== "actors"
                SplitView.fillWidth: true
                orientation: Qt.Horizontal

                Item {
                    visible: !root.compactLayout || root.compactSection === "workspace"
                    SplitView.fillWidth: true
                    SplitView.minimumWidth: 0
                    clip: true

                    Rectangle {
                        anchors.fill: parent
                        color: root.panelSurface
                        border.color: root.macOSStyle
                            ? "transparent" : root.softBorder
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: root.macOSStyle ? 8 : 6
                        spacing: root.macOSStyle ? 5 : 6

                        EpisodeControls {
                            Layout.minimumWidth: 0
                            Layout.maximumWidth: parent.width
                            appBridge: root.appBridge
                            onImportRequested: importSubtitleDialog.open()
                            onImportDocxRequested: importDocxDialog.open()
                            onGlobalSearchRequested: globalSearchDialog.open()
                        }

                        CharacterTable {
                            id: characterTable
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumWidth: 0
                            Layout.maximumWidth: parent.width
                            framed: false
                            appBridge: root.appBridge
                            actorColorDisplayMode: root.actorColorDisplayMode
                            actorColorMuteLevel: root.actorColorMuteLevel
                            actorCellFillFullHeight: root.actorColorCellFillFullHeight
                            actorMarkerShape: root.actorMarkerShape
                            actorMarkerSize: root.actorMarkerSize
                            columnOrder: root.jsonArray(root.characterColumnsOrderJson, [
                                "character", "lines", "rings", "words",
                                "scope", "actor", "preview"
                            ])
                            hiddenColumns: root.jsonArray(root.characterColumnsHiddenJson, [])
                            columnWidthModes: root.jsonObject(root.characterColumnWidthsJson, {})
                            compactRows: root.characterCompactRows
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

                        EpisodeTimeline {
                            Layout.fillWidth: true
                            visible: root.episodeTimelineVisible
                                && root.episodeTimelinePlacement !== "bottom"
                            timelineHeight: root.episodeTimelineHeight
                            useActorColors: root.episodeTimelineActorColors
                            timelineColorMuteLevel: root.episodeTimelineColorMuteLevel
                            castingBackend: root.appBridge ? root.appBridge.casting : null
                            softBorder: root.softBorder
                            softHeader: root.softHeader
                            softRow: root.softRow
                            softAltRow: root.softAltRow
                            softMuted: root.softMuted
                            onCharacterRequested: function(character) {
                                if (root.appBridge && root.appBridge.casting)
                                    root.appBridge.casting.selectCharacter(character)
                            }
                            onHeightAdjustmentRequested: function(height) {
                                root.episodeTimelineHeight = height
                                root.uiState.setIntValue("main.episodeTimelineHeight", height)
                            }
                        }
                    }
                }

                ToolsSidebar {
                    id: toolsSidebar
                    appBridge: root.appBridge
                    visible: !root.compactLayout
                    quickConverterVisible: root.quickConverterVisible
                    SplitView.preferredWidth: root.uiState.intValue("main.toolsPanelWidth", 235)
                    onWidthChanged: if (root.uiReady) panelStateTimer.restart()
                    softBorder: root.softBorder
                    softHeader: root.softHeader
                    softMuted: root.softMuted
                    panelSurface: root.panelSurface
                    onConverterResultsRequested: quickConverterResultsDialog.open()
                    onCharacterPreviewRequested: characterTable.previewSelectedCharacter()
                    onCharacterRenameRequested: characterTable.renameSelectedCharacter()
                    onCharacterSelectionCleared: characterTable.clearCharacterSelection()
                }
            }
        }

        EpisodeTimeline {
            Layout.fillWidth: true
            visible: root.episodeTimelineVisible
                && root.episodeTimelinePlacement === "bottom"
            timelineHeight: root.episodeTimelineHeight
            useActorColors: root.episodeTimelineActorColors
            timelineColorMuteLevel: root.episodeTimelineColorMuteLevel
            castingBackend: root.appBridge ? root.appBridge.casting : null
            softBorder: root.softBorder
            softHeader: root.softHeader
            softRow: root.softRow
            softAltRow: root.softAltRow
            softMuted: root.softMuted
            onCharacterRequested: function(character) {
                if (root.appBridge && root.appBridge.casting)
                    root.appBridge.casting.selectCharacter(character)
            }
            onHeightAdjustmentRequested: function(height) {
                root.episodeTimelineHeight = height
                root.uiState.setIntValue("main.episodeTimelineHeight", height)
            }
        }
    }
}
