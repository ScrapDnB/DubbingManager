pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: pane
    required property var backend
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    spacing: 10

    RowLayout {
        Layout.fillWidth: true
        Label { text: qsTr("2  Проверьте результат"); font.bold: true; Layout.fillWidth: true }
        Label { text: qsTr("Первые 30 строк"); color: pane.softMuted }
    }
    NavigationTabBar {
        id: previewTabs
        objectName: "importPreviewTabs"
        Layout.fillWidth: true
        tabWidth: width / 2
        model: [qsTr("Реплики после импорта"), qsTr("Исходные колонки")]
        softMuted: pane.softMuted
    }
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "transparent"
        border.color: pane.softBorder
        radius: 6
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 1
            spacing: 0
            visible: previewTabs.currentIndex === 0
            TableHeaderSurface {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                softHeader: pane.softHeader
                softBorder: pane.softBorder
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 12
                    TableHeaderLabel { text: qsTr("Персонаж"); Layout.preferredWidth: 100 }
                    TableHeaderLabel { text: qsTr("Тайминг"); Layout.preferredWidth: 105 }
                    TableHeaderLabel { text: qsTr("Текст реплики"); Layout.fillWidth: true }
                    TableHeaderLabel { text: qsTr("Статус"); Layout.preferredWidth: 110 }
                }
            }
            PersistentListView {
                id: preview
                objectName: "importPreview"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: pane.backend.previewModel
                delegate: Rectangle {
                    id: previewRow
                    required property int index
                    required property string character
                    required property string timing
                    required property string text
                    required property string status
                    width: preview.viewportWidth
                    height: Math.max(56, textLabel.implicitHeight + 20)
                    color: index % 2 ? pane.softAltRow : pane.softRow
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12
                        Label { text: previewRow.character || "—"; Layout.preferredWidth: 100; elide: Text.ElideRight }
                        Label {
                            text: (previewRow.timing || "—").replace(/\s[-–—]\s/, "\n")
                            Layout.preferredWidth: 105
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                        Label {
                            id: textLabel
                            text: previewRow.text || "—"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            HoverHandler { id: textHover }
                            ToolTip.visible: textHover.hovered && textLabel.truncated
                            ToolTip.text: previewRow.text
                        }
                        Label {
                            text: previewRow.status
                            Layout.preferredWidth: 110
                            wrapMode: Text.WordWrap
                            color: previewRow.status === "Готово" ? pane.softMuted : palette.brightText
                        }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    width: parent.width - 40
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: qsTr("Назначьте колонку с текстом, чтобы увидеть реплики.")
                    color: pane.softMuted
                    visible: preview.count === 0
                }
            }
        }
        PersistentScrollView {
            id: rawScroll
            anchors.fill: parent
            anchors.margins: 1
            visible: previewTabs.currentIndex === 1
            clip: true
            contentWidth: Math.max(availableWidth, 50 + pane.backend.columnCount * 180)
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ColumnLayout {
                width: rawScroll.contentWidth
                height: rawScroll.availableHeight
                spacing: 0
                Row {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    spacing: 0
                    Label { text: "№"; width: 50; height: 38; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    Repeater {
                        model: pane.backend.columnsModel
                        delegate: Label {
                            required property string label
                            width: 180
                            height: 38
                            verticalAlignment: Text.AlignVCenter
                            text: label
                            font.bold: true
                            elide: Text.ElideRight
                            leftPadding: 10
                            rightPadding: 10
                        }
                    }
                }
                ListView {
                    id: rawView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: pane.backend.rawRows
                    ScrollBar.vertical: ScrollBar { }
                    delegate: Rectangle {
                        id: rawRow
                        required property int index
                        required property var modelData
                        width: rawView.width
                        height: 52
                        color: index % 2 ? pane.softAltRow : pane.softRow
                        Row {
                            anchors.fill: parent
                            spacing: 0
                            Label { text: rawRow.modelData.row; width: 50; height: 52; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; color: pane.softMuted }
                            Repeater {
                                model: pane.backend.columnCount
                                delegate: Label {
                                    required property int index
                                    width: 180
                                    height: 52
                                    verticalAlignment: Text.AlignVCenter
                                    text: rawRow.modelData.cells[index] || ""
                                    wrapMode: Text.Wrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    leftPadding: 10
                                    rightPadding: 10
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    Label {
        Layout.fillWidth: true
        text: qsTr("Одна строка таблицы — одна реплика. Текст сохраняется внутри проекта.")
        color: pane.softMuted
        wrapMode: Text.WordWrap
    }
}
