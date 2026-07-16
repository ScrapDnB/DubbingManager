import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: controls

    required property var appBridge
    readonly property var projectBackend: appBridge ? appBridge.project : null
    readonly property var castingBackend: appBridge ? appBridge.casting : null
    readonly property bool compact: width < 1020
    readonly property bool narrow: width < 780

    Layout.fillWidth: true
    Layout.preferredHeight: 32
    implicitHeight: 32
    spacing: 0
    signal importRequested()
    signal importDocxRequested()
    signal globalSearchRequested()

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
        Layout.preferredHeight: 32
        spacing: 4

        Label {
            text: qsTr("Серия")
            font.bold: true
            visible: !controls.narrow
        }

        PlatformComboBox {
            id: episodeCombo
            Layout.preferredWidth: controls.narrow ? 105 : 140
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

        Button {
            id: importButton
            text: qsTr("Импорт")
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

        PlatformComboBox {
            id: actorFilterCombo
            Layout.preferredWidth: controls.narrow ? 95 : (controls.compact ? 120 : 150)
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
            Layout.preferredWidth: controls.narrow ? 90 : (controls.compact ? 120 : 170)
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
