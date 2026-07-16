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
    property string selectedKind: ""
    property string selectedPath: ""
    property bool selectedCanRegenerate: false
    property bool selectedHasSourceAss: false
    property bool selectedCanRelink: false
    property int initialTab: 0

    modal: true
    title: qsTr("Файлы проекта")
    standardButtons: Dialog.NoButton
    width: boundedWidth(1120, 28)
    height: boundedHeight(720, 28)

    footer: DialogButtonBox {
        anchors.fill: parent
        Button {
            text: qsTr("Резервные копии...")
            enabled: dialog.appBridge.project.path.length > 0
            onClicked: dialog.backupsRequested()
        }
        Button {
            text: qsTr("Закрыть")
            onClicked: dialog.close()
        }
    }

    function clearSelection() {
        selectedEpisode = ""
        selectedKind = ""
        selectedPath = ""
        selectedCanRegenerate = false
        selectedHasSourceAss = false
        selectedCanRelink = false
        filesView.currentIndex = -1
    }

    function openFor(tabName) {
        initialTab = tabName === "health" ? 1 : 0
        tabs.currentIndex = initialTab
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
            text: qsTr("Удалить серию ") + dialog.selectedEpisode
                + " и все связанные с ней пути из проекта?"
            wrapMode: Text.WordWrap
        }

        onAccepted: {
            dialog.projectFilesBackend.deleteEpisode(dialog.selectedEpisode)
            dialog.clearSelection()
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
            Button { text: qsTr("Выбрать..."); onClicked: folderDialog.open() }
            Button {
                text: qsTr("Отвязать")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: dialog.projectFilesBackend.clearFolder()
            }
            Button {
                text: qsTr("Сканировать")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: dialog.projectFilesBackend.scanFolder()
            }
            Button {
                text: qsTr("Добавить серии")
                enabled: dialog.projectFilesBackend
                    && dialog.projectFilesBackend.folder.length > 0
                onClicked: {
                    dialog.clearSelection()
                    dialog.projectFilesBackend.batchImportFolder()
                }
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Добавить найденные ASS, SRT и DOCX вместе с подходящими видео")
            }
            Button { text: qsTr("Обновить"); onClicked: dialog.projectFilesBackend.refresh() }
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

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    color: dialog.softHeader
                    border.color: dialog.softBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        Label { text: qsTr("Серия"); font.bold: true; Layout.preferredWidth: 70 }
                        Label { text: qsTr("Файл"); font.bold: true; Layout.preferredWidth: 125 }
                        Label { text: qsTr("Статус"); font.bold: true; Layout.preferredWidth: 120 }
                        Label { text: qsTr("Путь"); font.bold: true; Layout.fillWidth: true }
                    }
                }

                ListView {
                    id: filesView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    currentIndex: -1
                    model: dialog.projectFilesBackend
                        ? dialog.projectFilesBackend.filesModel : null

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

                        width: filesView.width
                        height: 34
                        color: filesView.currentIndex === index
                            ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)
                            : (rowHover.hovered ? dialog.softHover
                                : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow))

                        HoverHandler { id: rowHover }
                        TapHandler {
                            onTapped: {
                                filesView.currentIndex = fileRow.index
                                dialog.selectedEpisode = fileRow.episode
                                dialog.selectedKind = fileRow.kind
                                dialog.selectedPath = fileRow.path
                                dialog.selectedCanRegenerate = fileRow.canRegenerate
                                dialog.selectedHasSourceAss = fileRow.hasSourceAss
                                dialog.selectedCanRelink = fileRow.canRelink
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8
                            Label { text: fileRow.episode; Layout.preferredWidth: 70; elide: Text.ElideRight }
                            Label { text: fileRow.kindLabel; Layout.preferredWidth: 125; elide: Text.ElideRight }
                            Label {
                                text: fileRow.status
                                Layout.preferredWidth: 120
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
                    Button {
                        text: qsTr("Перепривязать...")
                        enabled: dialog.selectedEpisode.length > 0
                            && dialog.selectedCanRelink
                        onClicked: dialog.openRelinkDialog()
                    }
                    Button {
                        text: qsTr("Создать из источника")
                        enabled: dialog.selectedEpisode.length > 0
                            && dialog.selectedCanRegenerate
                        onClicked: dialog.projectFilesBackend.regenerateWorkingText(
                            dialog.selectedEpisode
                        )
                    }
                    Button {
                        text: qsTr("Создать недостающие")
                        onClicked: dialog.projectFilesBackend.createMissingWorkingTexts()
                    }
                    Button {
                        text: qsTr("Сохранить исходный ASS...")
                        enabled: dialog.selectedHasSourceAss
                        onClicked: saveAssDialog.open()
                    }
                    Button {
                        text: qsTr("Отвязать видео")
                        enabled: dialog.selectedEpisode.length > 0
                            && dialog.selectedKind === "video"
                            && dialog.selectedPath !== "-"
                        onClicked: {
                            dialog.projectFilesBackend.removeVideo(
                                dialog.selectedEpisode
                            )
                            dialog.clearSelection()
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: qsTr("Удалить серию...")
                        enabled: dialog.selectedEpisode.length > 0
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
                    Button {
                        text: qsTr("Обновить проверку")
                        onClicked: dialog.projectFilesBackend.refresh()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    color: dialog.softHeader
                    border.color: dialog.softBorder

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        Label { text: qsTr("Уровень"); font.bold: true; Layout.preferredWidth: 115 }
                        Label { text: qsTr("Серия"); font.bold: true; Layout.preferredWidth: 65 }
                        Label { text: qsTr("Категория"); font.bold: true; Layout.preferredWidth: 125 }
                        Label { text: qsTr("Сообщение"); font.bold: true; Layout.fillWidth: true }
                        Label { text: qsTr("Путь"); font.bold: true; Layout.preferredWidth: 250 }
                    }
                }

                ListView {
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

                        width: ListView.view.width
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
