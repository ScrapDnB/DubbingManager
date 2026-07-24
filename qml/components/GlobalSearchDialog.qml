import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    objectName: "globalSearchDialog"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    readonly property var reportsBackend: appBridge ? appBridge.reports : null
    property bool hasSearched: false
    property color selectedRow: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22
    )

    SystemPalette { id: palette; colorGroup: SystemPalette.Active }

    function sortTitle(label, key) {
        if (!reportsBackend || reportsBackend.searchSortKey !== key)
            return label
        return label + (reportsBackend.searchSortAscending ? " ↑" : " ↓")
    }

    modal: true
    macOSDocumentWindow: true
    title: qsTr("Глобальный поиск по проекту")
    standardButtons: macOSStyle ? Dialog.NoButton : Dialog.Close
    width: boundedWidth(920, 40)
    height: boundedHeight(620, 40)

    onOpened: {
        searchField.forceActiveFocus()
        searchField.selectAll()
    }

    function runSearch() {
        if (dialog.reportsBackend) {
            dialog.reportsBackend.search(searchField.text)
            dialog.hasSearched = true
            resultsView.currentIndex = resultsView.count > 0 ? 0 : -1
        }
    }

    function openCurrentResult() {
        if (!reportsBackend || resultsView.currentIndex < 0)
            return
        var row = reportsBackend.searchModel.get(resultsView.currentIndex)
        if (row.episode) {
            reportsBackend.openResult(row.episode, row.character)
            close()
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: qsTr("Текст или имя персонажа")
                selectByMouse: true
                onTextEdited: dialog.hasSearched = false
                onAccepted: dialog.runSearch()
            }

            AdaptiveButton {
                text: qsTr("Найти")
                enabled: searchField.text.trim().length > 0
                onClicked: dialog.runSearch()
            }
        }

        Label {
            Layout.fillWidth: true
            text: dialog.hasSearched && dialog.reportsBackend
                && dialog.reportsBackend.searchResultCount > 0
                ? "Найдено: " + dialog.reportsBackend.searchResultCount
                : ""
            color: dialog.softMuted
        }

        TableHeaderSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: dialog.tableHeaderHeight
            softHeader: dialog.softHeader
            softBorder: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 10

                TableHeaderButton { text: dialog.sortTitle(qsTr("Серия"), "episode"); Layout.preferredWidth: 64; onClicked: dialog.reportsBackend.setSearchSort("episode") }
                TableHeaderButton { text: dialog.sortTitle(qsTr("Таймкод"), "time"); Layout.preferredWidth: 90; onClicked: dialog.reportsBackend.setSearchSort("time") }
                TableHeaderButton { text: dialog.sortTitle(qsTr("Персонаж"), "character"); Layout.preferredWidth: 150; onClicked: dialog.reportsBackend.setSearchSort("character") }
                TableHeaderButton { text: dialog.sortTitle(qsTr("Текст"), "text"); Layout.fillWidth: true; onClicked: dialog.reportsBackend.setSearchSort("text") }
            }
        }

        PersistentListView {
            id: resultsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            model: dialog.reportsBackend
                ? dialog.reportsBackend.searchModel : null
            Keys.onReturnPressed: dialog.openCurrentResult()
            Keys.onEnterPressed: dialog.openCurrentResult()

            delegate: Rectangle {
                id: resultRow
                width: resultsView.viewportWidth
                height: dialog.regularRowHeight
                color: resultsView.currentIndex === index
                    ? dialog.selectedRow : resultHover.hovered
                    ? dialog.softHover
                    : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow)

                HoverHandler { id: resultHover }

                TapHandler {
                    onTapped: {
                        resultsView.currentIndex = index
                        resultsView.forceActiveFocus()
                    }
                    onDoubleTapped: {
                        dialog.reportsBackend.openResult(
                            model.episode,
                            model.character
                        )
                        dialog.close()
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 10

                    Label { text: model.episode; Layout.preferredWidth: 64; elide: Text.ElideRight }
                    Label { text: model.time; Layout.preferredWidth: 90; elide: Text.ElideRight }
                    Label { text: model.character; Layout.preferredWidth: 150; elide: Text.ElideRight }
                    Label { text: model.text; Layout.fillWidth: true; elide: Text.ElideRight }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: resultsView.count === 0
                text: dialog.hasSearched
                    ? "Совпадений нет"
                    : "Введите запрос и нажмите «Найти»"
                color: dialog.softMuted
            }
        }

        Shortcut {
            sequences: [StandardKey.Copy]
            enabled: resultsView.activeFocus && resultsView.currentIndex >= 0
            onActivated: dialog.reportsBackend.copySearchResult(
                resultsView.currentIndex
            )
        }

    }
}
