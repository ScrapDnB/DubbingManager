pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var backend
    required property var editorView
    required property color softMuted
    required property bool macOSStyle

    ColumnLayout {
        anchors.fill: parent
        spacing: 7

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: qsTr("Разметка ролей")
                font.bold: true
                Layout.fillWidth: true
            }
            Label { text: qsTr("Клавиши 1–9"); color: pane.softMuted }
        }

        PersistentScrollView {
            id: slotsScroll
            Layout.fillWidth: true
            Layout.preferredHeight: 330
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: slotsScroll.availableWidth
                spacing: 5
                Repeater {
                    model: pane.backend.slotsModel
                    delegate: RowLayout {
                        id: slotRow
                        required property int slotIndex
                        required property string character
                        required property int actorIndex
                        Layout.fillWidth: true
                        spacing: 5

                        Label {
                            text: String(slotRow.slotIndex + 1)
                            horizontalAlignment: Text.AlignHCenter
                            Layout.preferredWidth: 18
                        }
                        PlatformComboBox {
                            id: characterBox
                            editable: true
                            model: pane.backend.characterNames
                            Component.onCompleted: currentIndex = Math.max(
                                0, find(slotRow.character)
                            )
                            Layout.fillWidth: true
                            Layout.preferredWidth: 120
                            onAccepted: {
                                var actor = pane.backend.actorsModel.get(
                                    actorBox.currentIndex
                                )
                                pane.backend.setSlot(
                                    slotRow.slotIndex,
                                    editText,
                                    actor.actorId || ""
                                )
                            }
                        }
                        PlatformComboBox {
                            id: actorBox
                            model: pane.backend.actorsModel
                            textRole: "name"
                            Component.onCompleted: currentIndex = slotRow.actorIndex
                            Layout.fillWidth: true
                            Layout.preferredWidth: 120
                            onActivated: {
                                var actor = pane.backend.actorsModel.get(currentIndex)
                                var character = characterBox.editText
                                var actorId = actor.actorId || ""
                                var color = pane.backend.actorColor(actorId)
                                pane.editorView.runJavaScript(
                                    "window.dmEditor.recolor("
                                    + JSON.stringify(character) + ","
                                    + JSON.stringify(actorId) + ","
                                    + JSON.stringify(color) + ")"
                                )
                                pane.backend.setSlot(
                                    slotRow.slotIndex, character, actorId
                                )
                            }
                        }
                        ToolButton {
                            id: applyMarkupButton
                            text: qsTr("✓")
                            enabled: characterBox.editText.trim().length > 0
                            PlatformToolTip {
                                target: applyMarkupButton
                                text: qsTr("Разметить выделение")
                            }
                            onClicked: {
                                var actor = pane.backend.actorsModel.get(
                                    actorBox.currentIndex
                                )
                                var character = characterBox.editText
                                var actorId = actor.actorId || ""
                                var color = pane.backend.actorColor(actorId)
                                pane.editorView.runJavaScript(
                                    "window.dmEditor.applyMarkup("
                                    + JSON.stringify(character) + ","
                                    + JSON.stringify(actorId) + ","
                                    + JSON.stringify(color) + ")"
                                )
                                pane.backend.setSlot(
                                    slotRow.slotIndex, character, actorId
                                )
                            }
                        }
                    }
                }
            }
        }

        AdaptiveButton {
            text: qsTr("Снять разметку с выделения")
            Layout.fillWidth: true
            onClicked: pane.editorView.runJavaScript(
                "window.dmEditor.clearMarkup()"
            )
        }

        ToolSeparator { orientation: Qt.Horizontal; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("В главе"); font.bold: true; Layout.fillWidth: true }
            Label { text: pane.backend.statsSummary; color: pane.softMuted }
        }
        PersistentListView {
            id: markedItemsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: pane.backend.markedModel
            clip: true
            delegate: ItemDelegate {
                id: markedRow
                required property string character
                required property string summary
                width: markedItemsView.viewportWidth
                height: pane.macOSStyle ? 28 : 32
                contentItem: RowLayout {
                    Label {
                        text: markedRow.character
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Label { text: markedRow.summary; color: pane.softMuted }
                }
            }
        }
    }
}
