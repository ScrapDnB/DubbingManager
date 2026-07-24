pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var backend: appBridge ? appBridge.settings : null
    required property color softMuted

    signal actorBaseExportRequested()
    signal actorBaseImportRequested()

    property var montageDraft: ({})
    property var prompterDraft: ({})
    property var mergeDraft: ({})
    property var assDraft: ({})
    property var srtDraft: ({})
    property var docxDraft: ({})
    property var backupDraft: ({})

    modal: true
    title: qsTr("Глобальные настройки")
    standardButtons: Dialog.NoButton
    width: boundedWidth(820, 36)
    height: boundedHeight(590, 36)

    function openSettings() {
        keywordsArea.text = backend.audiobookKeywords
        montageDraft = Object.assign({}, backend.globalMontageConfig)
        prompterDraft = Object.assign({}, backend.globalPrompterConfig)
        mergeDraft = Object.assign({}, backend.globalMergeConfig)
        assDraft = Object.assign({}, backend.globalAssImportConfig)
        srtDraft = Object.assign({}, backend.globalSrtImportConfig)
        docxDraft = Object.assign({}, backend.globalDocxImportConfig)
        backupDraft = Object.assign({}, backend.globalBackupConfig)
        backupModeCombo.currentIndex = backupModeCombo.indexOfValue(
            backupDraft.path_mode || "relative"
        )
        globalNavigation.currentIndex = 0
        open()
    }

    content: RowLayout {
        anchors.fill: parent
        spacing: 12

        SettingsNavigation {
            id: globalNavigation
            Layout.preferredWidth: 174
            Layout.fillHeight: true
            sections: [
                "Интерфейс",
                "Резервные копии",
                "Аудиокниги",
                "Актёры",
                "Импорт",
                "Монтажный лист",
                "Телесуфлёр",
                "REAPER / OSC"
            ]
            softMuted: dialog.softMuted
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: globalNavigation.currentIndex

            ColumnLayout {
                spacing: 12
                Label {
                    Layout.fillWidth: true
                    text: qsTr("В этой предварительной версии интерфейс доступен на русском языке.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 12

                CheckBox {
                    id: backupEnabled
                    text: qsTr("Создавать резервные копии проектов")
                    checked: Boolean(dialog.backupDraft.enabled)
                    onToggled: {
                        var next = Object.assign({}, dialog.backupDraft)
                        next.enabled = checked
                        dialog.backupDraft = next
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10
                    enabled: backupEnabled.checked

                    Label { text: qsTr("Расположение:") }
                    ComboBox {
                        id: backupModeCombo
                        Layout.fillWidth: true
                        textRole: "label"
                        valueRole: "value"
                        model: ListModel {
                            ListElement { label: "Относительно папки проекта"; value: "relative" }
                            ListElement { label: "Абсолютный путь"; value: "absolute" }
                        }
                        onActivated: function(index) {
                            var next = Object.assign({}, dialog.backupDraft)
                            next.path_mode = currentValue
                            var oldPath = String(next.directory || "")
                            if (currentValue === "relative") {
                                if (oldPath.length === 0 || oldPath.startsWith("/")
                                        || /^[A-Za-z]:[\\/]/.test(oldPath))
                                    next.directory = ".backups"
                            } else if (!oldPath.startsWith("/")
                                    && !/^[A-Za-z]:[\\/]/.test(oldPath)) {
                                next.directory = ""
                            }
                            dialog.backupDraft = next
                        }
                    }

                    Label {
                        text: backupModeCombo.currentValue === "absolute"
                            ? "Папка:" : "Относительный путь:"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: backupDirectoryField
                            Layout.fillWidth: true
                            text: String(dialog.backupDraft.directory || "")
                            placeholderText: backupModeCombo.currentValue === "absolute"
                                ? "/путь/к/копиям" : ".backups"
                            selectByMouse: true
                            onEditingFinished: {
                                var next = Object.assign({}, dialog.backupDraft)
                                next.directory = text
                                dialog.backupDraft = next
                            }
                        }
                        AdaptiveButton {
                            text: qsTr("Выбрать...")
                            visible: backupModeCombo.currentValue === "absolute"
                            onClicked: backupFolderDialog.open()
                        }
                    }

                    Label { text: qsTr("Интервал:") }
                    RowLayout {
                        SpinBox {
                            from: 1
                            to: 1440
                            editable: true
                            value: Number(dialog.backupDraft.interval_minutes || 5)
                            onValueModified: {
                                var next = Object.assign({}, dialog.backupDraft)
                                next.interval_minutes = value
                                dialog.backupDraft = next
                            }
                        }
                        Label { text: qsTr("минут"); color: dialog.softMuted }
                        Item { Layout.fillWidth: true }
                    }

                    Label { text: qsTr("Хранить копий:") }
                    SpinBox {
                        from: 1
                        to: 100
                        editable: true
                        value: Number(dialog.backupDraft.max_backups || 10)
                        onValueModified: {
                            var next = Object.assign({}, dialog.backupDraft)
                            next.max_backups = value
                            dialog.backupDraft = next
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: backupModeCombo.currentValue === "absolute"
                        ? "В выбранной папке программа создаст отдельную подпапку для каждого проекта."
                        : "Путь вычисляется от папки каждого файла .dub. Например, .backups или Backup/Projects."
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Копии имеют расширение .dub_backup и содержат полный сохраняемый проект.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Слова, по которым программа распознаёт начало главы. По одному варианту на строку.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                TextArea {
                    id: keywordsArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    placeholderText: qsTr("Глава\nChapter")
                }
            }

            ColumnLayout {
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Глобальная база хранит имена и пол актёров отдельно от проектов. Цвета остаются настройкой конкретного проекта.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                PersistentListView {
                    id: globalActorsView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: dialog.appBridge.actorLibrary.globalActorsModel
                    delegate: ItemDelegate {
                        id: actorRow
                        required property string name
                        required property string gender
                        width: globalActorsView.viewportWidth
                        text: name + (gender ? " · " + gender : "")
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: globalActorsView.count === 0
                        text: qsTr("Глобальная база пуста")
                        color: dialog.softMuted
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Экспорт...")
                        enabled: globalActorsView.count > 0
                        onClicked: dialog.actorBaseExportRequested()
                    }
                    AdaptiveButton {
                        text: qsTr("Импорт...")
                        onClicked: dialog.actorBaseImportRequested()
                    }
                    Item { Layout.fillWidth: true }
                }
            }

            ColumnLayout {
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Применить к проекту")
                        onClicked: dialog.backend.applyImportConfigToProject(
                            dialog.mergeDraft,
                            dialog.assDraft,
                            dialog.srtDraft,
                            dialog.docxDraft
                        )
                    }
                    Item { Layout.fillWidth: true }
                }
                ImportSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    mergeConfiguration: dialog.mergeDraft
                    assConfiguration: dialog.assDraft
                    srtConfiguration: dialog.srtDraft
                    docxConfiguration: dialog.docxDraft
                    docxPresets: dialog.backend.globalDocxImportPresets
                    softMuted: dialog.softMuted
                    onMergeEdited: function(config) { dialog.mergeDraft = config }
                    onAssEdited: function(config) { dialog.assDraft = config }
                    onSrtEdited: function(config) { dialog.srtDraft = config }
                    onDocxEdited: function(config) { dialog.docxDraft = config }
                    onSaveDocxPresetRequested: function(name, config) {
                        dialog.backend.saveDocxImportPreset(name, config)
                    }
                    onDeleteDocxPresetRequested: function(name) {
                        dialog.backend.deleteDocxImportPreset(name)
                    }
                }
            }

            ColumnLayout {
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Применить к проекту")
                        onClicked: dialog.backend.applyGlobalConfigToProject(
                            "montage", dialog.montageDraft
                        )
                    }
                    Item { Layout.fillWidth: true }
                }
                MontageSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    configuration: dialog.montageDraft
                    onConfigEdited: function(config) { dialog.montageDraft = config }
                }
            }

            ColumnLayout {
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Применить к проекту")
                        onClicked: dialog.backend.applyGlobalConfigToProject(
                            "prompter", dialog.prompterDraft
                        )
                    }
                    Item { Layout.fillWidth: true }
                }
                TeleprompterSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    configuration: dialog.prompterDraft
                    onConfigEdited: function(config) { dialog.prompterDraft = config }
                }
            }

            ReaperOscSettingsPane {
                Layout.fillWidth: true
                Layout.fillHeight: true
                configuration: dialog.prompterDraft
                softMuted: dialog.softMuted
                onConfigEdited: function(config) {
                    dialog.prompterDraft = config
                }
            }
        }
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        AdaptiveButton {
            text: qsTr("Сохранить")
            onClicked: {
                if (dialog.backend.applyGlobalSettingsComplete(
                    "ru",
                    keywordsArea.text,
                    dialog.montageDraft,
                    dialog.prompterDraft,
                    dialog.mergeDraft,
                    dialog.assDraft,
                    dialog.srtDraft,
                    dialog.docxDraft,
                    dialog.backupDraft
                )) dialog.close()
            }
        }
        AdaptiveButton { text: qsTr("Отмена"); onClicked: dialog.close() }
    }

    FolderDialog {
        id: backupFolderDialog
        title: qsTr("Папка резервных копий")
        currentFolder: dialog.appBridge.uiState.folderUrl("backupFolders")
        onVisibleChanged: if (visible)
            currentFolder = dialog.appBridge.uiState.folderUrl("backupFolders")
        onAccepted: {
            dialog.appBridge.uiState.rememberFolder(
                "backupFolders", selectedFolder.toString()
            )
            var next = Object.assign({}, dialog.backupDraft)
            next.directory = dialog.appBridge.uiState.localPath(
                selectedFolder.toString()
            )
            next.path_mode = "absolute"
            dialog.backupDraft = next
            backupModeCombo.currentIndex = backupModeCombo.indexOfValue("absolute")
        }
    }
}
