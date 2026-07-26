pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    objectName: "projectFilesDialog"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    signal backupsRequested()

    readonly property var projectFilesBackend: appBridge
        ? appBridge.projectFiles : null

    property string selectedEpisode: ""
    property var selectedEpisodes: []
    property var collapsedEpisodes: ({})
    property string selectedKind: ""
    property string selectedPath: ""
    property bool selectedCanRegenerate: false
    property bool selectedHasSourceAss: false
    property bool selectedCanRelink: false
    property int initialTab: 0
    readonly property int episodeColumnWidth: 92
    readonly property int kindColumnWidth: 155
    readonly property int statusColumnWidth: 205

    component FileActionMenuItem: MenuItem {
        id: actionItem

        contentItem: Label {
            text: actionItem.text
            leftPadding: 12
            rightPadding: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            color: actionItem.enabled
                ? actionItem.palette.text : actionItem.palette.mid
        }
    }

    modal: true
    title: qsTr("Файлы проекта")
    standardButtons: Dialog.NoButton
    width: boundedWidth(1120, 28)
    height: boundedHeight(720, 28)

    footer: DialogButtonBox {
        anchors.fill: parent
        AdaptiveButton {
            text: qsTr("Резервные копии...")
            enabled: dialog.appBridge.project.path.length > 0
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: dialog.backupsRequested()
        }
        AdaptiveButton {
            text: qsTr("Закрыть")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }

    function clearSelection() {
        selectedEpisode = ""
        selectedEpisodes = []
        selectedKind = ""
        selectedPath = ""
        selectedCanRegenerate = false
        selectedHasSourceAss = false
        selectedCanRelink = false
        filesView.currentIndex = -1
    }

    function isEpisodeSelected(episode) {
        return selectedEpisodes.indexOf(episode) >= 0
    }

    function isEpisodeCollapsed(episode) {
        return collapsedEpisodes[episode] === true
    }

    function toggleEpisodeCollapsed(episode) {
        var collapsed = Object.assign({}, collapsedEpisodes)
        collapsed[episode] = !isEpisodeCollapsed(episode)
        collapsedEpisodes = collapsed
    }

    function selectEpisodeRow(episode, kind, path, canRegenerate,
                              hasSourceAss, canRelink, modifiers, index) {
        var isMultiSelect = (modifiers & Qt.ControlModifier)
            || (modifiers & Qt.MetaModifier)
        var episodes = selectedEpisodes.slice()
        var selectedIndex = episodes.indexOf(episode)
        if (isMultiSelect) {
            if (selectedIndex >= 0)
                episodes.splice(selectedIndex, 1)
            else
                episodes.push(episode)
        } else {
            episodes = [episode]
        }
        selectedEpisodes = episodes
        selectedEpisode = episode
        selectedKind = kind
        selectedPath = path
        selectedCanRegenerate = canRegenerate
        selectedHasSourceAss = hasSourceAss
        selectedCanRelink = canRelink
        filesView.currentIndex = index
    }

    function openFor(tabName) {
        initialTab = tabName === "health" ? 1 : 0
        tabs.currentIndex = initialTab
        collapsedEpisodes = ({})
        clearSelection()
        projectFilesBackend.refresh()
        open()
    }

    function openRelinkDialog() {
        if (selectedKind === "video") {
            videoFileDialog.open()
        } else if (selectedKind === "working") {
            workingFileDialog.open()
        } else {
            sourceFileDialog.open()
        }
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Выберите папку проекта")
        currentFolder: dialog.appBridge.uiState.folderUrl("projectFolders")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("projectFolders")
        onAccepted: {
            dialog.appBridge.uiState.rememberFolder("projectFolders", selectedFolder.toString())
            dialog.projectFilesBackend.setFolder(selectedFolder.toString())
        }
    }

    FileDialog {
        id: sourceFileDialog
        title: qsTr("Выберите исходный файл серии")
        currentFolder: dialog.appBridge.uiState.folderUrl("sourceFiles")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("sourceFiles")
        nameFilters: ["Тексты серий (*.ass *.srt *.docx)", "Все файлы (*)"]
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("sourceFiles", selectedFile.toString())
            dialog.projectFilesBackend.relink(
                dialog.selectedEpisode,
                "source",
                selectedFile.toString()
            )
        }
    }

    FileDialog {
        id: videoFileDialog
        title: qsTr("Выберите видео серии")
        currentFolder: dialog.appBridge.uiState.folderUrl("videoFiles")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("videoFiles")
        nameFilters: ["Видео (*.mp4 *.mkv *.avi *.mov *.m4v *.wmv)", "Все файлы (*)"]
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("videoFiles", selectedFile.toString())
            dialog.projectFilesBackend.relink(
                dialog.selectedEpisode,
                "video",
                selectedFile.toString()
            )
        }
    }

    FileDialog {
        id: workingFileDialog
        title: qsTr("Выберите рабочий JSON")
        currentFolder: dialog.appBridge.uiState.folderUrl("sourceFiles")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("sourceFiles")
        nameFilters: ["JSON (*.json)", "Все файлы (*)"]
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("sourceFiles", selectedFile.toString())
            dialog.projectFilesBackend.relink(
                dialog.selectedEpisode,
                "working",
                selectedFile.toString()
            )
        }
    }

    FileDialog {
        id: saveAssDialog
        title: qsTr("Сохранить исходный ASS")
        fileMode: FileDialog.SaveFile
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        defaultSuffix: "ass"
        nameFilters: ["ASS (*.ass)"]
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("exports", selectedFile.toString())
            dialog.projectFilesBackend.saveOriginalAss(
                dialog.selectedEpisode,
                selectedFile.toString()
            )
        }
    }

    NativeDialogWindow {
        id: deleteDialog
        ownerWindow: dialog
        modal: true
        title: qsTr("Удалить серию")
        standardButtons: Dialog.Yes | Dialog.No
        width: 420

        content: Label {
            anchors.fill: parent
            width: 360
            text: dialog.selectedEpisodes.length === 1
                ? qsTr("Удалить серию ") + dialog.selectedEpisodes[0]
                    + qsTr(" и все связанные с ней пути из проекта?")
                : qsTr("Удалить выбранные серии (")
                    + dialog.selectedEpisodes.join(", ")
                    + qsTr(") и все связанные с ними пути из проекта?")
            wrapMode: Text.WordWrap
        }

        onAccepted: {
            dialog.projectFilesBackend.deleteEpisodes(dialog.selectedEpisodes)
            dialog.clearSelection()
        }
    }

    Menu {
        id: fileActionsMenu
        width: 360

        FileActionMenuItem {
            text: qsTr("Перепривязать файл...")
            visible: dialog.selectedCanRelink
            height: visible ? implicitHeight : 0
            onTriggered: dialog.openRelinkDialog()
        }
        FileActionMenuItem {
            text: qsTr("Создать рабочий текст из источника")
            visible: dialog.selectedCanRegenerate
            height: visible ? implicitHeight : 0
            onTriggered: dialog.projectFilesBackend.regenerateWorkingText(
                dialog.selectedEpisode
            )
        }
        FileActionMenuItem {
            text: qsTr("Сохранить исходный ASS...")
            visible: dialog.selectedHasSourceAss
            height: visible ? implicitHeight : 0
            onTriggered: saveAssDialog.open()
        }
        FileActionMenuItem {
            text: qsTr("Отвязать видео")
            visible: dialog.selectedKind === "video"
                && dialog.selectedPath !== "-"
            height: visible ? implicitHeight : 0
            onTriggered: {
                dialog.projectFilesBackend.removeVideo(dialog.selectedEpisode)
                dialog.clearSelection()
            }
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Label { text: qsTr("Папка:"); font.bold: true }
            TextField {
                Layout.fillWidth: true
                readOnly: true
                text: dialog.projectFilesBackend
                    ? dialog.projectFilesBackend.folder : ""
                placeholderText: qsTr("Папка проекта не задана")
                selectByMouse: true
            }
            AdaptiveButton { text: qsTr("Выбрать..."); onClicked: folderDialog.open() }
            AdaptiveButton {
                text: qsTr("Отвязать")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: dialog.projectFilesBackend.clearFolder()
            }
            AdaptiveButton {
                text: qsTr("Сканировать")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: dialog.projectFilesBackend.scanFolder()
            }
            AdaptiveButton {
                id: batchImportButton
                text: qsTr("Добавить серии")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: {
                    dialog.clearSelection()
                    dialog.projectFilesBackend.batchImportFolder()
                }
                PlatformToolTip {
                    target: batchImportButton
                    text: qsTr("Добавить найденные ASS, SRT и DOCX вместе с подходящими видео")
                }
            }
            AdaptiveButton { text: qsTr("Обновить"); onClicked: dialog.projectFilesBackend.refresh() }
        }

        NavigationTabBar {
            id: tabs
            Layout.preferredWidth: implicitWidth
            model: ["Файлы", "Проверка"]
            tabWidth: 112
            softMuted: dialog.softMuted
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            ColumnLayout {
                spacing: 6

                Label {
                    Layout.fillWidth: true
                    text: dialog.projectFilesBackend
                        ? dialog.projectFilesBackend.filesSummary : ""
                    color: dialog.softMuted
                }

                TableHeaderSurface {
                    Layout.fillWidth: true
                    Layout.preferredHeight: dialog.tableHeaderHeight
                    softHeader: dialog.softHeader
                    softBorder: dialog.softBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        TableHeaderLabel {
                            text: qsTr("Серия")
                            Layout.preferredWidth: dialog.episodeColumnWidth
                            Layout.minimumWidth: dialog.episodeColumnWidth
                            Layout.maximumWidth: dialog.episodeColumnWidth
                        }
                        TableHeaderLabel {
                            text: qsTr("Тип файла")
                            Layout.preferredWidth: dialog.kindColumnWidth
                            Layout.minimumWidth: dialog.kindColumnWidth
                            Layout.maximumWidth: dialog.kindColumnWidth
                        }
                        TableHeaderLabel {
                            text: qsTr("Статус")
                            Layout.preferredWidth: dialog.statusColumnWidth
                            Layout.minimumWidth: dialog.statusColumnWidth
                            Layout.maximumWidth: dialog.statusColumnWidth
                        }
                        TableHeaderLabel { text: qsTr("Путь"); Layout.fillWidth: true }
                    }
                }

                PersistentListView {
                    id: filesView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    currentIndex: -1
                    model: dialog.projectFilesBackend
                        ? dialog.projectFilesBackend.filesModel : null

                    TapHandler {
                        onTapped: function(eventPoint) {
                            var rowIndex = filesView.indexAt(
                                eventPoint.position.x,
                                eventPoint.position.y + filesView.contentY
                            )
                            if (rowIndex < 0)
                                dialog.clearSelection()
                        }
                    }

                    delegate: Rectangle {
                        id: fileRow

                        required property int index
                        required property string episode
                        required property string kind
                        required property string kindLabel
                        required property string status
                        required property string statusKind
                        required property string path
                        required property bool canRegenerate
                        required property bool hasSourceAss
                        required property bool canRelink

                        width: filesView.viewportWidth
                        readonly property bool episodeHeader: kind === "source"
                        readonly property bool rowVisible: episodeHeader
                            || !dialog.isEpisodeCollapsed(episode)
                        readonly property bool hasActions: canRelink
                            || canRegenerate || hasSourceAss
                            || (kind === "video" && path !== "-")
                        height: rowVisible ? dialog.compactRowHeight : 0
                        visible: rowVisible
                        color: dialog.isEpisodeSelected(fileRow.episode)
                            ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)
                            : (rowHover.hovered ? dialog.softHover
                                : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow))

                        HoverHandler { id: rowHover }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            onClicked: function(mouse) {
                                dialog.selectEpisodeRow(
                                    fileRow.episode, fileRow.kind,
                                    fileRow.path, fileRow.canRegenerate,
                                    fileRow.hasSourceAss, fileRow.canRelink,
                                    mouse.modifiers, fileRow.index
                                )
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8
                            Item {
                                Layout.preferredWidth: dialog.episodeColumnWidth
                                Layout.minimumWidth: dialog.episodeColumnWidth
                                Layout.maximumWidth: dialog.episodeColumnWidth
                                ToolButton {
                                    id: episodeDisclosureButton
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: fileRow.episodeHeader
                                    enabled: visible
                                    implicitWidth: 22
                                    implicitHeight: 22
                                    padding: 4
                                    icon.source: fileRow.episodeHeader
                                        ? Qt.resolvedUrl(dialog.isEpisodeCollapsed(fileRow.episode)
                                            ? "../icons/chevron-right.svg"
                                            : "../icons/chevron-down.svg") : ""
                                    icon.width: 12
                                    icon.height: 12
                                    Accessible.name: dialog.isEpisodeCollapsed(fileRow.episode)
                                        ? qsTr("Развернуть серию")
                                        : qsTr("Свернуть серию")
                                    onClicked: dialog.toggleEpisodeCollapsed(fileRow.episode)
                                    PlatformToolTip {
                                        target: episodeDisclosureButton
                                        text: episodeDisclosureButton.Accessible.name
                                    }
                                }
                                Item {
                                    visible: !fileRow.episodeHeader
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 22
                                    height: 22
                                }
                                Label {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 26
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: fileRow.episode
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            Item {
                                Layout.preferredWidth: dialog.kindColumnWidth
                                Layout.minimumWidth: dialog.kindColumnWidth
                                Layout.maximumWidth: dialog.kindColumnWidth

                                Label {
                                    anchors.left: parent.left
                                    anchors.right: fileRow.hasActions
                                        ? fileActionsButton.left : parent.right
                                    anchors.rightMargin: fileRow.hasActions ? 4 : 0
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: fileRow.kindLabel
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                }
                                RowAccessoryButton {
                                    id: fileActionsButton
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: fileRow.hasActions
                                    toolTipText: qsTr("Действия с файлом")
                                    iconSource: Qt.platform.os === "osx"
                                        ? Qt.resolvedUrl("../icons/ellipsis.svg") : ""
                                    overlayIconSource: Qt.platform.os === "osx"
                                        ? "" : Qt.resolvedUrl("../icons/ellipsis.svg")
                                    onClicked: {
                                        dialog.selectEpisodeRow(
                                            fileRow.episode, fileRow.kind,
                                            fileRow.path, fileRow.canRegenerate,
                                            fileRow.hasSourceAss,
                                            fileRow.canRelink, 0, fileRow.index
                                        )
                                        fileActionsMenu.popup()
                                    }
                                }
                            }
                            Label {
                                text: fileRow.status
                                Layout.preferredWidth: dialog.statusColumnWidth
                                Layout.minimumWidth: dialog.statusColumnWidth
                                Layout.maximumWidth: dialog.statusColumnWidth
                                elide: Text.ElideRight
                                color: fileRow.statusKind === "error" ? "#c94b4b"
                                    : fileRow.statusKind === "warning" ? "#b8860b"
                                    : fileRow.statusKind === "success" ? "#2e8b57"
                                    : dialog.softMuted
                            }
                            Label { text: fileRow.path; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    AdaptiveButton {
                        text: qsTr("Создать недостающие")
                        onClicked: dialog.projectFilesBackend.createMissingWorkingTexts()
                    }
                    AdaptiveButton {
                        text: qsTr("Создать построчные")
                        onClicked: dialog.projectFilesBackend.createMissingSourceLines()
                    }
                    Item { Layout.fillWidth: true }
                    AdaptiveButton {
                        text: dialog.selectedEpisodes.length > 1
                            ? qsTr("Удалить серии (")
                                + dialog.selectedEpisodes.length + ")..."
                            : qsTr("Удалить серию...")
                        enabled: dialog.selectedEpisodes.length > 0
                        onClicked: deleteDialog.open()
                    }
                }
            }

            ColumnLayout {
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: dialog.projectFilesBackend
                            ? dialog.projectFilesBackend.healthSummary : ""
                        color: dialog.softMuted
                    }
                    AdaptiveButton {
                        text: qsTr("Обновить проверку")
                        onClicked: dialog.projectFilesBackend.refresh()
                    }
                }

                TableHeaderSurface {
                    Layout.fillWidth: true
                    Layout.preferredHeight: dialog.tableHeaderHeight
                    softHeader: dialog.softHeader
                    softBorder: dialog.softBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        TableHeaderLabel { text: qsTr("Уровень"); Layout.preferredWidth: 115 }
                        TableHeaderLabel { text: qsTr("Серия"); Layout.preferredWidth: 65 }
                        TableHeaderLabel { text: qsTr("Категория"); Layout.preferredWidth: 125 }
                        TableHeaderLabel { text: qsTr("Сообщение"); Layout.fillWidth: true }
                        TableHeaderLabel { text: qsTr("Путь"); Layout.preferredWidth: 250 }
                    }
                }

                PersistentListView {
                    id: healthView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: dialog.projectFilesBackend
                        ? dialog.projectFilesBackend.healthModel : null

                    delegate: Rectangle {
                        id: healthRow

                        required property int index
                        required property string severity
                        required property string severityLabel
                        required property string episode
                        required property string category
                        required property string message
                        required property string path

                        width: healthView.viewportWidth
                        height: Math.max(36, messageLabel.implicitHeight + 12)
                        color: index % 2 === 0 ? dialog.softRow : dialog.softAltRow

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8
                            Label {
                                text: healthRow.severityLabel
                                Layout.preferredWidth: 115
                                color: healthRow.severity === "error" ? "#c94b4b"
                                    : healthRow.severity === "warning" ? "#b8860b"
                                    : dialog.softMuted
                            }
                            Label { text: healthRow.episode || "-"; Layout.preferredWidth: 65; elide: Text.ElideRight }
                            Label { text: healthRow.category; Layout.preferredWidth: 125; elide: Text.ElideRight }
                            Label {
                                id: messageLabel
                                text: healthRow.message
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                            Label { text: healthRow.path || "-"; Layout.preferredWidth: 250; elide: Text.ElideMiddle }
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        visible: parent.count === 0
                        text: qsTr("Проблем не найдено")
                        color: dialog.softMuted
                    }
                }
            }
        }
    }
}
