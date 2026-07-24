import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var backend: appBridge ? appBridge.settings : null
    required property color softBorder
    required property color softMuted

    signal projectFilesRequested(string view)
    signal rolesRequested()
    signal assignmentExportRequested()
    signal assignmentImportRequested()

    property var montageDraft: ({})
    property var prompterDraft: ({})
    property var mergeDraft: ({})
    property var assDraft: ({})
    property var srtDraft: ({})
    property var docxDraft: ({})

    modal: true
    title: qsTr("Настройки проекта")
    standardButtons: Dialog.NoButton
    width: boundedWidth(860, 36)
    height: boundedHeight(620, 36)

    function openFor(tabIndex) {
        projectNavigation.currentIndex = tabIndex || 0
        projectNameField.text = backend.projectName
        authorField.text = backend.projectAuthor
        studioField.text = backend.projectStudio
        montageDraft = Object.assign({}, backend.projectMontageConfig)
        prompterDraft = Object.assign({}, backend.projectPrompterConfig)
        mergeDraft = Object.assign({}, backend.projectMergeConfig)
        assDraft = Object.assign({}, backend.projectAssImportConfig)
        srtDraft = Object.assign({}, backend.projectSrtImportConfig)
        docxDraft = Object.assign({}, backend.projectDocxImportConfig)
        open()
    }

    content: RowLayout {
        anchors.fill: parent
        spacing: 12

        SettingsNavigation {
            id: projectNavigation
            Layout.preferredWidth: 174
            Layout.fillHeight: true
            sections: [
                "Проект",
                "Серии и файлы",
                "Роли",
                "Монтажный лист",
                "Импорт",
                "Телесуфлёр",
                "Перенос"
            ]
            softMuted: dialog.softMuted
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: projectNavigation.currentIndex

            PersistentScrollView {
                id: projectPage
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: projectPage.availableWidth
                    spacing: 12

                    GroupBox {
                        title: qsTr("Сведения о проекте")
                        Layout.fillWidth: true
                        GridLayout {
                            anchors.fill: parent
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 8

                            Label { text: qsTr("Название:") }
                            TextField {
                                id: projectNameField
                                Layout.fillWidth: true
                                selectByMouse: true
                            }
                            Label { text: qsTr("Тип:") }
                            Label { text: dialog.backend.projectKindLabel; color: dialog.softMuted }
                            Label { text: qsTr("Автор проекта:") }
                            TextField {
                                id: authorField
                                Layout.fillWidth: true
                                selectByMouse: true
                            }
                            Label { text: qsTr("Студия:") }
                            TextField {
                                id: studioField
                                Layout.fillWidth: true
                                selectByMouse: true
                            }
                        }
                    }

                    GroupBox {
                        title: qsTr("Хранилище")
                        Layout.fillWidth: true
                        GridLayout {
                            anchors.fill: parent
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 6
                            Label { text: qsTr("Файл проекта:") }
                            Label { text: dialog.backend.projectPath; color: dialog.softMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Label { text: qsTr("Рабочая папка:") }
                            Label { text: dialog.backend.projectFolder; color: dialog.softMuted; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Label { text: qsTr("Серии:") }
                            Label { text: dialog.backend.episodeCount }
                            Label { text: qsTr("Рабочие тексты:") }
                            Label { text: dialog.backend.workingTextCount }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            ColumnLayout {
                spacing: 12
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Управление исходниками, рабочими текстами, видео и диагностикой проекта.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                GroupBox {
                    title: qsTr("Файлы проекта")
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent
                        Label {
                            Layout.fillWidth: true
                            text: dialog.backend.episodeCount + " серий · "
                                + dialog.backend.workingTextCount + " рабочих текстов"
                            color: dialog.softMuted
                        }
                        RowLayout {
                            AdaptiveButton {
                                text: qsTr("Файлы проекта...")
                                onClicked: dialog.projectFilesRequested("files")
                            }
                            AdaptiveButton {
                                text: qsTr("Проверка проекта...")
                                onClicked: dialog.projectFilesRequested("health")
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 12
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Просмотр ролей всего проекта и массовое назначение актёров.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                AdaptiveButton {
                    text: qsTr("Открыть роли проекта...")
                    onClicked: dialog.rolesRequested()
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Применить глобальные")
                        onClicked: dialog.montageDraft = Object.assign(
                            {}, dialog.backend.globalMontageConfig
                        )
                    }
                    AdaptiveButton {
                        text: qsTr("Сохранить по умолчанию")
                        onClicked: dialog.backend.saveConfigAsDefault(
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
                        text: qsTr("Применить глобальные")
                        onClicked: {
                            dialog.mergeDraft = Object.assign({}, dialog.backend.globalMergeConfig)
                            dialog.assDraft = Object.assign({}, dialog.backend.globalAssImportConfig)
                            dialog.srtDraft = Object.assign({}, dialog.backend.globalSrtImportConfig)
                            dialog.docxDraft = Object.assign({}, dialog.backend.globalDocxImportConfig)
                        }
                    }
                    AdaptiveButton {
                        text: qsTr("Сохранить по умолчанию")
                        onClicked: dialog.backend.saveImportConfigAsDefault(
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
                        text: qsTr("Применить глобальные")
                        onClicked: dialog.prompterDraft = Object.assign(
                            {}, dialog.backend.globalPrompterConfig
                        )
                    }
                    AdaptiveButton {
                        text: qsTr("Сохранить по умолчанию")
                        onClicked: dialog.backend.saveConfigAsDefault(
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

            ColumnLayout {
                spacing: 12
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Переносит актёров проекта, глобальные назначения персонажей и назначения по сериям. При импорте актёры сопоставляются по имени.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                GroupBox {
                    title: qsTr("Распределение актёров")
                    Layout.fillWidth: true
                    RowLayout {
                        anchors.fill: parent
                        AdaptiveButton {
                            text: qsTr("Экспорт...")
                            onClicked: dialog.assignmentExportRequested()
                        }
                        AdaptiveButton {
                            text: qsTr("Импорт...")
                            onClicked: dialog.assignmentImportRequested()
                        }
                        Item { Layout.fillWidth: true }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Импорт применяется одной операцией и может быть отменён через Undo.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        AdaptiveButton {
            text: qsTr("Сохранить")
            onClicked: {
                var saved = dialog.backend.applyProjectSettingsFull(
                    projectNameField.text,
                    authorField.text,
                    studioField.text,
                    dialog.montageDraft,
                    dialog.prompterDraft,
                    dialog.mergeDraft,
                    dialog.assDraft,
                    dialog.srtDraft,
                    dialog.docxDraft
                )
                if (saved) dialog.close()
            }
        }
        AdaptiveButton { text: qsTr("Отмена"); onClicked: dialog.close() }
    }
}
