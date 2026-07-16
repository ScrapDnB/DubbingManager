pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: pane

    required property var configuration
    required property color softMuted
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

        Label {
            Layout.fillWidth: true
            text: qsTr("Синхронизация телесуфлёра и REAPER по OSC работает на этом компьютере для всех проектов.")
            wrapMode: Text.WordWrap
            color: pane.softMuted
        }

        GroupBox {
            title: qsTr("Подключение")
            Layout.fillWidth: true

            GridLayout {
                anchors.fill: parent
                columns: 2
                columnSpacing: 14
                rowSpacing: 8

                CheckBox {
                    text: qsTr("Включать OSC при открытии телесуфлёра")
                    checked: Boolean(pane.configuration.osc_enabled)
                    onToggled: pane.setValue("osc_enabled", checked)
                    Layout.columnSpan: 2
                }
                CheckBox {
                    text: qsTr("Телесуфлёр следует за позицией REAPER")
                    checked: Boolean(pane.configuration.sync_in)
                    onToggled: pane.setValue("sync_in", checked)
                    Layout.columnSpan: 2
                }
                CheckBox {
                    text: qsTr("Навигация телесуфлёра управляет REAPER")
                    checked: Boolean(pane.configuration.sync_out)
                    onToggled: pane.setValue("sync_out", checked)
                    Layout.columnSpan: 2
                }

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

                CheckBox {
                    id: offsetEnabled
                    text: qsTr("Корректировать позицию перед отправкой")
                    checked: Boolean(pane.configuration.reaper_offset_enabled)
                    onToggled: pane.setValue("reaper_offset_enabled", checked)
                    Layout.columnSpan: 2
                }
                Label {
                    text: qsTr("Смещение:")
                    enabled: offsetEnabled.checked
                }
                RowLayout {
                    enabled: offsetEnabled.checked
                    SpinBox {
                        from: -600
                        to: 600
                        stepSize: 1
                        editable: true
                        value: Math.round(Number(
                            pane.configuration.reaper_offset_seconds === undefined
                                ? -2 : pane.configuration.reaper_offset_seconds
                        ) * 10)
                        textFromValue: function(value) {
                            return (value / 10).toFixed(1)
                        }
                        valueFromText: function(text) {
                            return Math.round(Number(text.replace(",", ".")) * 10)
                        }
                        onValueModified: pane.setValue(
                            "reaper_offset_seconds", value / 10
                        )
                    }
                    Label { text: qsTr("сек"); color: pane.softMuted }
                }
            }
        }

        GroupBox {
            title: qsTr("Как настроить REAPER")
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

        Item { Layout.fillHeight: true }
    }
}
