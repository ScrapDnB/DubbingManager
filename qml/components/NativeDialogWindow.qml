pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: window

    property bool modal: true
    property int standardButtons: Dialog.NoButton
    property var ownerWindow
    property alias content: contentHost.data
    property alias footer: customFooter.data
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    readonly property int dialogControlHeight: Math.max(
        40, Math.ceil(dialogFontMetrics.height + 18)
    )

    signal opened()
    signal closed()
    signal accepted()
    signal rejected()

    visible: false
    transientParent: Qt.platform.os === "osx" ? null : ownerWindow
    flags: Qt.Window
    modality: modal && Qt.platform.os !== "osx"
        ? Qt.ApplicationModal
        : Qt.NonModal
    color: palette.window

    function boundedWidth(preferredWidth, margin) {
        if (!ownerWindow) {
            return preferredWidth
        }
        return Math.min(preferredWidth, Math.max(300, ownerWindow.width - margin))
    }

    function boundedHeight(preferredHeight, margin) {
        if (!ownerWindow) {
            return preferredHeight
        }
        return Math.min(preferredHeight, Math.max(220, ownerWindow.height - margin))
    }

    function centerOnParent() {
        if (!ownerWindow) {
            return
        }
        x = ownerWindow.x + Math.round((ownerWindow.width - width) / 2)
        y = ownerWindow.y + Math.round((ownerWindow.height - height) / 2)
    }

    function open() {
        if (visible) {
            raise()
            requestActivate()
            return
        }
        centerOnParent()
        show()
        requestActivate()
        opened()
    }

    function accept() {
        accepted()
        close()
    }

    function reject() {
        rejected()
        close()
    }

    onClosing: closed()

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    FontMetrics {
        id: dialogFontMetrics
        font: Application.font
    }

    Item {
        id: contentHost
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: footerArea.top
        anchors.margins: 12
    }

    Item {
        id: footerArea
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.bottomMargin: 10
        height: customFooter.children.length > 0
            ? Math.max(
                customFooter.children[0].implicitHeight,
                window.windowsStyle ? window.dialogControlHeight : 0
            )
            : standardFooterHost.visible
                ? (window.windowsStyle ? window.dialogControlHeight
                    : standardFooterHost.item
                        ? standardFooterHost.item.implicitHeight : 0)
                : 0

        Item {
            id: customFooter
            anchors.fill: parent
        }

        Loader {
            id: standardFooterHost
            anchors.fill: parent
            visible: customFooter.children.length === 0
                && window.standardButtons !== Dialog.NoButton
            sourceComponent: window.windowsStyle
                ? windowsStandardFooter : nativeStandardFooter
        }

        Component {
            id: nativeStandardFooter

            DialogButtonBox {
                anchors.fill: parent
                standardButtons: window.standardButtons
                onAccepted: window.accept()
                onRejected: window.reject()
            }
        }

        Component {
            id: windowsStandardFooter

            RowLayout {
                anchors.fill: parent
                implicitHeight: window.dialogControlHeight
                spacing: 8

                Item { Layout.fillWidth: true }

                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.Cancel) !== 0
                    text: qsTr("Отмена")
                    Layout.preferredWidth: 100
                    onClicked: window.reject()
                }
                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.No) !== 0
                    text: qsTr("Нет")
                    Layout.preferredWidth: 100
                    onClicked: window.reject()
                }
                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.Close) !== 0
                    text: qsTr("Закрыть")
                    Layout.preferredWidth: 100
                    onClicked: window.reject()
                }
                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.Ok) !== 0
                    text: qsTr("ОК")
                    highlighted: true
                    Layout.preferredWidth: 100
                    onClicked: window.accept()
                }
                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.Save) !== 0
                    text: qsTr("Сохранить")
                    highlighted: true
                    Layout.preferredWidth: 110
                    onClicked: window.accept()
                }
                AdaptiveButton {
                    visible: (window.standardButtons & Dialog.Yes) !== 0
                    text: qsTr("Да")
                    highlighted: true
                    Layout.preferredWidth: 100
                    onClicked: window.accept()
                }
            }
        }
    }
}
