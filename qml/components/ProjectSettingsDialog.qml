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
        open()
    }

    content: RowLayout {
        anchors.fill: parent
        spacing: dialog.macOSStyle ? 16 : 12

        SettingsNavigation {
            id: projectNavigation
            Layout.preferredWidth: implicitWidth
            Layout.fillHeight: true
            sections: [
                "Проект",
                "Серии и файлы",
                "Роли",
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

                    SettingsPageHeader {
                        title: qsTr("Проект")
                        subtitle: qsTr("Основные сведения и расположение файлов проекта.")
                    }

                    FormSection {
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

                    FormSection {
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
                SettingsPageHeader {
                    title: qsTr("Серии и файлы")
                    subtitle: qsTr("Исходники, рабочие тексты, видео и диагностика проекта.")
                }
                FormSection {
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
                SettingsPageHeader {
                    title: qsTr("Роли")
                    subtitle: qsTr("Просмотр ролей всего проекта и массовое назначение актёров.")
                }
                AdaptiveButton {
                    text: qsTr("Открыть роли проекта...")
                    onClicked: dialog.rolesRequested()
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 12
                SettingsPageHeader {
                    title: qsTr("Перенос")
                    subtitle: qsTr("Актёры и назначения по проекту и сериям. При импорте актёры сопоставляются по имени.")
                }
                FormSection {
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
            highlighted: dialog.macOSStyle
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                var saved = dialog.backend.applyProjectSettingsFull(
                    projectNameField.text,
                    authorField.text,
                    studioField.text
                )
                if (saved) dialog.close()
            }
        }
        AdaptiveButton {
            text: qsTr("Отмена")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
