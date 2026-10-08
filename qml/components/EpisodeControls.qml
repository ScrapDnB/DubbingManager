import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id: controls

    required property var appBridge
    readonly property var projectBackend: appBridge ? appBridge.project : null
    readonly property var castingBackend: appBridge ? appBridge.casting : null
    readonly property bool compact: width < 1020
    readonly property bool narrow: width < 780
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int controlHeight: Math.max(
        macOSStyle ? 28 : 40,
        Math.ceil(controlsFontMetrics.height + (macOSStyle ? 8 : 18))
    )

    Layout.fillWidth: true
    Layout.fillHeight: false
    // The toolbar adapts its contents itself and must not impose the summed
    // implicit width of every control on the workspace column.
    Layout.minimumWidth: 0
    Layout.minimumHeight: controlHeight
    Layout.preferredHeight: controlHeight
    Layout.maximumHeight: controlHeight
    implicitHeight: controlHeight
    spacing: 0
    signal importRequested()
    signal importDocxRequested()
    signal globalSearchRequested()

    FontMetrics {
        id: controlsFontMetrics
        font: Application.font
    }

    FileDialog {
        id: episodeVideoDialog
        title: qsTr("Выберите видео серии")
        currentFolder: controls.appBridge
            ? controls.appBridge.uiState.folderUrl("videoFiles")
            : ""
        nameFilters: [
            "Видео (*.mp4 *.mkv *.avi *.mov *.m4v *.wmv)",
            "Все файлы (*)"
        ]
        onAccepted: {
            if (!controls.appBridge || !controls.projectBackend.currentEpisode) {
                return
            }
            controls.appBridge.uiState.rememberFile(
                "videoFiles", selectedFile.toString()
            )
            controls.appBridge.projectFiles.relink(
                controls.projectBackend.currentEpisode,
                "video",
                selectedFile.toString()
            )
        }
    }

    NativeDialogWindow {
        id: renameEpisodeDialog
        ownerWindow: controls.Window.window
        modal: true
        title: qsTr("Переименовать серию")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 360
        height: 150

        onOpened: {
            episodeNameField.text = controls.projectBackend ? controls.projectBackend.currentEpisode : ""
            episodeNameField.selectAll()
            episodeNameField.forceActiveFocus()
        }
        onAccepted: if (controls.projectBackend) controls.projectBackend.renameCurrentEpisode(episodeNameField.text)

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            TextField {
                id: episodeNameField
                Layout.fillWidth: true
                placeholderText: qsTr("Название серии")
                selectByMouse: true
                onAccepted: renameEpisodeDialog.accept()
            }
        }
    }

    NativeDialogWindow {
        id: deleteEpisodeDialog
        ownerWindow: controls.Window.window
        modal: true
        title: qsTr("Удалить серию")
        standardButtons: Dialog.Yes | Dialog.No
        width: 380
        height: 160

        content: Label {
            anchors.fill: parent
            text: controls.projectBackend ? "Удалить серию " + controls.projectBackend.currentEpisode + " из проекта?" : ""
            wrapMode: Text.WordWrap
            width: 320
        }

        onAccepted: if (controls.projectBackend) controls.projectBackend.deleteCurrentEpisode()
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: controls.controlHeight
        spacing: controls.macOSStyle ? 6 : 4

        Label {
            text: qsTr("Серия")
            font.weight: Font.DemiBold
            visible: !controls.narrow
        }

        PlatformComboBox {
            id: episodeCombo
            Layout.preferredWidth: controls.narrow ? 105 : 140
            Layout.minimumHeight: controls.controlHeight
            Layout.preferredHeight: controls.controlHeight
            Layout.maximumHeight: controls.controlHeight
            Layout.alignment: Qt.AlignVCenter
            model: controls.projectBackend ? controls.projectBackend.episodesModel : null
            textRole: "name"
            valueRole: "name"
            onActivated: if (controls.projectBackend) controls.projectBackend.selectEpisode(currentValue)
            Accessible.name: qsTr("Текущая серия")
            onCountChanged: syncCurrentEpisode()

            function syncCurrentEpisode() {
                if (!controls.projectBackend) {
                    return
                }
                var idx = episodeCombo.indexOfValue(controls.projectBackend.currentEpisode)
                episodeCombo.currentIndex = idx >= 0 ? idx : 0
            }

            Connections {
                target: controls.projectBackend
                function onCurrentEpisodeChanged() {
                    episodeCombo.syncCurrentEpisode()
                }
            }
        }

        CompactToolButton {
            id: importButton
            iconSource: Qt.resolvedUrl("../icons/file-plus.svg")
            toolTipText: qsTr("Импорт")
            enabled: controls.appBridge !== null
            onClicked: importMenu.open()
            Menu {
                id: importMenu
                y: importButton.height
                MenuItem { text: qsTr("ASS / SRT..."); onTriggered: controls.importRequested() }
                MenuItem { text: qsTr("DOCX..."); onTriggered: controls.importDocxRequested() }
            }
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/video.svg")
            toolTipText: qsTr("Добавить или заменить видео серии")
            enabled: controls.projectBackend
                && controls.projectBackend.currentEpisode.length > 0
            onClicked: episodeVideoDialog.open()
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/pencil.svg")
            toolTipText: qsTr("Переименовать серию")
            enabled: controls.projectBackend && controls.projectBackend.currentEpisode.length > 0
            onClicked: renameEpisodeDialog.open()
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/trash.svg")
            toolTipText: qsTr("Удалить серию")
            enabled: controls.projectBackend && controls.projectBackend.currentEpisode.length > 0
            onClicked: deleteEpisodeDialog.open()
        }

        ToolSeparator {
            visible: controls.macOSStyle && !controls.narrow
            Layout.fillHeight: true
        }

        Item { Layout.fillWidth: true }

        Label {
            text: qsTr("Актёр")
            visible: !controls.compact && !controls.macOSStyle
        }

        PlatformComboBox {
            id: actorFilterCombo
            Layout.preferredWidth: controls.narrow ? 150
                : (controls.compact ? 220 : 230)
            Layout.minimumHeight: controls.controlHeight
            Layout.preferredHeight: controls.controlHeight
            Layout.maximumHeight: controls.controlHeight
            Layout.alignment: Qt.AlignVCenter
            model: controls.castingBackend ? controls.castingBackend.actorFilterModel : null
            textRole: "name"
            valueRole: "id"
            enabled: controls.appBridge !== null
            onActivated: if (controls.castingBackend) controls.castingBackend.setActorFilter(currentValue)
            Accessible.name: qsTr("Фильтр по актёру")

            Connections {
                target: controls.castingBackend
                function syncActorFilter() {
                    if (!controls.castingBackend) {
                        return
                    }
                    var filterId = controls.castingBackend.showUnassignedOnly
                        ? "__unassigned__" : controls.castingBackend.actorFilter
                    var idx = actorFilterCombo.indexOfValue(filterId)
                    actorFilterCombo.currentIndex = idx >= 0 ? idx : 0
                }

                function onActorFilterChanged() { syncActorFilter() }
                function onShowUnassignedOnlyChanged() { syncActorFilter() }
            }
        }

        CompactToolButton {
            visible: controls.width < 920
            iconSource: Qt.resolvedUrl("../icons/search.svg")
            toolTipText: qsTr("Глобальный поиск")
            enabled: controls.projectBackend && controls.projectBackend.currentEpisode.length > 0
            onClicked: controls.globalSearchRequested()
        }

        AdaptiveButton {
            visible: controls.width >= 920
            text: qsTr("Глобальный поиск")
            enabled: controls.projectBackend && controls.projectBackend.currentEpisode.length > 0
            onClicked: controls.globalSearchRequested()
        }
    }
}
