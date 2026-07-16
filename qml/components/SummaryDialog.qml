import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    readonly property var reportsBackend: appBridge ? appBridge.reports : null
    property string targetEpisode: ""
    property color selectedRow: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22
    )

    SystemPalette { id: palette; colorGroup: SystemPalette.Active }

    function sortTitle(label, key) {
        if (!reportsBackend || reportsBackend.summarySortKey !== key)
            return label
        return label + (reportsBackend.summarySortAscending ? " ↑" : " ↓")
    }

    modal: true
    title: targetEpisode.length > 0
        ? "Отчёт: серия " + targetEpisode
        : "Сводный отчёт проекта"
    standardButtons: Dialog.Close
    width: boundedWidth(920, 40)
    height: boundedHeight(620, 40)

    ListModel {
        id: metricModel
        ListElement { label: "Кольца"; value: "rings" }
        ListElement { label: "Строчки"; value: "lines" }
        ListElement { label: "Слова"; value: "words" }
    }

    function openFor(episode) {
        targetEpisode = episode || ""
        reportsBackend.prepareSummary(targetEpisode)
        metricCombo.syncMetric()
        open()
    }

    FileDialog {
        id: exportDialog
        title: qsTr("Сохранить сводку проекта")
        fileMode: FileDialog.SaveFile
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        nameFilters: ["Excel workbook (*.xlsx)"]
        defaultSuffix: "xlsx"
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("exports", selectedFile.toString())
            dialog.reportsBackend.exportProjectSummaryXlsx(
                selectedFile.toString(),
                metricCombo.currentValue
            )
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: dialog.softHeader
            border.color: dialog.softBorder

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 10

                Label { text: qsTr(""); Layout.preferredWidth: 20 }
                ToolButton { text: dialog.sortTitle(qsTr("Актёр"), "actor"); font.bold: true; flat: true; padding: 0; Layout.preferredWidth: 190; onClicked: dialog.reportsBackend.setSummarySort("actor") }
                ToolButton { text: dialog.sortTitle(qsTr("Колец"), "rings"); font.bold: true; flat: true; padding: 0; Layout.preferredWidth: 60; onClicked: dialog.reportsBackend.setSummarySort("rings") }
                ToolButton { text: dialog.sortTitle(qsTr("Слов"), "words"); font.bold: true; flat: true; padding: 0; Layout.preferredWidth: 70; onClicked: dialog.reportsBackend.setSummarySort("words") }
                ToolButton { text: dialog.sortTitle(qsTr("Персонажи"), "roles"); font.bold: true; flat: true; padding: 0; Layout.fillWidth: true; onClicked: dialog.reportsBackend.setSummarySort("roles") }
            }
        }

        ListView {
            id: summaryView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            model: dialog.reportsBackend
                ? dialog.reportsBackend.summaryModel : null

            delegate: Rectangle {
                width: summaryView.width
                height: Math.max(38, rolesLabel.implicitHeight + 12)
                color: summaryView.currentIndex === index
                    ? dialog.selectedRow
                    : (index % 2 === 0 ? dialog.softRow : dialog.softAltRow)

                TapHandler {
                    onTapped: {
                        summaryView.currentIndex = index
                        summaryView.forceActiveFocus()
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                        radius: 2
                        color: model.color
                        border.color: model.unassigned ? "transparent" : dialog.softBorder
                    }

                    Label {
                        text: model.actor
                        color: model.unassigned ? "#D65A5A" : palette.text
                        font.bold: model.unassigned
                        Layout.preferredWidth: 190
                        elide: Text.ElideRight
                    }
                    Label { text: model.rings; Layout.preferredWidth: 60; horizontalAlignment: Text.AlignRight }
                    Label { text: model.words; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                    Label {
                        id: rolesLabel
                        text: model.roles
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: summaryView.count === 0
                text: qsTr("В проекте пока нет данных для отчёта")
                color: dialog.softMuted
            }
        }

        Shortcut {
            sequences: [StandardKey.Copy]
            enabled: summaryView.activeFocus && summaryView.currentIndex >= 0
            onActivated: dialog.reportsBackend.copySummaryRow(
                summaryView.currentIndex
            )
        }

        RowLayout {
            Layout.fillWidth: true
            visible: dialog.targetEpisode.length === 0
            spacing: 8

            Label { text: qsTr("Экспортировать:") }

            PlatformComboBox {
                id: metricCombo
                Layout.preferredWidth: 130
                model: metricModel
                textRole: "label"
                valueRole: "value"
                onActivated: if (dialog.reportsBackend) {
                    dialog.reportsBackend.setProjectSummaryMetric(currentValue)
                }

                function syncMetric() {
                    if (!dialog.reportsBackend) {
                        return
                    }
                    var metricIndex = indexOfValue(
                        dialog.reportsBackend.projectSummaryMetric
                    )
                    currentIndex = metricIndex >= 0 ? metricIndex : 0
                }
            }

            Button {
                text: qsTr("Экспорт для Google Sheets")
                onClicked: exportDialog.open()
            }

            Item { Layout.fillWidth: true }
        }
    }
}
