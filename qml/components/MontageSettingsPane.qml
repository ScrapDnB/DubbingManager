import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PersistentScrollView {
    id: pane

    required property var configuration
    property bool showFormatSettings: true
    property bool showOpenAfterExport: true
    property bool showEditableHtml: true
    signal configEdited(var config)

    clip: true
    contentWidth: availableWidth

    function setValue(key, value) {
        var next = Object.assign({}, configuration)
        next[key] = value
        configEdited(next)
    }

    function syncCombos() {
        layoutCombo.currentIndex = Math.max(0, layoutCombo.indexOfValue(configuration.layout_type))
        timeCombo.currentIndex = Math.max(0, timeCombo.indexOfValue(configuration.time_display))
    }

    onConfigurationChanged: Qt.callLater(syncCombos)

    ColumnLayout {
        width: pane.availableWidth
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Макет:") }
            PlatformComboBox {
                id: layoutCombo
                Layout.preferredWidth: 180
                model: ["Таблица", "Сценарий 1", "Сценарий 2", "Сценарий 3"]
                onActivated: pane.setValue("layout_type", currentText)
            }
            Item { Layout.fillWidth: true }
        }

        GroupBox {
            title: qsTr("Колонки и таймкод")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                CheckBox { text: qsTr("Таймкод"); checked: Boolean(pane.configuration.col_tc); onToggled: pane.setValue("col_tc", checked) }
                CheckBox { text: qsTr("Персонаж"); checked: Boolean(pane.configuration.col_char); onToggled: pane.setValue("col_char", checked) }
                CheckBox { text: qsTr("Актёр"); checked: Boolean(pane.configuration.col_actor); onToggled: pane.setValue("col_actor", checked) }
                CheckBox { text: qsTr("Реплика"); checked: Boolean(pane.configuration.col_text); onToggled: pane.setValue("col_text", checked) }
                Label { text: qsTr("Показывать:") }
                PlatformComboBox {
                    id: timeCombo
                    Layout.preferredWidth: 160
                    model: ListModel {
                        ListElement { label: "Диапазон"; value: "range" }
                        ListElement { label: "Только начало"; value: "start" }
                    }
                    textRole: "label"
                    valueRole: "value"
                    onActivated: pane.setValue("time_display", currentValue)
                }
                CheckBox { text: qsTr("Округлять"); checked: Boolean(pane.configuration.round_time); onToggled: pane.setValue("round_time", checked) }
                Item { Layout.fillWidth: true }
            }
        }

        GroupBox {
            title: qsTr("Оформление")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                CheckBox { text: qsTr("Цвета актёров"); checked: Boolean(pane.configuration.use_color); onToggled: pane.setValue("use_color", checked) }
                CheckBox { text: qsTr("Смягчать фон"); enabled: Boolean(pane.configuration.use_color); checked: Boolean(pane.configuration.soften_colors); onToggled: pane.setValue("soften_colors", checked) }
                CheckBox { visible: pane.showEditableHtml; text: qsTr("Разрешить правку"); checked: Boolean(pane.configuration.allow_edit); onToggled: pane.setValue("allow_edit", checked) }
                CheckBox { visible: pane.showOpenAfterExport; text: qsTr("Открывать экспорт"); checked: Boolean(pane.configuration.open_auto); onToggled: pane.setValue("open_auto", checked) }
            }
        }

        GroupBox {
            title: qsTr("Размер текста")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Label { text: qsTr("Таймкод") }
                WinUiSpinBox { from: 8; to: 72; value: Number(pane.configuration.f_time || 21); onValueModified: pane.setValue("f_time", value) }
                Label { text: qsTr("Персонаж") }
                WinUiSpinBox { from: 8; to: 72; value: Number(pane.configuration.f_char || 20); onValueModified: pane.setValue("f_char", value) }
                Label { text: qsTr("Актёр") }
                WinUiSpinBox { from: 8; to: 72; value: Number(pane.configuration.f_actor || 14); onValueModified: pane.setValue("f_actor", value) }
                Label { text: qsTr("Реплика") }
                WinUiSpinBox { from: 8; to: 72; value: Number(pane.configuration.f_text || 30); onValueModified: pane.setValue("f_text", value) }
            }
        }

        GroupBox {
            title: qsTr("Ширина колонок таблицы")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 6
                Label { text: qsTr("Таймкод") }
                WinUiSpinBox {
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_time || 7) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_time", value / 10)
                }
                Label { text: qsTr("Персонаж") }
                WinUiSpinBox {
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_char || 10) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_char", value / 10)
                }
                Label { text: qsTr("Актёр") }
                WinUiSpinBox {
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_actor || 8.5) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_actor", value / 10)
                }
            }
        }

        GroupBox {
            title: qsTr("Форматы экспорта по умолчанию")
            visible: pane.showFormatSettings
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                CheckBox { text: qsTr("HTML"); checked: Boolean(pane.configuration.format_html); onToggled: pane.setValue("format_html", checked) }
                CheckBox { text: qsTr("XLSX"); checked: Boolean(pane.configuration.format_xls); onToggled: pane.setValue("format_xls", checked) }
                CheckBox { text: qsTr("DOCX"); checked: Boolean(pane.configuration.format_docx); onToggled: pane.setValue("format_docx", checked) }
                CheckBox { text: qsTr("PDF"); checked: Boolean(pane.configuration.format_pdf); onToggled: pane.setValue("format_pdf", checked) }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
