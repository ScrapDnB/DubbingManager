pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var backend
    required property var editorView
    required property var appBridge
    required property var ownerWindow
    required property color softMuted
    required property bool macOSStyle
    property int selectedSlot: -1
    implicitHeight: contentColumn.implicitHeight
    signal dictionaryRequested(string word)

    function callEditor(method, args) {
        editorView.runJavaScript("window.dmEditor && window.dmEditor." + method + "(" + (args || []).map(JSON.stringify).join(",") + ")")
    }
    function editRole(index, character) {
        var slot = backend.slotPayload(index)
        roleEditor.slotIndex = index
        roleName.editText = character || slot.character || ""
        roleActor.currentIndex = character && index < 0 ? Math.max(0, roleActor.indexOfValue(backend.actorForCharacter(character))) : Math.max(0, slot.actorIndex || 0)
        roleEditor.open()
        roleName.forceActiveFocus()
    }
    function syncSelection() {
        var name = backend.selection.character || "Автор"
        selectedRole.currentIndex = Math.max(0, selectedRole.find(name))
        var actorId = backend.actorForCharacter(name)
        selectionActor.currentIndex = Math.max(0, selectionActor.indexOfValue(actorId))
    }

    NativeDialogWindow {
        id: roleEditor
        ownerWindow: pane.ownerWindow
        title: qsTr("Роль и актёр")
        width: 430
        height: 230
        property int slotIndex: -1
        content: ColumnLayout {
            anchors.fill: parent
            spacing: 10
            Label { text: roleEditor.slotIndex >= 0 ? qsTr("Роль · клавиша %1").arg(roleEditor.slotIndex + 1) : qsTr("Роль без быстрой клавиши"); font.bold: true }
            PlatformComboBox {
                id: roleName
                objectName: "audiobookRoleName"
                editable: true
                model: pane.backend.characterNames
                Layout.fillWidth: true
                Accessible.name: qsTr("Название роли")
            }
            Label { text: qsTr("Актёр для этой роли во всей книге"); color: pane.softMuted }
            PlatformComboBox {
                id: roleActor
                model: pane.backend.actorsModel
                textRole: "name"
                valueRole: "actorId"
                Layout.fillWidth: true
                Accessible.name: qsTr("Актёр роли")
            }
            Item { Layout.fillHeight: true }
        }
        footer: RowLayout {
            anchors.fill: parent
            Item { Layout.fillWidth: true }
            AdaptiveButton { text: qsTr("Отмена"); onClicked: roleEditor.close() }
            AdaptiveButton {
                text: qsTr("Сохранить")
                highlighted: true
                enabled: roleName.editText.trim().length > 0
                onClicked: if (pane.backend.configureRole(roleEditor.slotIndex, roleName.editText, roleActor.currentValue || "")) roleEditor.close()
            }
        }
    }

    Connections {
        target: pane.backend
        function onSelectionChanged() { pane.syncSelection() }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Разметка ролей"); font.bold: true; Layout.fillWidth: true }
            Label { text: qsTr("1–9"); color: pane.softMuted }
        }
        Label {
            text: qsTr("Выделите текст и выберите роль")
            color: pane.softMuted
            font.pixelSize: pane.macOSStyle ? 11 : 12
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        PersistentListView {
            id: rolesView
            objectName: "audiobookRolesView"
            model: pane.backend.rolesModel
            clip: true
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(300, Math.max(54, count * (pane.macOSStyle ? 52 : 58)))
            delegate: ItemDelegate {
                id: roleRow
                required property int slotIndex
                required property string character
                required property string actorName
                required property string actorId
                required property string color
                width: rolesView.viewportWidth
                height: pane.macOSStyle ? 52 : 58
                highlighted: slotIndex >= 0 && pane.selectedSlot === slotIndex
                Accessible.name: character + ", " + actorName + (slotIndex >= 0 ? qsTr(", клавиша ") + (slotIndex + 1) : "")
                onClicked: {
                    pane.selectedSlot = slotIndex
                    if (slotIndex >= 0) pane.callEditor("applySlot", [slotIndex])
                    else pane.callEditor("applyMarkup", [character, actorId, color])
                }
                contentItem: RowLayout {
                    spacing: 10
                    Rectangle { implicitWidth: 12; implicitHeight: 12; radius: 6; color: roleRow.color; Layout.alignment: Qt.AlignVCenter }
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: roleRow.character; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: roleRow.actorName; color: pane.softMuted; font.pixelSize: pane.macOSStyle ? 11 : 12; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Label {
                        text: roleRow.slotIndex >= 0 ? String(roleRow.slotIndex + 1) : ""
                        color: pane.softMuted
                        horizontalAlignment: Text.AlignHCenter
                        Layout.preferredWidth: 20
                    }
                    RowAccessoryButton {
                        iconSource: "../icons/ellipsis.svg"
                        toolTipText: qsTr("Настроить роль и актёра")
                        onClicked: pane.editRole(roleRow.slotIndex, roleRow.character)
                    }
                }
                Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 1; color: roleRow.palette.mid; opacity: 0.18 }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            RowAccessoryButton {
                iconSource: "../icons/plus.svg"
                toolTipText: qsTr("Добавить роль")
                onClicked: pane.editRole(pane.backend.nextSlot, "")
            }
            RowAccessoryButton {
                iconSource: "../icons/x.svg"
                toolTipText: qsTr("Убрать выбранную роль из быстрых клавиш")
                enabled: pane.selectedSlot >= 0
                onClicked: { pane.backend.removeRoleShortcut(pane.selectedSlot); pane.selectedSlot = -1 }
            }
            Item { Layout.fillWidth: true }
        }
        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
        Label { text: qsTr("Выделение"); font.bold: true }
        Label {
            text: pane.backend.selection.words > 0 ? qsTr("%1 слов").arg(pane.backend.selection.words) : qsTr("Выделите фрагмент в тексте")
            color: pane.softMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        GridLayout {
            columns: 2
            Layout.fillWidth: true
            columnSpacing: 8
            rowSpacing: 8
            Label { text: qsTr("Роль:"); color: pane.softMuted }
            PlatformComboBox {
                id: selectedRole
                objectName: "audiobookSelectionRole"
                model: pane.backend.characterNames
                Layout.fillWidth: true
                Accessible.name: qsTr("Роль выделенного фрагмента")
                onActivated: selectionActor.currentIndex = Math.max(0, selectionActor.indexOfValue(pane.backend.actorForCharacter(currentText)))
            }
            Label { text: qsTr("Актёр:"); color: pane.softMuted }
            PlatformComboBox {
                id: selectionActor
                model: pane.backend.actorsModel
                textRole: "name"
                valueRole: "actorId"
                Layout.fillWidth: true
                Accessible.name: qsTr("Актёр выделенного фрагмента")
            }
        }
        RowLayout {
            Layout.fillWidth: true
            AdaptiveButton {
                text: qsTr("Снять разметку")
                enabled: (pane.backend.selection.words || 0) > 0
                onClicked: pane.callEditor("clearMarkup")
            }
            Item { Layout.fillWidth: true }
            AdaptiveButton {
                text: qsTr("Применить")
                enabled: (pane.backend.selection.words || 0) > 0 && selectedRole.currentText.length > 0
                onClicked: pane.callEditor("applyMarkup", [selectedRole.currentText, selectionActor.currentValue || "", pane.backend.actorColor(selectionActor.currentValue || "")])
            }
        }
        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
        RowLayout {
            Label { text: qsTr("Произношения"); font.bold: true; Layout.fillWidth: true }
            RowAccessoryButton {
                iconSource: "../icons/plus.svg"
                toolTipText: qsTr("Добавить произношение")
                onClicked: pane.dictionaryRequested(pane.backend.selection.text || "")
            }
        }
        Repeater {
            model: pane.backend.pronunciations.slice(0, 3)
            delegate: Label {
                required property var modelData
                text: modelData.pronunciation
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }
        Label {
            visible: pane.backend.pronunciations.length === 0
            text: qsTr("Ударения и подсказки для диктора")
            color: pane.softMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
        AdaptiveButton { text: qsTr("Открыть словарь…"); flat: true; onClicked: pane.dictionaryRequested("") }
        Item { Layout.fillHeight: true }
    }
}
