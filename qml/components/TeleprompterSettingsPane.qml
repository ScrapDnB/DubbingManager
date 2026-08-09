pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

PersistentScrollView {
    id: pane

    required property var configuration
    signal configEdited(var config)

    function scrollSmoothnessLevel() {
        return Math.round(Math.max(0, Math.min(
            100, Number(pane.configuration.scroll_smoothness_slider || 0)
        )))
    }
    property string colorTarget: ""
    property string colorOriginalValue: ""
    property bool globalScope: false
    property bool appearanceScope: true
    property bool automationScope: true
    readonly property var layoutTypes: [
        "Сценарий 1", "Сценарий 2", "Сценарий 3"
    ]

    clip: true
    contentWidth: availableWidth

    function setValue(key, value) {
        var next = Object.assign({}, configuration)
        next[key] = value
        configEdited(next)
    }

    function setLayout(layoutType) {
        var next = Object.assign({}, configuration)
        var profiles = Object.assign({}, next.layout_font_sizes || {})
        var profile = Object.assign({}, profiles[layoutType] || {})
        next.layout_type = layoutType
        var fontKeys = ["f_tc", "f_char", "f_actor", "f_text"]
        for (var index = 0; index < fontKeys.length; ++index) {
            var key = fontKeys[index]
            next[key] = Number(profile[key] || {
                f_tc: 20, f_char: 24, f_actor: 18, f_text: 36
            }[key])
        }
        configEdited(next)
    }

    function setLayoutFontSize(key, value) {
        var next = Object.assign({}, configuration)
        var layoutType = next.layout_type || "Сценарий 1"
        var profiles = Object.assign({}, next.layout_font_sizes || {})
        var profile = Object.assign({}, profiles[layoutType] || {})
        profile[key] = value
        profiles[layoutType] = profile
        next.layout_font_sizes = profiles
        next[key] = value
        configEdited(next)
    }

    function setColor(key, value) {
        var next = Object.assign({}, configuration)
        var colors = Object.assign({}, next.colors || {})
        colors[key] = value
        next.colors = colors
        configEdited(next)
    }

    function targetHighlightOpacity() {
        var raw = configuration.page_target_highlight_opacity
        var value = raw === undefined ? 0.22 : Number(raw)
        return Math.max(0, Math.min(0.44, value))
    }

    function targetHighlightBrightnessPercent() {
        return Math.round(targetHighlightOpacity() / 0.44 * 100)
    }

    function setTargetHighlightBrightness(percent) {
        setValue(
            "page_target_highlight_opacity",
            Math.max(0, Math.min(0.44, percent * 0.0044))
        )
    }

    ColorDialog {
        id: colorDialog
        title: qsTr("Цвет телесуфлёра")
        property bool previewActive: false
        onSelectedColorChanged: {
            if (previewActive) {
                pane.setColor(pane.colorTarget, selectedColor.toString())
            }
        }
        onAccepted: {
            previewActive = false
            pane.setColor(pane.colorTarget, selectedColor.toString())
        }
        onRejected: {
            previewActive = false
            pane.setColor(pane.colorTarget, pane.colorOriginalValue)
        }
    }

    ColumnLayout {
        width: pane.availableWidth
        spacing: 10

        FormSection {
            visible: pane.appearanceScope
            title: qsTr("Отображение")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 3
                CheckBox { text: qsTr("Зеркально"); checked: Boolean(pane.configuration.is_mirrored); onToggled: pane.setValue("is_mirrored", checked) }
                CheckBox { text: qsTr("Показывать заголовок"); checked: Boolean(pane.configuration.show_header); onToggled: pane.setValue("show_header", checked) }
                Label { text: qsTr("Позиция фокуса: ") + Math.round(Number(pane.configuration.focus_ratio || 0.5) * 100) + "%"; Layout.columnSpan: 2 }
                Slider { from: 0.1; to: 0.9; value: Number(pane.configuration.focus_ratio || 0.5); onMoved: pane.setValue("focus_ratio", value); Layout.fillWidth: true }
            }
        }

        FormSection {
            visible: pane.automationScope
            title: qsTr("Автопрокрутка")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 3
                CheckBox {
                    text: qsTr("Постраничный режим")
                    checked: Boolean(pane.configuration.page_scroll_mode)
                    onToggled: pane.setValue("page_scroll_mode", checked)
                    Layout.columnSpan: 3
                }
                Label { text: qsTr("Уровень плавности: %1%").arg(pane.scrollSmoothnessLevel()); Layout.columnSpan: 2 }
                Slider { from: 0; to: 100; value: pane.configuration.scroll_smoothness_slider === undefined ? 18 : Number(pane.configuration.scroll_smoothness_slider); onMoved: pane.setValue("scroll_smoothness_slider", Math.round(value)); Layout.fillWidth: true }
                CheckBox {
                    text: qsTr("Показывать диагностику постраничного режима")
                    checked: Boolean(pane.configuration.page_debug_overlay)
                    onToggled: pane.setValue("page_debug_overlay", checked)
                    Layout.columnSpan: 3
                }
            }
        }

        FormSection {
            visible: pane.automationScope
                && Boolean(pane.configuration.page_scroll_mode)
            title: qsTr("Паузы в постраничном режиме")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 14
                rowSpacing: 8

                Label { text: qsTr("Считать паузой интервал от:") }
                RowLayout {
                    SpinBox {
                        from: 0
                        to: 600
                        stepSize: 1
                        editable: true
                        value: Math.round(Number(
                            pane.configuration.page_gap_prefetch_seconds === undefined
                                ? 1 : pane.configuration.page_gap_prefetch_seconds
                        ) * 10)
                        textFromValue: function(value) {
                            return (value / 10).toFixed(1)
                        }
                        valueFromText: function(text) {
                            return Math.round(Number.fromLocaleString(locale, text) * 10)
                        }
                        onValueModified: pane.setValue(
                            "page_gap_prefetch_seconds", value / 10
                        )
                    }
                    Label { text: qsTr("с") }
                }
                Label { text: qsTr("Подтягивать следующую реплику через:") }
                RowLayout {
                    SpinBox {
                        from: 0
                        to: 600
                        stepSize: 1
                        editable: true
                        value: Math.round(Number(
                            pane.configuration.page_gap_prefetch_delay_seconds === undefined
                                ? 1 : pane.configuration.page_gap_prefetch_delay_seconds
                        ) * 10)
                        textFromValue: function(value) {
                            return (value / 10).toFixed(1)
                        }
                        valueFromText: function(text) {
                            return Math.round(Number.fromLocaleString(locale, text) * 10)
                        }
                        onValueModified: pane.setValue(
                            "page_gap_prefetch_delay_seconds", value / 10
                        )
                    }
                    Label { text: qsTr("с") }
                }
            }
        }

        FormSection {
            visible: pane.globalScope && pane.appearanceScope
            title: qsTr("Разметка")
            Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Label { text: qsTr("Сценарий") }
                    PlatformComboBox {
                        Layout.fillWidth: true
                        model: pane.layoutTypes
                        currentIndex: Math.max(
                            0, pane.layoutTypes.indexOf(
                                String(pane.configuration.layout_type || "Сценарий 1")
                            )
                        )
                        onActivated: pane.setLayout(currentText)
                    }
                }

                CollapsibleSection {
                    title: qsTr("Элементы")
                    expanded: true
                    Layout.fillWidth: true

                    CheckBox {
                        text: qsTr("Таймкод")
                        checked: Boolean(pane.configuration.show_timecode)
                        onToggled: pane.setValue("show_timecode", checked)
                    }
                    CheckBox {
                        text: qsTr("Окончание реплики")
                        checked: Boolean(pane.configuration.show_end_timecode)
                        enabled: Boolean(pane.configuration.show_timecode)
                        onToggled: pane.setValue(
                            "show_end_timecode", checked
                        )
                    }
                    CheckBox {
                        text: qsTr("Персонаж")
                        checked: Boolean(pane.configuration.show_character)
                        onToggled: pane.setValue("show_character", checked)
                    }
                    CheckBox {
                        text: qsTr("Актёр")
                        checked: Boolean(pane.configuration.show_actor)
                        onToggled: pane.setValue("show_actor", checked)
                    }
                    CheckBox {
                        text: qsTr("Реплика")
                        checked: Boolean(pane.configuration.show_replica)
                        onToggled: pane.setValue("show_replica", checked)
                    }
                    CheckBox {
                        text: qsTr("Границы блоков")
                        checked: Boolean(pane.configuration.show_block_borders)
                        onToggled: pane.setValue("show_block_borders", checked)
                    }
                    CheckBox {
                        text: qsTr("Скрывать нули")
                        checked: Boolean(pane.configuration.hide_leading_timecode_zeros)
                        onToggled: pane.setValue("hide_leading_timecode_zeros", checked)
                    }
                }
            }
        }

        FormSection {
            visible: pane.globalScope && pane.appearanceScope
            title: qsTr("Размер текста")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Label { text: qsTr("Таймкод") }
                SpinBox { from: 10; to: 150; value: Number(pane.configuration.f_tc || 20); onValueModified: pane.setLayoutFontSize("f_tc", value) }
                Label { text: qsTr("Персонаж") }
                SpinBox { from: 10; to: 150; value: Number(pane.configuration.f_char || 24); onValueModified: pane.setLayoutFontSize("f_char", value) }
                Label { text: qsTr("Актёр") }
                SpinBox { from: 10; to: 150; value: Number(pane.configuration.f_actor || 18); onValueModified: pane.setLayoutFontSize("f_actor", value) }
                Label { text: qsTr("Реплика") }
                SpinBox { from: 10; to: 300; value: Number(pane.configuration.f_text || 36); onValueModified: pane.setLayoutFontSize("f_text", value) }
            }
        }

        FormSection {
            visible: pane.appearanceScope
            title: qsTr("Цветовая схема")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Repeater {
                    model: [
                        { key: "bg", label: "Фон" },
                        { key: "active_text", label: "Активный текст" },
                        { key: "inactive_text", label: "Неактивный текст" },
                        { key: "tc", label: "Таймкод" },
                        { key: "actor", label: "Актёр" },
                        { key: "header_text", label: "Текст заголовка" },
                        { key: "block_border", label: "Границы блоков" },
                        { key: "page_target_highlight", label: "Подсветка прокрутки" }
                    ]
                    delegate: RowLayout {
                        id: colorRow
                        required property var modelData
                        Layout.columnSpan: 2
                        Label { text: colorRow.modelData.label; Layout.fillWidth: true }
                        AdaptiveButton {
                            id: colorButton
                            text: qsTr("")
                            implicitWidth: 42
                            Rectangle {
                                anchors.centerIn: parent
                                width: 26
                                height: 14
                                color: (pane.configuration.colors || {})[
                                    colorRow.modelData.key
                                ] || "#000000"
                                border.color: palette.mid
                                radius: 2
                            }
                            onClicked: {
                                colorDialog.previewActive = false
                                pane.colorTarget = colorRow.modelData.key
                                pane.colorOriginalValue = (pane.configuration.colors || {})[
                                    colorRow.modelData.key
                                ] || "#000000"
                                colorDialog.selectedColor = pane.colorOriginalValue
                                colorDialog.previewActive = true
                                colorDialog.open()
                            }
                            PlatformToolTip {
                                target: colorButton
                                text: colorRow.modelData.label
                            }
                        }
                    }
                }

                CheckBox {
                    id: pageTargetHighlightEnabled
                    Layout.columnSpan: 4
                    text: qsTr("Подсвечивать цель при перемотке")
                    checked: Boolean(
                        pane.configuration.page_target_highlight_enabled
                    )
                    onToggled: pane.setValue(
                        "page_target_highlight_enabled", checked
                    )
                }
                Label {
                    Layout.columnSpan: 4
                    Layout.fillWidth: true
                    enabled: pageTargetHighlightEnabled.checked
                    text: qsTr("Яркость подсветки: %1%").arg(
                        pane.targetHighlightBrightnessPercent()
                    )
                }
                Slider {
                    Layout.columnSpan: 4
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    stepSize: 1
                    enabled: pageTargetHighlightEnabled.checked
                    value: pane.targetHighlightBrightnessPercent()
                    onMoved: pane.setTargetHighlightBrightness(value)
                    PlatformToolTip {
                        target: parent
                        text: qsTr("0% — полностью прозрачная, 100% — наиболее заметная")
                    }
                }
                Label {
                    Layout.columnSpan: 2
                    text: qsTr("Время угасания:")
                    enabled: pageTargetHighlightEnabled.checked
                }
                RowLayout {
                    Layout.columnSpan: 2
                    enabled: pageTargetHighlightEnabled.checked

                    SpinBox {
                        from: 0
                        to: 10000
                        stepSize: 100
                        editable: true
                        value: Number(
                            pane.configuration.page_target_highlight_fade_ms
                                === undefined
                                ? 1000
                                : pane.configuration.page_target_highlight_fade_ms
                        )
                        onValueModified: pane.setValue(
                            "page_target_highlight_fade_ms", value
                        )
                    }
                    Label { text: qsTr("мс") }
                }
            }
        }

        FormSection {
            visible: pane.automationScope
            title: qsTr("Навигация")
            Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent
                columns: 4
                Label { text: qsTr("Предыдущая:") }
                TextField { text: String(pane.configuration.key_prev || "Left"); onEditingFinished: pane.setValue("key_prev", text); Layout.fillWidth: true }
                Label { text: qsTr("Следующая:") }
                TextField { text: String(pane.configuration.key_next || "Right"); onEditingFinished: pane.setValue("key_next", text); Layout.fillWidth: true }
            }
        }

    }
}
