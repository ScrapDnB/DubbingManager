import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var backend: appBridge ? appBridge.converter : null

    modal: true
    title: backend && backend.previewSettingsMode
        ? qsTr("Настройки быстрого конвертера")
        : qsTr("Предпросмотр: ") + (backend ? backend.previewTitle : "")
    width: boundedWidth(1080, 32)
    height: boundedHeight(720, 32)
    property bool decisionMade: false

    function openPreview() {
        decisionMade = false
        open()
        preview.loadHtml(backend ? backend.previewHtml : "")
    }

    onClosed: {
        if (!decisionMade && backend)
            backend.cancelPreview()
    }

    Connections {
        target: dialog.backend
        function onPreviewChanged() {
            preview.loadHtml(dialog.backend ? dialog.backend.previewHtml : "")
        }
    }

    content: SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        MontageSettingsPane {
            SplitView.preferredWidth: 380
            SplitView.minimumWidth: 320
            configuration: dialog.backend ? dialog.backend.previewConfig : ({})
            showFormatSettings: false
            showOpenAfterExport: false
            showEditableHtml: false
            onConfigEdited: function(config) {
                if (!dialog.backend)
                    return
                for (var key in config) {
                    if (config[key] !== dialog.backend.previewConfig[key])
                        dialog.backend.setPreviewOption(key, config[key])
                }
            }
        }

        WebEngineView {
            id: preview
            SplitView.fillWidth: true
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        spacing: 8

        CheckBox {
            text: qsTr("Построчный экспорт")
            checked: dialog.backend ? dialog.backend.lineByLine : false
            onToggled: if (dialog.backend) {
                dialog.backend.setLineByLine(checked)
            }
            Accessible.description: qsTr("Не объединять соседние строки")
        }

        Item { Layout.fillWidth: true }

        AdaptiveButton {
            text: qsTr("Отмена")
            Layout.preferredWidth: 120
            onClicked: {
                dialog.decisionMade = true
                if (dialog.backend) dialog.backend.cancelPreview()
                dialog.close()
            }
        }
        AdaptiveButton {
            text: dialog.backend && dialog.backend.previewSettingsMode
                ? qsTr("Сохранить настройки")
                : qsTr("Экспортировать все")
            highlighted: true
            Layout.preferredWidth: 180
            onClicked: {
                if (!dialog.backend)
                    return
                if (dialog.backend.previewSettingsMode) {
                    if (dialog.backend.savePreviewSettings()) {
                        dialog.decisionMade = true
                        dialog.close()
                    }
                } else {
                    dialog.decisionMade = true
                    dialog.backend.continueAfterPreview()
                    dialog.close()
                }
            }
        }
    }
}
