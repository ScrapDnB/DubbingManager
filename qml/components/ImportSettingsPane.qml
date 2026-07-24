pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane

    property var mergeConfiguration: ({})
    property var assConfiguration: ({})
    property var srtConfiguration: ({})
    property var docxConfiguration: ({})
    property var docxPresets: []
    property color softMuted: palette.placeholderText

    signal mergeEdited(var config)
    signal assEdited(var config)
    signal srtEdited(var config)
    signal docxEdited(var config)
    signal saveDocxPresetRequested(string name, var config)
    signal deleteDocxPresetRequested(string name)

    function numberFrom(text, fallback) {
        var value = Number(String(text).replace(",", "."))
        return isNaN(value) ? fallback : value
    }

    function setMergeValue(key, value) {
        var next = Object.assign({}, mergeConfiguration)
        next[key] = value
        mergeEdited(next)
    }

    function setGapSeconds(value) {
        var next = Object.assign({}, mergeConfiguration)
        var fps = Number(next.fps || 25)
        next.merge_gap = Math.round(Math.max(0, value) * fps)
        mergeEdited(next)
    }

    function setFps(value) {
        var next = Object.assign({}, mergeConfiguration)
        var oldFps = Number(next.fps || 25)
        var gapSeconds = Number(next.merge_gap || 0) / oldFps
        next.fps = value
        next.merge_gap = Math.round(gapSeconds * value)
        mergeEdited(next)
    }

    function setAssValue(key, value) {
        var next = Object.assign({}, assConfiguration)
        next[key] = value
        assEdited(next)
    }

    function setSrtValue(key, value) {
        var next = Object.assign({}, srtConfiguration)
        next[key] = value
        srtEdited(next)
    }

    function setDocxValue(key, value) {
        var next = Object.assign({}, docxConfiguration)
        next[key] = value
        docxEdited(next)
    }

    function setDocxAliases(field, text) {
        var next = Object.assign({}, docxConfiguration)
        var aliases = Object.assign({}, next.aliases || {})
        aliases[field] = String(text).split(/[,\n]/).map(function(value) {
            return value.trim()
        }).filter(function(value) { return value.length > 0 })
        next.aliases = aliases
        docxEdited(next)
    }

    function aliasesText(field) {
        var aliases = docxConfiguration.aliases || {}
        return Array.isArray(aliases[field]) ? aliases[field].join(", ") : ""
    }

    function docxFieldLabel(field) {
        var labels = {
            "character": "Персонаж",
            "time_start": "Начало",
            "time_end": "Конец",
            "time_split": "Диапазон времени",
            "text": "Текст реплики"
        }
        return labels[field] || field
    }

    function moveDocxPriority(index, offset) {
        var priority = Array.isArray(docxConfiguration.field_priority)
            ? docxConfiguration.field_priority.slice()
            : ["character", "time_start", "time_end", "time_split", "text"]
        var target = index + offset
        if (target < 0 || target >= priority.length)
            return
        var item = priority[index]
        priority[index] = priority[target]
        priority[target] = item
        setDocxValue("field_priority", priority)
    }

    function setDocxFallback(field, value) {
        var next = Object.assign({}, docxConfiguration)
        var fallback = Object.assign({}, next.fallback_mapping || {})
        fallback[field] = value < 0 ? null : value
        next.fallback_mapping = fallback
        docxEdited(next)
    }

    function applyDocxPreset(index) {
        if (index < 0 || index >= docxPresets.length)
            return
        var config = docxPresets[index].config || {}
        docxEdited(JSON.parse(JSON.stringify(config)))
    }

    PersistentScrollView {
        id: importScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: importScroll.availableWidth
            spacing: 10

            Label {
                Layout.fillWidth: true
                text: qsTr("Эти параметры управляют разбором исходников до создания рабочего текста.")
                wrapMode: Text.WordWrap
                color: pane.softMuted
            }

            GroupBox {
                title: qsTr("Объединение реплик")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    CheckBox {
                        text: qsTr("Объединять близкие реплики одного персонажа")
                        checked: Boolean(pane.mergeConfiguration.merge)
                        Layout.columnSpan: 2
                        onToggled: pane.setMergeValue("merge", checked)
                    }
                    Label { text: qsTr("FPS:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.mergeConfiguration.fps || 25)
                        validator: DoubleValidator { bottom: 1; top: 120; decimals: 3 }
                        onEditingFinished: pane.setFps(pane.numberFrom(text, 25))
                    }
                    Label { text: qsTr("Порог объединения, сек:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: {
                            var fps = Number(pane.mergeConfiguration.fps || 25)
                            return String(Number(pane.mergeConfiguration.merge_gap || 0) / fps)
                        }
                        validator: DoubleValidator { bottom: 0; top: 10; decimals: 3 }
                        onEditingFinished: pane.setGapSeconds(
                            pane.numberFrom(text, 4.8)
                        )
                    }
                    Label { text: qsTr("Пауза для '/', сек:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.mergeConfiguration.p_short ?? 0.5)
                        validator: DoubleValidator { bottom: 0; top: 5; decimals: 3 }
                        onEditingFinished: pane.setMergeValue(
                            "p_short", pane.numberFrom(text, 0.5)
                        )
                    }
                    Label { text: qsTr("Пауза для '//', сек:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.mergeConfiguration.p_long ?? 2)
                        validator: DoubleValidator { bottom: 0; top: 10; decimals: 3 }
                        onEditingFinished: pane.setMergeValue(
                            "p_long", pane.numberFrom(text, 2)
                        )
                    }
                }
            }

            GroupBox {
                title: qsTr("ASS")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    CheckBox {
                        text: qsTr("Разделять несколько имён персонажей")
                        checked: Boolean(pane.assConfiguration.split_character_names)
                        Layout.columnSpan: 2
                        onToggled: pane.setAssValue("split_character_names", checked)
                    }
                    CheckBox {
                        text: qsTr("Удалять служебные теги оформления ASS")
                        checked: Boolean(pane.assConfiguration.strip_override_tags)
                        Layout.columnSpan: 2
                        onToggled: pane.setAssValue("strip_override_tags", checked)
                    }
                    Label { text: qsTr("Разделитель имён:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.assConfiguration.character_separator || ";")
                        maximumLength: 8
                        onEditingFinished: pane.setAssValue(
                            "character_separator", text || ";"
                        )
                    }
                }
            }

            GroupBox {
                title: qsTr("SRT")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    CheckBox {
                        text: qsTr("Распознавать имя персонажа в начале реплики")
                        checked: Boolean(pane.srtConfiguration.detect_character_prefix)
                        Layout.columnSpan: 2
                        onToggled: pane.setSrtValue("detect_character_prefix", checked)
                    }
                    CheckBox {
                        text: qsTr("Сохранять переносы строк внутри реплики")
                        checked: Boolean(pane.srtConfiguration.keep_multiline)
                        Layout.columnSpan: 2
                        onToggled: pane.setSrtValue("keep_multiline", checked)
                    }
                    Label { text: qsTr("Разделитель имени:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.srtConfiguration.character_separator || ":")
                        maximumLength: 8
                        onEditingFinished: pane.setSrtValue(
                            "character_separator", text || ":"
                        )
                    }
                    Label { text: qsTr("Персонаж по умолчанию:") }
                    TextField {
                        Layout.fillWidth: true
                        text: String(pane.srtConfiguration.default_character || "")
                        placeholderText: qsTr("Оставьте пустым")
                        onEditingFinished: pane.setSrtValue(
                            "default_character", text.trim()
                        )
                    }
                }
            }

            GroupBox {
                title: qsTr("DOCX: пресеты")
                Layout.fillWidth: true

                GridLayout {
                    anchors.fill: parent
                    columns: 3
                    columnSpacing: 8
                    rowSpacing: 7

                    PlatformComboBox {
                        id: docxPresetCombo
                        Layout.fillWidth: true
                        Layout.columnSpan: 2
                        model: pane.docxPresets
                        textRole: "name"
                        valueRole: "name"
                    }
                    Button {
                        text: qsTr("Применить")
                        enabled: docxPresetCombo.currentIndex >= 0
                        onClicked: pane.applyDocxPreset(
                            docxPresetCombo.currentIndex
                        )
                    }
                    TextField {
                        id: docxPresetName
                        Layout.fillWidth: true
                        Layout.columnSpan: 2
                        placeholderText: qsTr("Название нового пресета")
                        selectByMouse: true
                    }
                    RowLayout {
                        Button {
                            text: qsTr("Сохранить")
                            enabled: docxPresetName.text.trim().length > 0
                            onClicked: pane.saveDocxPresetRequested(
                                docxPresetName.text.trim(),
                                pane.docxConfiguration
                            )
                        }
                        Button {
                            text: qsTr("Удалить")
                            enabled: docxPresetCombo.currentIndex >= 0
                            onClicked: pane.deleteDocxPresetRequested(
                                String(docxPresetCombo.currentValue || "")
                            )
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("DOCX: автоматическое распознавание")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    Label { text: qsTr("Строка заголовков:") }
                    PlatformComboBox {
                        Layout.preferredWidth: 190
                        model: [
                            { text: qsTr("Определять автоматически"), value: "auto" },
                            { text: qsTr("Всегда первая строка"), value: "first" },
                            { text: qsTr("Без заголовков"), value: "none" }
                        ]
                        textRole: "text"
                        valueRole: "value"
                        currentIndex: {
                            var mode = String(pane.docxConfiguration.header_mode || "auto")
                            return mode === "first" ? 1 : (mode === "none" ? 2 : 0)
                        }
                        onActivated: pane.setDocxValue("header_mode", currentValue)
                    }
                    Label { text: qsTr("Искать заголовки в первых строках:") }
                    SpinBox {
                        from: 1
                        to: 20
                        value: Number(pane.docxConfiguration.header_search_rows || 5)
                        editable: true
                        onValueModified: pane.setDocxValue("header_search_rows", value)
                    }
                    Label { text: qsTr("Минимум совпавших полей:") }
                    SpinBox {
                        from: 1
                        to: 5
                        value: Number(pane.docxConfiguration.minimum_header_matches || 2)
                        editable: true
                        onValueModified: pane.setDocxValue("minimum_header_matches", value)
                    }
                    Label { text: qsTr("Пропустить строк после заголовка:") }
                    SpinBox {
                        from: 0
                        to: 100
                        value: Number(pane.docxConfiguration.rows_to_skip || 0)
                        editable: true
                        onValueModified: pane.setDocxValue("rows_to_skip", value)
                    }
                    Label { text: qsTr("Длительность без тайминга, сек:") }
                    TextField {
                        Layout.preferredWidth: 120
                        text: String(pane.docxConfiguration.default_duration || 1)
                        validator: DoubleValidator { bottom: 0.01; top: 60; decimals: 3 }
                        onEditingFinished: pane.setDocxValue(
                            "default_duration", pane.numberFrom(text, 1)
                        )
                    }
                    Label { text: qsTr("Разделители диапазона времени:") }
                    TextField {
                        Layout.fillWidth: true
                        text: Array.isArray(pane.docxConfiguration.time_separators)
                            ? pane.docxConfiguration.time_separators.join(" ") : "- – — |"
                        onEditingFinished: pane.setDocxValue(
                            "time_separators",
                            text.split(/\s+/).filter(function(value) { return value.length > 0 })
                        )
                    }
                }
            }

            GroupBox {
                title: qsTr("DOCX: порядок распознавания")
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 5

                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Если заголовок подходит нескольким полям, используется первое поле в списке.")
                        color: pane.softMuted
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: Array.isArray(pane.docxConfiguration.field_priority)
                            ? pane.docxConfiguration.field_priority
                            : ["character", "time_start", "time_end", "time_split", "text"]
                        delegate: RowLayout {
                            id: priorityRow
                            required property int index
                            required property string modelData
                            Layout.fillWidth: true
                            Label {
                                text: String(priorityRow.index + 1) + ". "
                                    + pane.docxFieldLabel(priorityRow.modelData)
                                Layout.fillWidth: true
                            }
                            ToolButton {
                                text: qsTr("↑")
                                enabled: priorityRow.index > 0
                                onClicked: pane.moveDocxPriority(
                                    priorityRow.index, -1
                                )
                                ToolTip.visible: hovered
                                ToolTip.text: qsTr("Поднять приоритет")
                            }
                            ToolButton {
                                text: qsTr("↓")
                                enabled: priorityRow.index < 4
                                onClicked: pane.moveDocxPriority(
                                    priorityRow.index, 1
                                )
                                ToolTip.visible: hovered
                                ToolTip.text: qsTr("Опустить приоритет")
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("DOCX: столбцы без заголовков")
                Layout.fillWidth: true

                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    Repeater {
                        model: [
                            "character", "time_start", "time_end",
                            "time_split", "text"
                        ]
                        delegate: RowLayout {
                            id: fallbackRow
                            required property string modelData
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Label {
                                text: pane.docxFieldLabel(fallbackRow.modelData)
                                Layout.fillWidth: true
                            }
                            SpinBox {
                                from: -1
                                to: 99
                                editable: true
                                value: {
                                    var mapping = pane.docxConfiguration.fallback_mapping || {}
                                    var item = mapping[fallbackRow.modelData]
                                    return item === null || item === undefined
                                        ? -1 : Number(item)
                                }
                                textFromValue: function(value) {
                                    return value < 0 ? "Не задан" : String(value + 1)
                                }
                                valueFromText: function(text) {
                                    var number = Number(text)
                                    return isNaN(number) ? -1 : number - 1
                                }
                                onValueModified: pane.setDocxFallback(
                                    fallbackRow.modelData, value
                                )
                            }
                        }
                    }
                    Label {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        text: qsTr("Номера показываются с единицы. «Не задан» отключает поле.")
                        color: pane.softMuted
                        wrapMode: Text.WordWrap
                    }
                }
            }

            GroupBox {
                title: qsTr("DOCX: названия столбцов")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    Label { text: qsTr("Персонаж:") }
                    TextField {
                        Layout.fillWidth: true
                        text: pane.aliasesText("character")
                        onEditingFinished: pane.setDocxAliases("character", text)
                    }
                    Label { text: qsTr("Начало:") }
                    TextField {
                        Layout.fillWidth: true
                        text: pane.aliasesText("time_start")
                        onEditingFinished: pane.setDocxAliases("time_start", text)
                    }
                    Label { text: qsTr("Конец:") }
                    TextField {
                        Layout.fillWidth: true
                        text: pane.aliasesText("time_end")
                        onEditingFinished: pane.setDocxAliases("time_end", text)
                    }
                    Label { text: qsTr("Диапазон времени:") }
                    TextField {
                        Layout.fillWidth: true
                        text: pane.aliasesText("time_split")
                        onEditingFinished: pane.setDocxAliases("time_split", text)
                    }
                    Label { text: qsTr("Текст реплики:") }
                    TextField {
                        Layout.fillWidth: true
                        text: pane.aliasesText("text")
                        onEditingFinished: pane.setDocxAliases("text", text)
                    }
                    Label {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        text: qsTr("Варианты разделяются запятыми. Префикс re: задаёт регулярное выражение.")
                        wrapMode: Text.WordWrap
                        color: pane.softMuted
                    }
                }
            }
        }
    }
}
