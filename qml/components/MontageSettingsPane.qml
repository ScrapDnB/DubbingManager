import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PersistentScrollView {
    id: pane

    required property var configuration
    property bool showFormatSettings: true
    property bool showOpenAfterExport: true
    property bool showEditableHtml: true
    readonly property var layoutProfileKeys: [
        "font_family",
        "col_tc", "col_char", "col_actor", "col_text",
        "table_width_time", "table_width_char", "table_width_actor",
        "time_display", "round_time", "hide_leading_timecode_zeros",
        "use_color", "soften_colors", "color_softening_level",
        "highlight_character_only",
        "f_time", "f_char", "f_actor", "f_text",
        "bold_time", "bold_char", "bold_actor", "bold_text"
    ]
    signal configEdited(var config)

    clip: true
    contentWidth: availableWidth

    function setValue(key, value) {
        var next = Object.assign({}, configuration)
        var profiles = Object.assign({}, next.layout_profiles || {})
        var activeLayout = String(next.layout_type || "Таблица")
        var activeProfile = Object.assign({}, profiles[activeLayout] || {})

        if (key === "layout_type") {
            for (var currentIndex = 0;
                 currentIndex < layoutProfileKeys.length; ++currentIndex) {
                var currentKey = layoutProfileKeys[currentIndex]
                activeProfile[currentKey] = next[currentKey]
            }
            profiles[activeLayout] = activeProfile

            var selectedProfile = Object.assign({}, profiles[value] || {})
            next.layout_type = value
            for (var selectedIndex = 0;
                 selectedIndex < layoutProfileKeys.length; ++selectedIndex) {
                var selectedKey = layoutProfileKeys[selectedIndex]
                if (selectedProfile[selectedKey] !== undefined)
                    next[selectedKey] = selectedProfile[selectedKey]
            }
        } else {
            next[key] = value
            if (layoutProfileKeys.indexOf(key) >= 0) {
                activeProfile[key] = value
                profiles[activeLayout] = activeProfile
            }
        }
        next.layout_profiles = profiles
        configEdited(next)
    }

    function softeningLevel() {
        var value = configuration.color_softening_level
        return value === undefined ? 1 : Math.max(-2, Math.min(2, Number(value)))
    }

    function systemFontFamilies() {
        var result = ["Segoe UI"]
        var installed = Qt.fontFamilies()
        for (var index = 0; index < installed.length; ++index) {
            if (installed[index] !== "Segoe UI") {
                result.push(installed[index])
            }
        }
        return result
    }

    function syncCombos() {
        layoutCombo.currentIndex = Math.max(0, layoutCombo.indexOfValue(configuration.layout_type))
        fontCombo.currentIndex = Math.max(0, fontCombo.find(
            String(configuration.font_family || "Segoe UI")
        ))
        timeCombo.currentIndex = Math.max(0, timeCombo.indexOfValue(configuration.time_display))
    }

    onConfigurationChanged: Qt.callLater(syncCombos)

    ColumnLayout {
        x: 12
        width: Math.max(0, pane.availableWidth - 24)
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

        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Шрифт") }
            PlatformComboBox {
                id: fontCombo
                Layout.preferredWidth: 180
                model: pane.systemFontFamilies()
                onActivated: pane.setValue("font_family", currentText)
            }
            Item { Layout.fillWidth: true }
        }

        FormSection {
            title: qsTr("Элементы и таймкод")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 2
                CheckBox { text: qsTr("Таймкод"); checked: Boolean(pane.configuration.col_tc); onToggled: pane.setValue("col_tc", checked) }
                CheckBox { text: qsTr("Персонаж"); checked: Boolean(pane.configuration.col_char); onToggled: pane.setValue("col_char", checked) }
                CheckBox { text: qsTr("Актёр"); checked: Boolean(pane.configuration.col_actor); onToggled: pane.setValue("col_actor", checked) }
                CheckBox { text: qsTr("Реплика"); checked: Boolean(pane.configuration.col_text); onToggled: pane.setValue("col_text", checked) }
                Label { text: qsTr("Показывать:") }
                PlatformComboBox {
                    id: timeCombo
                    Layout.fillWidth: true
                    model: ListModel {
                        ListElement { label: "Диапазон"; value: "range" }
                        ListElement { label: "Только начало"; value: "start" }
                    }
                    textRole: "label"
                    valueRole: "value"
                    onActivated: pane.setValue("time_display", currentValue)
                }
                CheckBox { text: qsTr("Округлять"); checked: Boolean(pane.configuration.round_time); onToggled: pane.setValue("round_time", checked) }
                CheckBox {
                    text: qsTr("Скрывать нули")
                    enabled: Boolean(pane.configuration.col_tc)
                    checked: Boolean(pane.configuration.hide_leading_timecode_zeros)
                    onToggled: pane.setValue("hide_leading_timecode_zeros", checked)
                }
            }
        }

        FormSection {
            title: qsTr("Цвета и подсветка")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 2
                CheckBox { text: qsTr("Цвета актёров"); checked: Boolean(pane.configuration.use_color); onToggled: pane.setValue("use_color", checked) }
                CheckBox { text: qsTr("Выделять только персонажа"); enabled: Boolean(pane.configuration.use_color); checked: Boolean(pane.configuration.highlight_character_only); onToggled: pane.setValue("highlight_character_only", checked) }
                RowLayout {
                    Layout.fillWidth: true
                    CheckBox {
                        id: softenColorsCheck
                        Layout.fillWidth: true
                        text: qsTr("Смягчать цвета")
                        enabled: Boolean(pane.configuration.use_color)
                        checked: Boolean(pane.configuration.soften_colors)
                        onToggled: pane.setValue("soften_colors", checked)
                    }
                    Slider {
                        id: softeningLevelSlider
                        Layout.preferredWidth: 78
                        from: -2
                        to: 2
                        stepSize: 1
                        snapMode: Slider.SnapAlways
                        enabled: softenColorsCheck.enabled && softenColorsCheck.checked
                        value: pane.softeningLevel()
                        Accessible.name: qsTr("Уровень смягчения")
                        onMoved: pane.setValue(
                            "color_softening_level", Math.round(value)
                        )
                    }
                }
                CheckBox { visible: pane.showEditableHtml; text: qsTr("Разрешить правку"); checked: Boolean(pane.configuration.allow_edit); onToggled: pane.setValue("allow_edit", checked) }
                CheckBox { visible: pane.showOpenAfterExport; text: qsTr("Открывать экспорт"); checked: Boolean(pane.configuration.open_auto); onToggled: pane.setValue("open_auto", checked) }
            }
        }

        FormSection {
            title: qsTr("Размер текста")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 3
                Label { text: qsTr("Таймкод") }
                SpinBox { Layout.fillWidth: true; from: 8; to: 72; value: Number(pane.configuration.f_time || 21); onValueModified: pane.setValue("f_time", value) }
                CheckBox { text: qsTr("Жирный"); checked: Boolean(pane.configuration.bold_time); onToggled: pane.setValue("bold_time", checked) }
                Label { text: qsTr("Персонаж") }
                SpinBox { Layout.fillWidth: true; from: 8; to: 72; value: Number(pane.configuration.f_char || 20); onValueModified: pane.setValue("f_char", value) }
                CheckBox { text: qsTr("Жирный"); checked: pane.configuration.bold_char === undefined ? true : Boolean(pane.configuration.bold_char); onToggled: pane.setValue("bold_char", checked) }
                Label { text: qsTr("Актёр") }
                SpinBox { Layout.fillWidth: true; from: 8; to: 72; value: Number(pane.configuration.f_actor || 14); onValueModified: pane.setValue("f_actor", value) }
                CheckBox { text: qsTr("Жирный"); checked: Boolean(pane.configuration.bold_actor); onToggled: pane.setValue("bold_actor", checked) }
                Label { text: qsTr("Реплика") }
                SpinBox { Layout.fillWidth: true; from: 8; to: 72; value: Number(pane.configuration.f_text || 30); onValueModified: pane.setValue("f_text", value) }
                CheckBox { text: qsTr("Жирный"); checked: Boolean(pane.configuration.bold_text); onToggled: pane.setValue("bold_text", checked) }
            }
        }

        FormSection {
            title: qsTr("Ширина колонок таблицы")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 2
                Label { text: qsTr("Таймкод") }
                SpinBox {
                    Layout.fillWidth: true
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_time || 7) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_time", value / 10)
                }
                Label { text: qsTr("Персонаж") }
                SpinBox {
                    Layout.fillWidth: true
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_char || 10) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_char", value / 10)
                }
                Label { text: qsTr("Актёр") }
                SpinBox {
                    Layout.fillWidth: true
                    from: 10; to: 300; value: Math.round(Number(pane.configuration.table_width_actor || 8.5) * 10)
                    textFromValue: function(value) { return (value / 10).toFixed(1) }
                    valueFromText: function(text) { return Math.round(Number(text.replace(",", ".")) * 10) }
                    onValueModified: pane.setValue("table_width_actor", value / 10)
                }
            }
        }

        FormSection {
            title: qsTr("Форматы экспорта по умолчанию")
            visible: pane.showFormatSettings
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 2
                CheckBox { text: qsTr("HTML"); checked: Boolean(pane.configuration.format_html); onToggled: pane.setValue("format_html", checked) }
                CheckBox { text: qsTr("XLSX"); checked: Boolean(pane.configuration.format_xls); onToggled: pane.setValue("format_xls", checked) }
                CheckBox { text: qsTr("DOCX"); checked: Boolean(pane.configuration.format_docx); onToggled: pane.setValue("format_docx", checked) }
                CheckBox { text: qsTr("PDF"); checked: Boolean(pane.configuration.format_pdf); onToggled: pane.setValue("format_pdf", checked) }
            }
        }
    }
}
