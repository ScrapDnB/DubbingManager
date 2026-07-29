pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: pane

    property var columnOrder: []
    property var hiddenColumns: []
    property var widthModes: ({})
    property bool compactRows: false
    property bool timelineVisible: true
    property bool timelineActorColors: true
    property int timelineColorMuteLevel: 2
    property string timelinePlacement: "table"
    property int timelineHeight: 180
    property string timelineSortMode: "appearance"
    signal configurationChanged(
        var order, var hidden, var widths, bool compact, bool timeline,
        bool timelineActorColors, int timelineColorMuteLevel,
        string timelinePlacement, int timelineHeight, string timelineSortMode
    )

    readonly property var availableColumns: [
        { key: "character", title: qsTr("Персонаж"), mandatory: true },
        { key: "lines", title: qsTr("Строк") },
        { key: "rings", title: qsTr("Колец") },
        { key: "words", title: qsTr("Слов") },
        { key: "scope", title: qsTr("Область") },
        { key: "actor", title: qsTr("Актёр") },
        { key: "preview", title: qsTr("Просмотр") }
    ]

    function titleFor(key) {
        for (var i = 0; i < availableColumns.length; ++i)
            if (availableColumns[i].key === key)
                return availableColumns[i].title
        return key
    }

    function isMandatory(key) { return key === "character" }

    function emitConfiguration() {
        configurationChanged(
            columnOrder, hiddenColumns, widthModes, compactRows, timelineVisible,
            timelineActorColors, timelineColorMuteLevel,
            timelinePlacement, timelineHeight, timelineSortMode
        )
    }

    function timelineSortIndex(mode) {
        if (mode === "words") return 1
        if (mode === "lines") return 2
        if (mode === "name") return 3
        return 0
    }

    function timelineSortValue(index) {
        return ["appearance", "words", "lines", "name"][Math.max(0, index)]
    }

    function moveColumn(index, offset) {
        var destination = index + offset
        if (destination < 0 || destination >= columnOrder.length)
            return
        var next = columnOrder.slice(0)
        var item = next.splice(index, 1)[0]
        next.splice(destination, 0, item)
        columnOrder = next
        emitConfiguration()
    }

    function setVisible(key, visible) {
        var next = hiddenColumns.filter(function(item) { return item !== key })
        if (!visible)
            next.push(key)
        hiddenColumns = next
        emitConfiguration()
    }

    function setWidth(key, value) {
        var next = Object.assign({}, widthModes)
        next[key] = value
        widthModes = next
        emitConfiguration()
    }

    spacing: 10

    CollapsibleSection {
        Layout.fillWidth: true
        title: qsTr("Колонки главной таблицы")
        expanded: false

        Label {
            Layout.fillWidth: true
            text: qsTr("Порядок, состав и ширина колонок сохраняются для этого компьютера.")
            wrapMode: Text.WordWrap
            color: palette.placeholderText
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Repeater {
                model: pane.columnOrder

                delegate: RowLayout {
                    required property string modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 6

                    CheckBox {
                        text: pane.titleFor(modelData)
                        checked: pane.hiddenColumns.indexOf(modelData) < 0
                        enabled: !pane.isMandatory(modelData)
                        onToggled: pane.setVisible(modelData, checked)
                    }
                    Item { Layout.fillWidth: true }
                    PlatformComboBox {
                        Layout.preferredWidth: 116
                        model: [qsTr("Узкая"), qsTr("Обычная"), qsTr("Широкая")]
                        currentIndex: Number(pane.widthModes[modelData] || 0) + 1
                        onActivated: pane.setWidth(modelData, currentIndex - 1)
                    }
                    ToolButton {
                        text: "‹"
                        implicitWidth: 26
                        implicitHeight: 26
                        enabled: index > 0
                        onClicked: pane.moveColumn(index, -1)
                        PlatformToolTip {
                            target: parent
                            text: qsTr("Переместить левее")
                        }
                    }
                    ToolButton {
                        text: "›"
                        implicitWidth: 26
                        implicitHeight: 26
                        enabled: index < pane.columnOrder.length - 1
                        onClicked: pane.moveColumn(index, 1)
                        PlatformToolTip {
                            target: parent
                            text: qsTr("Переместить правее")
                        }
                    }
                }
            }
        }
    }

    Label {
        text: qsTr("Таймлайн серии")
        font.bold: true
    }

    RowLayout {
        Layout.fillWidth: true
        enabled: pane.timelineVisible && pane.timelineActorColors

        Label { text: qsTr("Яркость блоков") }
        Rectangle {
            Layout.preferredWidth: 10
            Layout.preferredHeight: 10
            radius: width / 2
            color: pane.palette.highlight
            opacity: 0.20
        }
        Rectangle {
            Layout.preferredWidth: 10
            Layout.preferredHeight: 10
            radius: width / 2
            color: pane.palette.highlight
            opacity: 0.55
        }
        Rectangle {
            Layout.preferredWidth: 10
            Layout.preferredHeight: 10
            radius: width / 2
            color: pane.palette.highlight
        }
        Slider {
            id: timelineColorMuteSlider
            Layout.preferredWidth: 86
            from: 0
            to: 2
            stepSize: 1
            snapMode: Slider.SnapAlways
            value: 2 - pane.timelineColorMuteLevel
            onMoved: {
                pane.timelineColorMuteLevel = 2 - Math.round(value)
                pane.emitConfiguration()
            }
            PlatformToolTip {
                target: timelineColorMuteSlider
                text: timelineColorMuteSlider.value >= 2
                    ? qsTr("Яркие цвета")
                    : timelineColorMuteSlider.value > 0
                        ? qsTr("Умеренно приглушённые цвета")
                        : qsTr("Приглушённые цвета")
            }
        }
        Item { Layout.fillWidth: true }
    }
    CheckBox {
        text: qsTr("Окрашивать блоки в цвета актёров")
        checked: pane.timelineActorColors
        enabled: pane.timelineVisible
        onToggled: {
            pane.timelineActorColors = checked
            pane.emitConfiguration()
        }
    }
    RowLayout {
        Layout.fillWidth: true
        enabled: pane.timelineVisible
        Label { text: qsTr("Сортировка дорожек") }
        PlatformComboBox {
            Layout.preferredWidth: 230
            model: [
                qsTr("По появлению в серии"),
                qsTr("По количеству слов"),
                qsTr("По количеству реплик"),
                qsTr("По имени актёра")
            ]
            currentIndex: pane.timelineSortIndex(pane.timelineSortMode)
            onActivated: {
                pane.timelineSortMode = pane.timelineSortValue(currentIndex)
                pane.emitConfiguration()
            }
        }
        Item { Layout.fillWidth: true }
    }
    RowLayout {
        Layout.fillWidth: true
        enabled: pane.timelineVisible
        Label { text: qsTr("Расположение") }
        PlatformComboBox {
            Layout.preferredWidth: 230
            model: [qsTr("Под главной таблицей"), qsTr("Внизу окна")]
            currentIndex: pane.timelinePlacement === "bottom" ? 1 : 0
            onActivated: {
                pane.timelinePlacement = currentIndex === 1 ? "bottom" : "table"
                pane.emitConfiguration()
            }
        }
        Item { Layout.fillWidth: true }
    }
    Label {
        Layout.fillWidth: true
        enabled: pane.timelineVisible
        text: qsTr("Высота изменяется перетаскиванием верхней границы таймлайна.")
        wrapMode: Text.WordWrap
        color: pane.palette.placeholderText
    }
    CheckBox {
        text: qsTr("Показывать таймлайн серии")
        checked: pane.timelineVisible
        onToggled: {
            pane.timelineVisible = checked
            pane.emitConfiguration()
        }
    }
}
