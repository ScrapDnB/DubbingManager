import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var rolesBackend: appBridge ? appBridge.roles : null
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted

    property var selectedRoles: ({})

    modal: true
    title: qsTr("Роли проекта")
    standardButtons: Dialog.Close
    width: boundedWidth(860, 36)
    height: boundedHeight(600, 36)

    function openForProject() {
        selectedRoles = ({})
        roleSearch.text = ""
        rolesBackend.refresh()
        open()
    }

    function toggleRole(role, checked) {
        var next = Object.assign({}, selectedRoles)
        if (checked) next[role] = true
        else delete next[role]
        selectedRoles = next
    }

    function selectedRoleNames() {
        return Object.keys(selectedRoles)
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: roleSearch
                Layout.fillWidth: true
                placeholderText: qsTr("Поиск по роли или актёру")
                selectByMouse: true
            }
            Button {
                text: qsTr("Выбрать видимые")
                onClicked: {
                    var next = Object.assign({}, dialog.selectedRoles)
                    var query = roleSearch.text.trim().toLowerCase()
                    for (var i = 0; i < rolesView.count; ++i) {
                        var row = dialog.rolesBackend.model.get(i)
                        var haystack = (row.name + " " + row.actorName).toLowerCase()
                        if (!query || haystack.indexOf(query) >= 0)
                            next[row.name] = true
                    }
                    dialog.selectedRoles = next
                }
            }
            Button {
                text: qsTr("Снять выбор")
                enabled: dialog.selectedRoleNames().length > 0
                onClicked: dialog.selectedRoles = ({})
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: dialog.softHeader
            border.color: dialog.softBorder
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8
                Label { text: qsTr(""); Layout.preferredWidth: 24 }
                Label { text: qsTr("Роль"); font.bold: true; Layout.fillWidth: true }
                Label { text: qsTr("Текущий актёр"); font.bold: true; Layout.preferredWidth: 180 }
                Label { text: qsTr("Серии"); font.bold: true; Layout.preferredWidth: 180 }
            }
        }

        ListView {
            id: rolesView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.rolesBackend ? dialog.rolesBackend.model : null

            delegate: Rectangle {
                id: roleRow
                required property int index
                required property string name
                required property string actorName
                required property string episodes
                property bool matches: {
                    var query = roleSearch.text.trim().toLowerCase()
                    return !query || (name + " " + actorName).toLowerCase().indexOf(query) >= 0
                }
                visible: matches
                width: rolesView.width
                height: visible ? 34 : 0
                color: rowHover.hovered ? dialog.softHover
                    : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow)

                HoverHandler { id: rowHover }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8
                    CheckBox {
                        Layout.preferredWidth: 24
                        checked: dialog.selectedRoles[roleRow.name] === true
                        onToggled: dialog.toggleRole(roleRow.name, checked)
                    }
                    Label { text: roleRow.name; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: roleRow.actorName; Layout.preferredWidth: 180; elide: Text.ElideRight }
                    Label { text: roleRow.episodes; Layout.preferredWidth: 180; elide: Text.ElideMiddle }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: rolesView.count === 0
                text: qsTr("В проекте пока нет ролей")
                color: dialog.softMuted
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Назначить:") }
            PlatformComboBox {
                id: roleActorCombo
                Layout.preferredWidth: 220
                model: dialog.rolesBackend
                    ? dialog.rolesBackend.actorModel : null
                textRole: "name"
                valueRole: "id"
            }
            Button {
                text: qsTr("Применить")
                enabled: dialog.selectedRoleNames().length > 0
                onClicked: {
                    dialog.rolesBackend.assign(
                        dialog.selectedRoleNames(),
                        roleActorCombo.currentValue
                    )
                    dialog.selectedRoles = ({})
                }
            }
            Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignRight
                text: qsTr("Выбрано: ") + dialog.selectedRoleNames().length
                color: dialog.softMuted
            }
        }
    }
}
