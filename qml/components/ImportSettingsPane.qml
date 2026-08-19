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
        next.merge_gap_seconds = Math.max(0, value)
        mergeEdited(next)
    }

    function commitPendingMergeEdits() {
        // A button click does not reliably emit editingFinished for the field
        // that still owns focus. Read every visible value synchronously before
        // the settings dialog sends its draft to Python.
        var next = Object.assign({}, mergeConfiguration)
        var gapFallback = Number(next.merge_gap_seconds ?? 4.8)
        var gapSeconds = Math.max(
            0, numberFrom(mergeGapField.text, gapFallback)
        )
        next.merge = mergeEnabledCheck.checked
        next.merge_parallel_replicas = mergeParallelCheck.checked
        next.respect_existing_separators =
            respectExistingSeparatorsCheck.checked
        next.merge_gap_seconds = gapSeconds
        next.p_short = Math.max(
            0, numberFrom(shortPauseField.text, Number(next.p_short ?? 0.5))
        )
        next.p_long = Math.max(
            0, numberFrom(longPauseField.text, Number(next.p_long ?? 2))
        )
        next.inline_timecodes_enabled = inlineTimecodesCheck.checked
        next.inline_timecode_brackets = String(
            inlineTimecodeBracketsCombo.currentValue || "square"
        )
        next.inline_timecode_min_duration = Math.max(
            0,
            numberFrom(
                inlineTimecodeDurationField.text,
                Number(next.inline_timecode_min_duration ?? 30)
            )
        )
        next.inline_timecode_every = Math.max(
            1,
            Math.round(numberFrom(
                inlineTimecodeEveryField.text,
                Number(next.inline_timecode_every ?? 3)
            ))
        )
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
                text: qsTr("Глобальные правила объединения управляют отображением реплик во всех динамических проектах и применяются на лету. FPS хранится отдельно в настройках проекта. Параметры ASS, SRT и DOCX используются только при разборе исходников.")
                wrapMode: Text.WordWrap
                color: pane.softMuted
            }

            FormSection {
                title: qsTr("Объединение реплик")
                Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 6

                    CheckBox {
                        id: mergeEnabledCheck
                        text: qsTr("Объединять близкие реплики одного персонажа")
                        checked: Boolean(pane.mergeConfiguration.merge)
                        Layout.columnSpan: 2
                        onToggled: pane.setMergeValue("merge", checked)
                    }
                    CheckBox {
                        id: mergeParallelCheck
                        text: qsTr("Не разрывать реплики параллельными репликами других персонажей")
                        checked: Boolean(
                            pane.mergeConfiguration.merge_parallel_replicas
                        )
                        enabled: mergeEnabledCheck.checked
                        Layout.columnSpan: 2
                        onToggled: pane.setMergeValue(
                            "merge_parallel_replicas", checked
                        )
                    }
                    CheckBox {
                        id: respectExistingSeparatorsCheck
                        text: qsTr("Учитывать уже имеющиеся разделители")
                        checked: Boolean(
                            pane.mergeConfiguration.respect_existing_separators
                        )
                        enabled: mergeEnabledCheck.checked
                        Layout.columnSpan: 2
                        onToggled: pane.setMergeValue(
                            "respect_existing_separators", checked
                        )
                    }
                    Label { text: qsTr("Порог объединения, сек:") }
                    TextField {
                        id: mergeGapField
                        Layout.preferredWidth: 120
                        text: String(
                            pane.mergeConfiguration.merge_gap_seconds ?? 4.8
                        )
                        validator: DoubleValidator { bottom: 0; top: 10; decimals: 3 }
                        onEditingFinished: pane.setGapSeconds(
                            pane.numberFrom(text, 4.8)
                        )
                    }
                    Label { text: qsTr("Пауза для '/', сек:") }
                    TextField {
                        id: shortPauseField
                        Layout.preferredWidth: 120
                        text: String(pane.mergeConfiguration.p_short ?? 0.5)
                        validator: DoubleValidator { bottom: 0; top: 5; decimals: 3 }
                        onEditingFinished: pane.setMergeValue(
                            "p_short", pane.numberFrom(text, 0.5)
                        )
                    }
                    Label { text: qsTr("Пауза для '//', сек:") }
                    TextField {
                        id: longPauseField
                        Layout.preferredWidth: 120
                        text: String(pane.mergeConfiguration.p_long ?? 2)
                        validator: DoubleValidator { bottom: 0; top: 10; decimals: 3 }
                        onEditingFinished: pane.setMergeValue(
                            "p_long", pane.numberFrom(text, 2)
                        )
                    }
                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        CheckBox {
                            id: inlineTimecodesCheck
                            text: qsTr("Тайм-коды внутри длинных объединённых реплик")
                            checked: Boolean(
                                pane.mergeConfiguration.inline_timecodes_enabled
                            )
                            enabled: mergeEnabledCheck.checked
                            onToggled: pane.setMergeValue(
                                "inline_timecodes_enabled", checked
                            )
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: qsTr("Скобки:")
                            enabled: inlineTimecodesCheck.checked
                                || mergeParallelCheck.checked
                        }
                        PlatformComboBox {
                            id: inlineTimecodeBracketsCombo
                            Layout.preferredWidth: 92
                            enabled: inlineTimecodesCheck.checked
                                || mergeParallelCheck.checked
                            model: [
                                { label: "[ ]", value: "square" },
                                { label: "( )", value: "round" },
                                { label: "{ }", value: "curly" }
                            ]
                            textRole: "label"
                            valueRole: "value"
                            currentIndex: {
                                var style = String(
                                    pane.mergeConfiguration.inline_timecode_brackets
                                    || "square"
                                )
                                return style === "round" ? 1
                                    : (style === "curly" ? 2 : 0)
                            }
                            onActivated: pane.setMergeValue(
                                "inline_timecode_brackets", currentValue
                            )
                        }
                    }
                    Label {
                        text: qsTr("Если реплика длиннее, сек:")
                        enabled: inlineTimecodesCheck.checked
                    }
                    TextField {
                        id: inlineTimecodeDurationField
                        Layout.preferredWidth: 120
                        enabled: inlineTimecodesCheck.checked
                        text: String(
                            pane.mergeConfiguration.inline_timecode_min_duration
                            ?? 30
                        )
                        validator: DoubleValidator {
                            bottom: 0
                            top: 86400
                            decimals: 3
                        }
                        onEditingFinished: pane.setMergeValue(
                            "inline_timecode_min_duration",
                            pane.numberFrom(text, 30)
                        )
                    }
                    Label {
                        text: qsTr("Интервал, исходных реплик:")
                        enabled: inlineTimecodesCheck.checked
                    }
                    TextField {
                        id: inlineTimecodeEveryField
                        Layout.preferredWidth: 120
                        enabled: inlineTimecodesCheck.checked
                        text: String(
                            pane.mergeConfiguration.inline_timecode_every ?? 3
                        )
                        validator: IntValidator { bottom: 1; top: 1000 }
                        onEditingFinished: pane.setMergeValue(
                            "inline_timecode_every",
                            Math.max(1, Math.round(pane.numberFrom(text, 3)))
                        )
                    }
                    Label {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        text: qsTr("Настройки внутренних тайм-кодов глобальны и не записываются в файл проекта.")
                        wrapMode: Text.WordWrap
                        color: pane.softMuted
                        visible: inlineTimecodesCheck.checked
                    }
                }
            }

            FormSection {
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

            FormSection {
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

            FormSection {
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
                    AdaptiveButton {
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
                        AdaptiveButton {
                            text: qsTr("Сохранить")
                            enabled: docxPresetName.text.trim().length > 0
                            onClicked: pane.saveDocxPresetRequested(
                                docxPresetName.text.trim(),
                                pane.docxConfiguration
                            )
                        }
                        AdaptiveButton {
                            text: qsTr("Удалить")
                            enabled: docxPresetCombo.currentIndex >= 0
                            onClicked: pane.deleteDocxPresetRequested(
                                String(docxPresetCombo.currentValue || "")
                            )
                        }
                    }
                }
            }

            FormSection {
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

            FormSection {
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
                                id: movePriorityUpButton
                                text: qsTr("↑")
                                enabled: priorityRow.index > 0
                                onClicked: pane.moveDocxPriority(
                                    priorityRow.index, -1
                                )
                                PlatformToolTip {
                                    target: movePriorityUpButton
                                    text: qsTr("Поднять приоритет")
                                }
                            }
                            ToolButton {
                                id: movePriorityDownButton
                                text: qsTr("↓")
                                enabled: priorityRow.index < 4
                                onClicked: pane.moveDocxPriority(
                                    priorityRow.index, 1
                                )
                                PlatformToolTip {
                                    target: movePriorityDownButton
                                    text: qsTr("Опустить приоритет")
                                }
                            }
                        }
                    }
                }
            }

            FormSection {
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

            FormSection {
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
