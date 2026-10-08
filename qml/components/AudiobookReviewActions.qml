pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
    id: pane
    required property var backend
    required property color softMuted
    padding: 14
    background: Rectangle { color: pane.palette.window; Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: pane.palette.mid; opacity: 0.25 } }
    function sync() {
        var role = backend.selectedReview.character || "Автор"
        roleBox.currentIndex = Math.max(0, roleBox.find(role))
        actorBox.currentIndex = Math.max(0, actorBox.indexOfValue(backend.actorForCharacter(role)))
    }
    Connections { target: pane.backend; function onReviewChanged() { pane.sync() } }
    contentItem: ColumnLayout {
        spacing: 8
        Label { text: pane.backend.selectedReview.kindLabel || qsTr("Выберите замечание слева"); font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Роль:"); color: pane.softMuted }
            PlatformComboBox {
                id: roleBox
                editable: true
                model: pane.backend.characterNames
                Layout.fillWidth: true
                Accessible.name: qsTr("Роль для исправления замечания")
                onActivated: actorBox.currentIndex = Math.max(0, actorBox.indexOfValue(pane.backend.actorForCharacter(currentText)))
            }
            Label { text: qsTr("Актёр:"); color: pane.softMuted }
            PlatformComboBox { id: actorBox; model: pane.backend.actorsModel; textRole: "name"; valueRole: "actorId"; Layout.fillWidth: true; Accessible.name: qsTr("Актёр для исправления замечания") }
        }
        RowLayout {
            Layout.fillWidth: true
            AdaptiveButton {
                text: qsTr("Пропустить")
                enabled: Boolean(pane.backend.selectedReview.issue)
                onClicked: { pane.backend.ignoreReviewItem(pane.backend.selectedReviewId); pane.backend.openNextReviewItem() }
            }
            Item { Layout.fillWidth: true }
            AdaptiveButton {
                objectName: "audiobookResolveReview"
                text: qsTr("Применить и перейти дальше")
                highlighted: true
                enabled: pane.backend.selectedReviewId.length > 0 && roleBox.editText.trim().length > 0
                onClicked: pane.backend.resolveReviewItem(pane.backend.selectedReviewId, roleBox.editText, actorBox.currentValue || "")
            }
        }
    }
}
