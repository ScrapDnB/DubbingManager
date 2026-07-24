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
    readonly property int controlHeight: Math.max(
        40, Math.ceil(controlsFontMetrics.height + 18)
    )

    Layout.fillWidth: true
    Layout.preferredHeight: controlHeight
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
        spacing: 4

        Label {
            text: qsTr("Серия")
            font.bold: true
            visible: !controls.narrow
        }

        ComboBox {
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

        Item { Layout.fillWidth: true }

        Label { text: qsTr("Актёр"); visible: !controls.compact }

        ComboBox {
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
                function onActorFilterChanged() {
                    if (!controls.castingBackend) {
                        return
                    }
                    var idx = actorFilterCombo.indexOfValue(controls.castingBackend.actorFilter)
                    actorFilterCombo.currentIndex = idx >= 0 ? idx : 0
                }
            }
        }

        CheckBox {
            text: qsTr("Неназначенные")
            visible: !controls.narrow
            enabled: controls.appBridge !== null
            checked: controls.castingBackend ? controls.castingBackend.showUnassignedOnly : false
            onToggled: if (controls.castingBackend) controls.castingBackend.setShowUnassignedOnly(checked)
        }

        TextField {
            Layout.preferredWidth: controls.narrow ? 120
                : (controls.compact ? 150 : 180)
            Layout.minimumHeight: controls.controlHeight
            Layout.preferredHeight: controls.controlHeight
            Layout.maximumHeight: controls.controlHeight
            Layout.alignment: Qt.AlignVCenter
            placeholderText: qsTr("Поиск")
            enabled: controls.appBridge !== null
            text: controls.castingBackend ? controls.castingBackend.searchText : ""
            selectByMouse: true
            Accessible.name: qsTr("Поиск по персонажам")
            onTextEdited: if (controls.castingBackend) controls.castingBackend.setSearchText(text)
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/x.svg")
            toolTipText: qsTr("Сбросить фильтры")
            enabled: controls.castingBackend && (controls.castingBackend.actorFilter.length > 0 || controls.castingBackend.showUnassignedOnly || controls.castingBackend.searchText.length > 0)
            onClicked: {
                if (!controls.castingBackend) {
                    return
                }
                controls.castingBackend.setActorFilter("")
                controls.castingBackend.setShowUnassignedOnly(false)
                controls.castingBackend.setSearchText("")
            }
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/search.svg")
            toolTipText: qsTr("Глобальный поиск")
            enabled: controls.projectBackend && controls.projectBackend.currentEpisode.length > 0
            onClicked: controls.globalSearchRequested()
        }
    }
}
