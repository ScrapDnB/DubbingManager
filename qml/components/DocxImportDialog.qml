pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    readonly property var backend: appBridge ? appBridge.docxImport : null
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted

    modal: true
    title: qsTr("Импорт DOCX")
    standardButtons: Dialog.NoButton
    minimumWidth: 900
    minimumHeight: 640
    width: boundedWidth(1180, 28)
    height: boundedHeight(780, 28)

    function openForFile(path) {
        if (!backend.load(path)) return
        episodeField.text = backend.suggestedEpisode
        tableCombo.currentIndex = backend.currentTableIndex
        open()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Label {
                text: dialog.backend.fileName
                font.bold: true
                Layout.fillWidth: true
                elide: Text.ElideMiddle
            }
            Label { text: qsTr("Таблица:"); visible: tableCombo.count > 1 }
            PlatformComboBox {
                id: tableCombo
                visible: count > 1
                Layout.preferredWidth: 280
                model: dialog.backend.tablesModel
                textRole: "label"
                valueRole: "index"
                onActivated: dialog.backend.setTable(currentValue)
            }
            Button { text: qsTr("Автоопределение"); onClicked: dialog.backend.autoDetect() }
        }

        Label {
            Layout.fillWidth: true
            text: dialog.backend.detectionSummary
            color: dialog.softMuted
            wrapMode: Text.WordWrap
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            PersistentScrollView {
                id: settingsScroll
                SplitView.preferredWidth: 390
                SplitView.minimumWidth: 340
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                ColumnLayout {
                    width: settingsScroll.availableWidth
                    spacing: 10

                    GroupBox {
                        title: qsTr("Колонки")
                        Layout.fillWidth: true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 6

                            Repeater {
                                model: dialog.backend.fields
                                delegate: RowLayout {
                                    id: mappingRow
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: 6

                                    Label {
                                        text: mappingRow.modelData.label
                                        Layout.preferredWidth: 140
                                        elide: Text.ElideRight
                                    }
                                    PlatformComboBox {
                                        id: mappingCombo
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 120
                                        model: dialog.backend.columnsModel
                                        textRole: "label"
                                        valueRole: "index"
                                        currentIndex: {
                                            var value = dialog.backend.mapping[mappingRow.modelData.key]
                                            return value === null || value === undefined ? -1 : Number(value)
                                        }
                                        onActivated: dialog.backend.setMapping(mappingRow.modelData.key, currentValue)
                                    }
                                    ToolButton {
                                        text: qsTr("×")
                                        Layout.preferredWidth: 28
                                        Layout.preferredHeight: 28
                                        enabled: mappingCombo.currentIndex >= 0
                                        onClicked: dialog.backend.setMapping(mappingRow.modelData.key, -1)
                                        ToolTip.visible: hovered
                                        ToolTip.text: qsTr("Не использовать колонку")
                                    }
                                }
                            }
                        }
                    }

                    GroupBox {
                        title: qsTr("Тайминг")
                        Layout.fillWidth: true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 6
                            Label { text: qsTr("Разделители диапазона:"); color: dialog.softMuted }
                            TextField {
                                Layout.fillWidth: true
                                text: dialog.backend.separators
                                selectByMouse: true
                                onEditingFinished: dialog.backend.setSeparators(text)
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            ColumnLayout {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 500
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30
                    color: dialog.softHeader
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 10
                        Label { text: qsTr("Персонаж"); font.bold: true; Layout.preferredWidth: 140 }
                        Label { text: qsTr("Тайминг"); font.bold: true; Layout.preferredWidth: 125 }
                        Label { text: qsTr("Реплика"); font.bold: true; Layout.fillWidth: true }
                        Label { text: qsTr("Статус"); font.bold: true; Layout.preferredWidth: 85 }
                    }
                }
                PersistentListView {
                    id: previewView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: dialog.backend.previewModel
                    delegate: Rectangle {
                        id: previewRow
                        required property int index
                        required property string character
                        required property string timing
                        required property string text
                        required property string status
                        width: previewView.viewportWidth
                        height: 36
                        color: index % 2 === 0 ? dialog.softRow : dialog.softAltRow
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 10
                            Label { text: previewRow.character; Layout.preferredWidth: 140; elide: Text.ElideRight }
                            Label { text: previewRow.timing; Layout.preferredWidth: 125; elide: Text.ElideRight }
                            Label { text: previewRow.text; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: previewRow.status; Layout.preferredWidth: 85; color: previewRow.status === "Готово" ? palette.text : palette.brightText }
                        }
                    }
                }
            }
        }

        Label { text: dialog.backend.summary; color: dialog.softMuted; Layout.fillWidth: true }
    }

    footer: RowLayout {
        anchors.fill: parent
        spacing: 8

        Label { text: qsTr("Серия:") }
        TextField {
            id: episodeField
            Layout.preferredWidth: 170
            Layout.minimumWidth: 110
            selectByMouse: true
            placeholderText: qsTr("Название серии")
        }
        Item { Layout.fillWidth: true }
        Button {
            text: dialog.width < 940 ? "Таблицу" : "Импортировать таблицу"
            enabled: dialog.backend.canImport
            onClicked: if (dialog.backend.importEpisode(episodeField.text, false)) dialog.close()
        }
        Button {
            text: dialog.width < 940 ? "Все таблицы" : "Импортировать все"
            visible: dialog.backend.tableCount > 1
            enabled: dialog.backend.canImport
            onClicked: if (dialog.backend.importEpisode(episodeField.text, true)) dialog.close()
        }
        Button { text: qsTr("Отмена"); onClicked: dialog.close() }
    }
}
