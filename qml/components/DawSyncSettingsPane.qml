pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PersistentScrollView {
    id: pane

    required property var configuration
    required property color softMuted
    required property var teleprompter
    readonly property bool isNuendo: configuration.sync_daw === "nuendo"

    Component.onCompleted: if (visible && isNuendo) teleprompter.refreshMidiPorts()
    onVisibleChanged: if (visible && isNuendo) teleprompter.refreshMidiPorts()
    onIsNuendoChanged: if (visible && isNuendo) teleprompter.refreshMidiPorts()

    function portChoices(kind, selected) {
        var choices = [{ label: qsTr("Выберите MIDI-порт"), value: "" }]
        if (teleprompter.midiSupportsVirtual)
            choices.push({ label: qsTr("Создать порт Dubbing Manager"), value: "__virtual__" })
        var names = teleprompter.midiPorts[kind] || []
        for (var i = 0; i < names.length; i++)
            choices.push({ label: names[i], value: names[i] })
        var found = choices.some(function(item) { return item.value === selected })
        if (selected && !found)
            choices.push({ label: (selected === "__virtual__" ? qsTr("Выберите порт для Windows") : selected + qsTr(" (недоступен)")), value: selected })
        return choices
    }

    function portIndex(choices, selected) {
        for (var i = 0; i < choices.length; i++)
            if (choices[i].value === selected)
                return i
        return 0
    }
    signal configEdited(var config)

    clip: true
    contentWidth: availableWidth

    function setValue(key, value) {
        var next = Object.assign({}, configuration)
        next[key] = value
        configEdited(next)
    }

    ColumnLayout {
        width: pane.availableWidth
        spacing: 14

        FormSection {
            title: qsTr("Запуск")
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 14
                rowSpacing: 8

                Label { text: qsTr("Синхронизировать с:") }
                ComboBox {
                    objectName: "syncDawSelector"
                    implicitContentWidthPolicy: ComboBox.WidestText
                    model: ["Reaper · OSC", "Nuendo · MIDI"]
                    currentIndex: pane.isNuendo ? 1 : 0
                    onActivated: pane.setValue("sync_daw", currentIndex === 1 ? "nuendo" : "reaper")
                }
                CheckBox {
                    text: qsTr("Включать синхронизацию при открытии телесуфлёра")
                    checked: Boolean(pane.configuration.osc_enabled)
                    onToggled: pane.setValue("osc_enabled", checked)
                    Layout.columnSpan: 2
                }
            }
        }

        FormSection {
            title: qsTr("OSC-подключение")
            visible: !pane.isNuendo
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 14
                rowSpacing: 8

                Label { text: qsTr("Dubbing Manager принимает:") }
                RowLayout {
                    SpinBox {
                        from: 1
                        to: 65535
                        editable: true
                        value: Number(pane.configuration.port_in || 8000)
                        onValueModified: pane.setValue("port_in", value)
                    }
                    Label { text: qsTr("UDP"); color: pane.softMuted }
                }

                Label { text: qsTr("Dubbing Manager отправляет:") }
                RowLayout {
                    SpinBox {
                        from: 1
                        to: 65535
                        editable: true
                        value: Number(pane.configuration.port_out || 9000)
                        onValueModified: pane.setValue("port_out", value)
                    }
                    Label { text: qsTr("UDP"); color: pane.softMuted }
                }
            }
        }

        FormSection {
            title: qsTr("Как настроить REAPER")
            visible: !pane.isNuendo
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 7

                Label {
                    Layout.fillWidth: true
                    text: qsTr("1. Откройте Options → Preferences → Control/OSC/Web.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("2. Нажмите Add и выберите OSC (Open Sound Control).")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("3. Для работы на одном компьютере укажите Device IP: 127.0.0.1.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("4. В Device port укажите порт «Dubbing Manager принимает» (сейчас ")
                        + Number(pane.configuration.port_in || 8000) + ")."
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("5. В Local listen port укажите порт «Dubbing Manager отправляет» (сейчас ")
                        + Number(pane.configuration.port_out || 9000) + ")."
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Оставьте Default.ReaperOSC как Pattern config. Если связь не запускается, проверьте, что эти UDP-порты не заняты другой программой.")
                    wrapMode: Text.WordWrap
                    color: pane.softMuted
                }
            }
        }

        FormSection {
            title: qsTr("MIDI-подключение Nuendo")
            visible: pane.isNuendo
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 14
                rowSpacing: 8

                Label { text: qsTr("Приём таймкода MTC:") }
                ComboBox {
                    id: midiInput
                    objectName: "midiInputSelector"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    model: pane.portChoices("inputs", pane.configuration.midi_input_port || "")
                    textRole: "label"
                    currentIndex: pane.portIndex(model, pane.configuration.midi_input_port || "")
                    onActivated: pane.setValue("midi_input_port", model[currentIndex].value)
                }
                Label { text: qsTr("Отправка переходов MMC:") }
                ComboBox {
                    id: midiOutput
                    objectName: "midiOutputSelector"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    model: pane.portChoices("outputs", pane.configuration.midi_output_port || "")
                    textRole: "label"
                    currentIndex: pane.portIndex(model, pane.configuration.midi_output_port || "")
                    onActivated: pane.setValue("midi_output_port", model[currentIndex].value)
                }
                Label { text: qsTr("Частота кадров проекта:") }
                ComboBox {
                    id: midiRate
                    objectName: "midiRateSelector"
                    implicitContentWidthPolicy: ComboBox.WidestText
                    readonly property var rates: ["24", "25", "29.97df", "30", "23.976", "29.97"]
                    model: ["24 fps", "25 fps", "29.97 fps · Drop Frame", "30 fps", "23.976 fps", "29.97 fps · Non-Drop"]
                    currentIndex: rates.indexOf(pane.configuration.midi_frame_rate || "25")
                    onActivated: pane.setValue("midi_frame_rate", rates[currentIndex])
                }
                Label { text: qsTr("MMC Device ID:") }
                SpinBox {
                    from: 0
                    to: 127
                    editable: true
                    value: Number(pane.configuration.midi_device_id === undefined ? 127 : pane.configuration.midi_device_id)
                    onValueModified: pane.setValue("midi_device_id", value)
                }
                Label { text: qsTr("Начало таймкода проекта:") }
                SpinBox {
                    objectName: "midiOriginSpinBox"
                    from: 0
                    to: 86399
                    stepSize: 3600
                    editable: true
                    value: Math.round(Number(pane.configuration.midi_timecode_origin_seconds || 0))
                    textFromValue: function(value) {
                        var hours = Math.floor(value / 3600)
                        var minutes = Math.floor(value / 60) % 60
                        var seconds = value % 60
                        return String(hours).padStart(2, "0") + ":" + String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0")
                    }
                    valueFromText: function(text) {
                        var parts = text.split(":")
                        if (parts.length !== 3)
                            return Number(text)
                        return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2])
                    }
                    Accessible.name: qsTr("Начало таймкода проекта Nuendo")
                    onValueModified: pane.setValue("midi_timecode_origin_seconds", value)
                }
                Button {
                    text: qsTr("Обновить MIDI-порты")
                    onClicked: pane.teleprompter.refreshMidiPorts()
                    Layout.columnSpan: 2
                }
                Label {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    visible: !pane.teleprompter.midiAvailable || Boolean(pane.teleprompter.midiPorts.error)
                    text: pane.teleprompter.midiPorts.error || qsTr("MIDI недоступен: установите python-rtmidi")
                    wrapMode: Text.WordWrap
                    color: pane.softMuted
                }
            }
        }

        FormSection {
            title: qsTr("Как настроить Nuendo")
            visible: pane.isNuendo
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 7
                Label {
                    Layout.fillWidth: true
                    text: pane.teleprompter.midiSupportsVirtual
                        ? qsTr("1. Выберите «Создать порт Dubbing Manager» в обоих направлениях. Сохраните настройки и откройте телесуфлёр: появится MIDI-порт Dubbing Manager MTC. Включите «DAW следует за навигацией», чтобы появился Dubbing Manager MMC.")
                        : qsTr("1. Создайте два отдельных порта в loopMIDI: Nuendo → Dubbing Manager и Dubbing Manager → Nuendo. Здесь выберите первый для MTC, второй для MMC. Для аппаратного подключения выберите соответствующие порты MIDI-интерфейса.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("2. В Nuendo откройте Transport → Project Synchronization Setup → Destinations. В MIDI Timecode Destinations выберите порт приёма MTC в Dubbing Manager. Включите MIDI Timecode Follows Project Time; Timecode Offset установите в 0.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("3. На странице Machine Control задайте Machine Control Input: MIDI Machine Control. В MIDI Input выберите порт отправки MMC из Dubbing Manager. Device ID должен совпадать; 127 в Dubbing Manager означает отправку всем устройствам.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("4. Оставьте Internal Timecode и выключите Activate External Sync. Частота кадров и начало таймкода здесь должны совпадать с Project Setup в Nuendo. Исключите эти MIDI-порты из All MIDI Inputs, чтобы они не записывались на музыкальные треки.")
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("В телесуфлёре включите нужные направления синхронизации. Nuendo должен передавать MTC Full Frame для переходов в режиме Stop; Quarter Frame используется во время воспроизведения. После прекращения MTC телесуфлёр считает воспроизведение остановленным.")
                    wrapMode: Text.WordWrap
                    color: pane.softMuted
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
