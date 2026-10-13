pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    required property var appBridge
    property bool spreadsheet: false
    readonly property var backend: appBridge ? (spreadsheet ? appBridge.spreadsheetImport : appBridge.docxImport) : null
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted

    modal: true
    title: spreadsheet ? qsTr("Импорт таблиц") : qsTr("Импорт DOCX")
    standardButtons: Dialog.NoButton
    minimumWidth: 980
    minimumHeight: 680
    width: boundedWidth(1220, 28)
    height: boundedHeight(860, 28)

    function openForFile(path) {
        if (!backend.load(path)) return
        episodeField.text = spreadsheet ? backend.episodeName : backend.suggestedEpisode
        if (!spreadsheet) tableCombo.currentIndex = backend.currentTableIndex
        open()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Rectangle {
                Layout.preferredWidth: 62
                Layout.preferredHeight: 54
                radius: 10
                color: dialog.softHeader
                border.color: dialog.softBorder
                Label {
                    anchors.centerIn: parent
                    text: dialog.spreadsheet ? (dialog.backend.isCsv ? "CSV" : "XLS") : "DOCX"
                    font.bold: true
                    color: palette.text
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                Label {
                    text: dialog.backend.fileName
                    font.pixelSize: 18
                    font.bold: true
                    Layout.fillWidth: true
                    elide: Text.ElideMiddle
                }
                Label { text: dialog.backend.sourceSummary; color: dialog.softMuted; Layout.fillWidth: true }
            }
            ColumnLayout {
                visible: !dialog.spreadsheet && dialog.backend.tableCount > 1
                Label { text: qsTr("Таблица для настройки"); color: dialog.softMuted }
                PlatformComboBox {
                    id: tableCombo
                    Layout.preferredWidth: 280
                    model: dialog.spreadsheet ? null : dialog.backend.tablesModel
                    textRole: "label"
                    valueRole: "index"
                    onActivated: dialog.backend.setTable(currentValue)
                }
            }
        }

        Rectangle {
            visible: dialog.spreadsheet && !dialog.backend.isCsv
            Layout.fillWidth: true
            Layout.preferredHeight: 108
            color: dialog.softHeader
            border.color: dialog.softBorder
            radius: 6
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6
                Label { text: qsTr("Выберите листы для импорта. Каждый выбранный лист станет отдельной серией."); color: dialog.softMuted }
                ListView {
                    id: sheetsView
                    objectName: "importSheets"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: ListView.Horizontal
                    spacing: 8
                    clip: true
                    model: dialog.spreadsheet ? dialog.backend.sheets : []
                    ScrollBar.horizontal: ScrollBar { }
                    delegate: Rectangle {
                        id: sheetCard
                        required property var modelData
                        width: 240
                        height: 52
                        radius: 5
                        color: sheetCard.modelData.index === dialog.backend.currentSheetIndex ? palette.base : "transparent"
                        border.color: sheetCard.modelData.index === dialog.backend.currentSheetIndex ? palette.highlight : dialog.softBorder
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 6
                            CheckBox {
                                checked: sheetCard.modelData.selected
                                enabled: sheetCard.modelData.rowCount > 0
                                Accessible.name: qsTr("Импортировать лист ") + sheetCard.modelData.name
                                onClicked: dialog.backend.setSelected(sheetCard.modelData.index, checked)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label { text: sheetCard.modelData.name; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label {
                                    text: sheetCard.modelData.rowCount === 0 ? qsTr("Пустой лист")
                                        : sheetCard.modelData.episode + (sheetCard.modelData.hidden ? qsTr(" · скрытый") : "")
                                    color: dialog.softMuted
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                TapHandler {
                                    onTapped: {
                                        dialog.backend.setSheet(sheetCard.modelData.index)
                                        episodeField.text = dialog.backend.episodeName
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            visible: dialog.spreadsheet && dialog.backend.isCsv
            Layout.fillWidth: true
            Label { text: qsTr("Кодировка:"); color: dialog.softMuted }
            PlatformComboBox {
                Layout.preferredWidth: 180
                model: ["Автоматически", "UTF-8", "Windows-1251", "UTF-16", "KOI8-R"]
                readonly property var values: ["auto", "utf-8-sig", "cp1251", "utf-16", "koi8-r"]
                currentIndex: dialog.spreadsheet ? values.indexOf(dialog.backend.encoding) : 0
                onActivated: dialog.backend.setCsvOptions(values[currentIndex], dialog.backend.delimiter)
            }
            Label { text: qsTr("Разделитель:"); color: dialog.softMuted }
            PlatformComboBox {
                Layout.preferredWidth: 180
                model: ["Автоматически", "Точка с запятой ;", "Запятая ,", "Табуляция", "Вертикальная черта |"]
                readonly property var values: ["auto", ";", ",", "\t", "|"]
                currentIndex: dialog.spreadsheet ? values.indexOf(dialog.backend.delimiter) : 0
                onActivated: dialog.backend.setCsvOptions(dialog.backend.encoding, values[currentIndex])
            }
            Item { Layout.fillWidth: true }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            PersistentScrollView {
                id: settingsScroll
                SplitView.preferredWidth: 330
                SplitView.minimumWidth: 310
                SplitView.maximumWidth: 420
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: settingsScroll.availableWidth
                    spacing: 18
                    CheckBox {
                        objectName: "importIgnoreHeader"
                        text: qsTr("Игнорировать заголовок таблицы")
                        enabled: dialog.backend.rowCount > 0
                        checked: dialog.backend.ignoreHeader
                        onClicked: dialog.backend.setIgnoreHeader(checked)
                    }
                    AdaptiveButton {
                        objectName: "importApplyColumnsToAll"
                        visible: dialog.spreadsheet && !dialog.backend.isCsv
                        enabled: dialog.spreadsheet && dialog.backend.canApplyMappingToAll
                        Layout.fillWidth: true
                        Layout.rightMargin: 14
                        text: qsTr("Применить колонки ко всем сериям")
                        onClicked: dialog.backend.applyMappingToAll()
                    }
                    ImportColumnMapping {
                        Layout.fillWidth: true
                        Layout.rightMargin: 14
                        backend: dialog.backend
                        softMuted: dialog.softMuted
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.rightMargin: 14
                        spacing: 6
                        Label { text: qsTr("Начало данных"); font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Начальная строка таблицы"); Layout.fillWidth: true }
                            SpinBox {
                                objectName: "importFirstRow"
                                from: 1
                                to: Math.max(1, dialog.backend.rowCount)
                                value: dialog.backend.tableStartRow
                                editable: true
                                onValueModified: dialog.backend.setTableStartRow(value)
                            }
                        }
                        Label {
                            text: qsTr("Строки выше пропускаются. Если галочка включена, начальная строка считается заголовком и тоже пропускается.")
                            Layout.fillWidth: true
                            color: dialog.softMuted
                            wrapMode: Text.WordWrap
                        }
                        Label {
                            visible: !dialog.spreadsheet
                            text: dialog.spreadsheet ? "" : dialog.backend.detectionSummary
                            Layout.fillWidth: true
                            color: dialog.softMuted
                            wrapMode: Text.WordWrap
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.rightMargin: 14
                        spacing: 6
                        Label { text: qsTr("Формат времени"); font.bold: true }
                        Label {
                            text: dialog.spreadsheet ? qsTr("Числовые значения времени") : qsTr("Разделители начала и конца")
                            color: dialog.softMuted
                        }
                        PlatformComboBox {
                            visible: dialog.spreadsheet
                            Layout.fillWidth: true
                            model: ["Секунды (например, 12.5)", "Доли суток Excel (например, 0.5)"]
                            currentIndex: dialog.spreadsheet && dialog.backend.timeUnit === "excel" ? 1 : 0
                            onActivated: dialog.backend.setTimeUnit(currentIndex === 1 ? "excel" : "seconds")
                        }
                        TextField {
                            visible: !dialog.spreadsheet
                            Layout.fillWidth: true
                            text: dialog.spreadsheet ? "" : dialog.backend.separators
                            selectByMouse: true
                            onEditingFinished: dialog.backend.setSeparators(text)
                        }
                        RowLayout {
                            visible: dialog.spreadsheet
                            Label { text: qsTr("Кадров в секунду (FPS)"); Layout.fillWidth: true }
                            TextField {
                                Layout.preferredWidth: 74
                                text: dialog.spreadsheet ? String(dialog.backend.fps) : "25"
                                validator: DoubleValidator { bottom: 1; top: 240; locale: "C" }
                                selectByMouse: true
                                onEditingFinished: dialog.backend.setFps(Number(text.replace(",", ".")))
                            }
                        }
                        Label {
                            text: dialog.spreadsheet
                                ? qsTr("Поддерживаются 00:01:23.500, диапазоны времени, Excel-время и 00:01:23:12 с кадрами. Без тайминга: начало 0, длительность 1 с.")
                                : qsTr("Пример диапазона: 00:01:23 – 00:01:25. Без тайминга будет использована длительность по умолчанию.")
                            Layout.fillWidth: true
                            color: dialog.softMuted
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
            ImportPreviewPane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 600
                Layout.leftMargin: 14
                backend: dialog.backend
                softBorder: dialog.softBorder
                softHeader: dialog.softHeader
                softRow: dialog.softRow
                softAltRow: dialog.softAltRow
                softMuted: dialog.softMuted
            }
        }
    }

    footer: ColumnLayout {
        anchors.fill: parent
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: dialog.spreadsheet ? qsTr("Серия текущего листа:") : qsTr("Название серии:") }
            TextField {
                id: episodeField
                objectName: "importEpisodeName"
                Layout.preferredWidth: 280
                Layout.fillWidth: true
                selectByMouse: true
                placeholderText: qsTr("Например, 01 · Начало")
                onTextEdited: if (dialog.spreadsheet) dialog.backend.setEpisodeName(text)
            }
            Label {
                text: dialog.spreadsheet ? dialog.backend.summary : qsTr("Таблицы будут добавлены в одну серию")
                color: dialog.softMuted
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: dialog.backend.validationMessage || (dialog.spreadsheet
                    ? qsTr("Настройки колонок и начала данных сохраняются отдельно для каждого листа.")
                    : dialog.backend.summary)
                color: dialog.backend.validationMessage ? palette.brightText : dialog.softMuted
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            AdaptiveButton { text: qsTr("Отмена"); onClicked: dialog.close() }
            AdaptiveButton {
                text: qsTr("Все таблицы в одну серию")
                visible: !dialog.spreadsheet && dialog.backend.tableCount > 1
                enabled: dialog.backend.canImport && episodeField.text.trim().length > 0
                onClicked: if (dialog.backend.importEpisode(episodeField.text, true)) dialog.close()
            }
            AdaptiveButton {
                objectName: "importConfirmButton"
                text: dialog.spreadsheet ? qsTr("Импортировать выбранные листы") : qsTr("Импортировать таблицу")
                highlighted: true
                enabled: dialog.backend.canImport && episodeField.text.trim().length > 0
                onClicked: {
                    var success = dialog.spreadsheet ? dialog.backend.importSelected()
                        : dialog.backend.importEpisode(episodeField.text, false)
                    if (success) dialog.close()
                }
            }
        }
    }
}
