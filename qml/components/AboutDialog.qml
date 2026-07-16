pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softMuted
    readonly property var updates: appBridge.updates

    modal: true
    title: qsTr("О программе")
    width: boundedWidth(520, 32)
    height: boundedHeight(460, 40)
    standardButtons: Dialog.NoButton

    NativeDialogWindow {
        id: installConfirmation
        ownerWindow: dialog
        modal: true
        title: dialog.updates.forceInstall
            ? qsTr("Переустановить текущую версию?")
            : qsTr("Установить обновление?")
        width: boundedWidth(430, 32)
        standardButtons: Dialog.Yes | Dialog.No
        content: Label {
            anchors.fill: parent
            text: dialog.updates.sourceCheckout
                ? qsTr("Программа выполнит git pull --ff-only. Рабочая копия должна быть без несохранённых изменений.")
                : qsTr("Обновление будет скачано, после чего программа закроется, заменит файлы внешним установщиком и запустится снова.")
            wrapMode: Text.WordWrap
        }
        onAccepted: dialog.updates.install()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: qsTr("Dubbing Manager")
            font.pixelSize: 24
            font.bold: true
            Layout.fillWidth: true
        }
        Label {
            text: qsTr("Управление проектами дубляжа и озвучивания")
            color: dialog.softMuted
            Layout.fillWidth: true
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 18
            rowSpacing: 7

            Label { text: qsTr("Версия:"); color: dialog.softMuted }
            Label { text: dialog.updates.appVersion }
            Label { text: qsTr("Python:"); color: dialog.softMuted }
            Label { text: dialog.updates.pythonVersion }
            Label { text: qsTr("PySide:"); color: dialog.softMuted }
            Label { text: dialog.updates.pysideVersion }
            Label { text: qsTr("Qt:"); color: dialog.softMuted }
            Label { text: dialog.updates.qtVersion }
            Label { text: qsTr("Исходный код:"); color: dialog.softMuted }
            Label {
                text: qsTr("<a href='") + dialog.updates.githubUrl
                    + "'>ScrapDnB/DubbingManager</a>"
                textFormat: Text.RichText
                onLinkActivated: function(_link) { dialog.updates.openGithub() }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: palette.mid
            opacity: 0.45
        }

        Label {
            text: qsTr("Обновления")
            font.bold: true
            Layout.fillWidth: true
        }
        Label {
            text: dialog.updates.status
            color: dialog.softMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        ProgressBar {
            visible: dialog.updates.busy
            indeterminate: dialog.updates.progressTotal <= 0
            from: 0
            to: Math.max(1, dialog.updates.progressTotal)
            value: dialog.updates.progress
            Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            Button {
                text: dialog.updates.busy
                    ? qsTr("Проверяю...") : qsTr("Проверить обновления")
                enabled: !dialog.updates.busy
                onClicked: dialog.updates.check(false)
            }
            Button {
                text: dialog.updates.updateAvailable
                    ? qsTr("Установить ") + dialog.updates.latestVersion
                    : qsTr("Переустановить текущую")
                visible: dialog.updates.checked
                enabled: !dialog.updates.busy
                onClicked: {
                    if (dialog.updates.updateAvailable
                            || dialog.updates.forceInstall) {
                        installConfirmation.open()
                    } else {
                        dialog.updates.check(true)
                    }
                }
            }
            Button {
                text: qsTr("Страница релиза")
                visible: dialog.updates.checked
                enabled: !dialog.updates.busy
                onClicked: dialog.updates.openReleasePage()
            }
            Item { Layout.fillWidth: true }
            Button {
                text: qsTr("Отмена")
                visible: dialog.updates.busy
                onClicked: dialog.updates.cancel()
            }
        }

        Label {
            text: qsTr("© 2026 Юрий Романов")
            color: dialog.softMuted
            Layout.fillWidth: true
        }
        Item { Layout.fillHeight: true }
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        Button { text: qsTr("Закрыть"); onClicked: dialog.close() }
    }
}
