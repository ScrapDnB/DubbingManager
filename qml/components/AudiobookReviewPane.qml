pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var backend
    required property color softMuted

    ColumnLayout {
        anchors.fill: parent
        spacing: 7

        Label { text: pane.backend.reviewSummary; color: pane.softMuted }
        TextField {
            Layout.fillWidth: true
            placeholderText: qsTr("Поиск по тексту, главе, роли или алиасу")
            onTextChanged: pane.backend.setReviewSearch(text)
        }
        PlatformComboBox {
            id: reviewFilterCombo
            Layout.fillWidth: true
            textRole: "label"
            valueRole: "value"
            model: [
                {label: qsTr("Требуют проверки"), value: "issues"},
                {label: qsTr("Прямая речь без роли"), value: "unmarked_dialogue"},
                {label: qsTr("Роли без актёра"), value: "unassigned"},
                {label: qsTr("Все фрагменты"), value: "all"},
                {label: qsTr("Пропущенные"), value: "ignored"}
            ]
            onActivated: pane.backend.setReviewFilter(currentValue)
            Component.onCompleted: currentIndex = Math.max(
                0, indexOfValue(pane.backend.reviewFilter)
            )
        }

        Connections {
            target: pane.backend
            function onReviewChanged() {
                var index = reviewFilterCombo.indexOfValue(
                    pane.backend.reviewFilter
                )
                if (index >= 0 && index !== reviewFilterCombo.currentIndex)
                    reviewFilterCombo.currentIndex = index
            }
        }

        PersistentListView {
            id: reviewItemsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: pane.backend.reviewModel
            clip: true
            spacing: 3
            delegate: ItemDelegate {
                id: reviewRow
                required property string itemId
                required property string chapter
                required property string character
                required property string snippet
                required property string kindLabel
                required property bool issue
                required property bool ignored
                width: reviewItemsView.viewportWidth
                height: Math.max(72, reviewContent.implicitHeight + 10)
                onClicked: pane.backend.openReviewItem(itemId)
                contentItem: ColumnLayout {
                    id: reviewContent
                    spacing: 2
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: reviewRow.chapter
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: reviewRow.kindLabel
                            color: reviewRow.issue ? "#b06020" : pane.softMuted
                        }
                        ToolButton {
                            id: ignoreButton
                            visible: reviewRow.issue && !reviewRow.ignored
                            text: qsTr("×")
                            onClicked: pane.backend.ignoreReviewItem(
                                reviewRow.itemId
                            )
                            PlatformToolTip {
                                target: ignoreButton
                                text: qsTr("Пропустить проверку")
                            }
                        }
                    }
                    Label {
                        text: reviewRow.character
                        color: pane.softMuted
                    }
                    Label {
                        text: reviewRow.snippet
                        Layout.fillWidth: true
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        wrapMode: Text.Wrap
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: parent.count === 0
                text: qsTr("Нет подходящих фрагментов")
                color: pane.softMuted
            }
        }

        AdaptiveButton {
            visible: pane.backend.reviewFilter === "ignored"
            text: qsTr("Вернуть все пропущенные")
            Layout.fillWidth: true
            onClicked: pane.backend.resetIgnoredReviewItems()
        }
    }
}
