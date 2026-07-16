import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var backend: appBridge ? appBridge.converter : null

    modal: true
    title: qsTr("Предпросмотр: ") + (backend ? backend.previewTitle : "")
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
            SplitView.preferredWidth: 340
            SplitView.minimumWidth: 280
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

    footer: DialogButtonBox {
        anchors.fill: parent
        Button {
            text: qsTr("Отмена")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: {
                dialog.decisionMade = true
                if (dialog.backend) dialog.backend.cancelPreview()
                dialog.close()
            }
        }
        Button {
            text: qsTr("Экспортировать все")
            highlighted: true
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                dialog.decisionMade = true
                if (dialog.backend) dialog.backend.continueAfterPreview()
                dialog.close()
            }
        }
    }
}
