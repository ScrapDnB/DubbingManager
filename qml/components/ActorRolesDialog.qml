import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    required property var appBridge
    readonly property var rolesBackend: appBridge ? appBridge.roles : null
    required property color softRow
    required property color softAltRow
    required property color softMuted

    title: qsTr("Роли: ") + (rolesBackend ? rolesBackend.actorStatsTitle : "")
    modal: true
    standardButtons: Dialog.Close
    width: boundedWidth(520, 36)
    height: boundedHeight(460, 36)

    function openFor(actorId) {
        rolesBackend.prepareActorStats(actorId)
        open()
    }

    content: ListView {
        id: statsView
        anchors.fill: parent
        clip: true
        model: dialog.rolesBackend
            ? dialog.rolesBackend.actorStatsModel : null
        delegate: Rectangle {
            required property int index
            required property string name
            required property int rings
            required property int words
            width: statsView.width
            height: 36
            color: index % 2 === 0 ? dialog.softRow : dialog.softAltRow
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                Label { text: name; Layout.fillWidth: true }
                Label { text: rings + " кол."; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                Label { text: words + " сл."; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
            }
        }
        Label {
            anchors.centerIn: parent
            visible: statsView.count === 0
            text: qsTr("У актёра пока нет ролей")
            color: dialog.softMuted
        }
    }
}
