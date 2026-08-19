pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PersistentScrollView {
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

        FormSection {
            title: qsTr("Запуск")
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
            }
        }

        FormSection {
            title: qsTr("OSC-подключение")
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
