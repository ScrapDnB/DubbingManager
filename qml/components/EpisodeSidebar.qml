pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: sidebar
    objectName: "episodeSidebarPanel"
    required property var appBridge
    required property color softBorder
    required property color softMuted
    property bool overlay: false
    signal episodeActivated
    signal importRequested
    signal filesRequested
    signal settingsRequested
    color: Qt.platform.os === "osx" ? Qt.rgba(palette.window.r, palette.window.g, palette.window.b, 0.65) : palette.window
    SystemPalette {
        id: palette
    }
    implicitWidth: 200
    SplitView.minimumWidth: 160
    SplitView.preferredWidth: 200
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Label {
                text: qsTr("Серии")
                font.weight: Font.DemiBold
                Layout.fillWidth: true
                Layout.minimumWidth: 0
            }
            CompactToolButton {
                objectName: "episodeImportButton"
                iconSource: Qt.resolvedUrl("../icons/file-plus.svg")
                toolTipText: qsTr("Импортировать серию")
                onClicked: sidebar.importRequested()
            }
        }
        PersistentListView {
            id: episodes
            objectName: "workspaceEpisodes"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.fillHeight: true
            clip: true
            model: sidebar.appBridge.project.episodesModel
            activeFocusOnTab: true
            currentIndex: -1
            Keys.onReturnPressed: activate(currentIndex)
            Keys.onEnterPressed: activate(currentIndex)
            function activate(index) {
                var row = sidebar.appBridge.project.episodesModel.get(index);
                if (row.name) {
                    sidebar.appBridge.project.selectEpisode(row.name);
                    sidebar.episodeActivated();
                }
            }
            delegate: ItemDelegate {
                id: episodeRow
                required property int index
                required property string name
                required property int lineCount
                required property bool hasVideo
                width: episodes.viewportWidth
                height: 60
                highlighted: sidebar.appBridge.project.currentEpisode === name
                onClicked: {
                    episodes.currentIndex = index;
                    episodes.activate(index);
                }
                Accessible.name: name + ", " + lineCount + qsTr(" реплик")
                contentItem: Column {
                    spacing: 4
                    Label {
                        width: parent.width
                        text: episodeRow.name
                        font.weight: episodeRow.highlighted ? Font.DemiBold : Font.Normal
                        elide: Text.ElideRight
                    }
                    Label {
                        width: parent.width
                        text: episodeRow.lineCount + qsTr(" реплик") + (episodeRow.hasVideo ? qsTr(" · видео") : "")
                        color: sidebar.softMuted
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }
                background: Rectangle {
                    radius: Qt.platform.os === "osx" ? 6 : 4
                    color: episodeRow.highlighted ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.16) : episodeRow.hovered ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.05) : "transparent"
                    Rectangle {
                        visible: Qt.platform.os !== "osx" && episodeRow.highlighted
                        width: 3
                        height: 24
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        radius: 2
                        color: palette.highlight
                    }
                }
            }
            Label {
                objectName: "episodeSidebarEmptyState"
                visible: episodes.count === 0
                anchors.centerIn: parent
                width: parent.width - 12
                text: qsTr("Импортируйте сценарий, чтобы добавить первую серию")
                color: sidebar.softMuted
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
        AdaptiveButton {
            id: episodeActions
            objectName: "episodeActionsButton"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            Layout.maximumWidth: Number.POSITIVE_INFINITY
            text: qsTr("Действия с серией…")
            enabled: sidebar.appBridge.project.currentEpisode.length > 0
            onClicked: episodeMenu.popup()
            Menu {
                id: episodeMenu
                MenuItem {
                    text: qsTr("Добавить или заменить видео…")
                    onTriggered: videoDialog.open()
                }
                MenuItem {
                    text: qsTr("Переименовать…")
                    onTriggered: renameDialog.open()
                }
                MenuItem {
                    text: qsTr("Удалить серию…")
                    onTriggered: deleteDialog.open()
                }
            }
        }
        ToolSeparator {
            orientation: Qt.Horizontal
            Layout.fillWidth: true
        }
        SidebarCommandButton {
            objectName: "episodeFilesButton"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: qsTr("Файлы проекта")
            onClicked: sidebar.filesRequested()
        }
        SidebarCommandButton {
            objectName: "episodeSettingsButton"
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: qsTr("Настройки проекта")
            onClicked: sidebar.settingsRequested()
        }
    }
    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: sidebar.softBorder
    }

    FileDialog {
        id: videoDialog
        title: qsTr("Выберите видео серии")
        currentFolder: sidebar.appBridge.uiState.folderUrl("videoFiles")
        onVisibleChanged: if (visible)
            currentFolder = sidebar.appBridge.uiState.folderUrl("videoFiles")
        nameFilters: ["Видео (*.mp4 *.mkv *.avi *.mov *.m4v *.wmv)", "Все файлы (*)"]
        onAccepted: {
            sidebar.appBridge.uiState.rememberFile("videoFiles", selectedFile.toString());
            sidebar.appBridge.projectFiles.relink(sidebar.appBridge.project.currentEpisode, "video", selectedFile.toString());
        }
    }
    NativeDialogWindow {
        id: renameDialog
        ownerWindow: sidebar.Window.window
        title: qsTr("Переименовать серию")
        modal: true
        width: 380
        height: 150
        standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: {
            nameField.text = sidebar.appBridge.project.currentEpisode;
            nameField.selectAll();
            nameField.forceActiveFocus();
        }
        onAccepted: if (sidebar.appBridge.workspace.flush())
            sidebar.appBridge.project.renameCurrentEpisode(nameField.text)
        content: TextField {
            id: nameField
            anchors.fill: parent
            placeholderText: qsTr("Название серии")
            selectByMouse: true
            onAccepted: renameDialog.accept()
        }
    }
    NativeDialogWindow {
        id: deleteDialog
        ownerWindow: sidebar.Window.window
        title: qsTr("Удалить серию")
        modal: true
        width: 380
        height: 170
        standardButtons: Dialog.Yes | Dialog.No
        content: Label {
            anchors.fill: parent
            text: qsTr("Удалить серию «") + sidebar.appBridge.project.currentEpisode + qsTr("» из проекта?")
            wrapMode: Text.WordWrap
        }
        onAccepted: if (sidebar.appBridge.workspace.flush())
            sidebar.appBridge.project.deleteCurrentEpisode()
    }
}
