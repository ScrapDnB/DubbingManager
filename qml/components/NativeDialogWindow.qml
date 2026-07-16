import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: window

    property bool modal: true
    property int standardButtons: Dialog.NoButton
    property var ownerWindow
    property alias content: contentHost.data
    property alias footer: customFooter.data

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
            ? customFooter.children[0].implicitHeight
            : standardFooter.visible
                ? standardFooter.implicitHeight
                : 0

        Item {
            id: customFooter
            anchors.fill: parent
        }

        DialogButtonBox {
            id: standardFooter
            anchors.fill: parent
            visible: customFooter.children.length === 0
                && window.standardButtons !== Dialog.NoButton
            standardButtons: window.standardButtons
            onAccepted: window.accept()
            onRejected: window.reject()
        }
    }
}
