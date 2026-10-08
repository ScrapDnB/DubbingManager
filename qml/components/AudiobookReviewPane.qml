pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var backend
    required property color softMuted
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        Label { text: qsTr("Проверка книги"); font.bold: true }
        Label { text: pane.backend.reviewSummary; color: pane.softMuted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        TextField {
            objectName: "audiobookReviewSearch"
            Layout.fillWidth: true
            placeholderText: qsTr("Текст, глава или роль")
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
            Component.onCompleted: currentIndex = Math.max(0, indexOfValue(pane.backend.reviewFilter))
        }
        PersistentListView {
            id: reviewItemsView
            objectName: "audiobookReviewItems"
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: pane.backend.reviewModel
            clip: true
            spacing: 2
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
                height: Math.max(98, reviewContent.implicitHeight + 18)
                highlighted: pane.backend.selectedReviewId === itemId
                onClicked: pane.backend.openReviewItem(itemId)
                contentItem: ColumnLayout {
                    id: reviewContent
                    spacing: 5
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { implicitWidth: 6; implicitHeight: 6; radius: 3; color: reviewRow.issue ? "#c18a32" : pane.softMuted }
                        Label { text: reviewRow.kindLabel; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Label { text: reviewRow.chapter + " · " + reviewRow.character; color: pane.softMuted; font.pixelSize: pane.macOSStyle ? 11 : 12; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: reviewRow.snippet; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.Wrap }
                }
            }
            ColumnLayout {
                anchors.centerIn: parent
                width: Math.max(100, parent.width - 30)
                visible: reviewItemsView.count === 0
                Label { text: pane.backend.reviewCount === 0 ? qsTr("Замечаний нет") : qsTr("Ничего не найдено"); font.bold: true; Layout.alignment: Qt.AlignHCenter }
                Label { text: qsTr("Измените фильтр или поисковый запрос"); color: pane.softMuted; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
            }
        }
        AdaptiveButton {
            visible: pane.backend.reviewFilter === "ignored"
            text: qsTr("Вернуть пропущенные")
            onClicked: pane.backend.resetIgnoredReviewItems()
        }
        Label { text: qsTr("Готовы %1 из %2 глав").arg(pane.backend.readyChapters).arg(pane.backend.chapterTitles.length); color: pane.softMuted }
    }
}
