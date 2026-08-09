pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted

    property string actorColorDisplayMode: "marker"
    property int actorColorMuteLevel: 2
    property bool actorColorCellFillFullHeight: false
    property int actorMarkerShape: 0
    property int actorMarkerSize: 0
    property int uiScalePercent: 75
    property string characterColumnsOrder: "[]"
    property string characterColumnsHidden: "[]"
    property string characterColumnWidths: "{}"
    property bool characterCompactRows: false
    property bool episodeTimelineVisible: true
    property bool episodeTimelineActorColors: true
    property int episodeTimelineColorMuteLevel: 2
    property string episodeTimelinePlacement: "table"
    property int episodeTimelineHeight: 180
    property string episodeTimelineSortMode: "appearance"

    property int currentStep: 0
    property bool firstRun: false
    property string actorColorDisplayDraft: "marker"
    property int actorColorMuteLevelDraft: 2
    property bool actorColorCellFillFullHeightDraft: false
    property int actorMarkerShapeDraft: 0
    property int actorMarkerSizeDraft: 0
    property int uiScalePercentDraft: 75
    property var characterColumnsOrderDraft: []
    property var characterColumnsHiddenDraft: []
    property var characterColumnWidthsDraft: ({})
    property bool characterCompactRowsDraft: false
    property bool episodeTimelineVisibleDraft: true
    property bool episodeTimelineActorColorsDraft: true
    property int episodeTimelineColorMuteLevelDraft: 2
    property string episodeTimelinePlacementDraft: "table"
    property int episodeTimelineHeightDraft: 180
    property string episodeTimelineSortModeDraft: "appearance"

    readonly property var steps: [
        qsTr("Добро пожаловать"),
        qsTr("Плотность"),
        qsTr("Цвета актёров"),
        qsTr("Главная таблица"),
        qsTr("Таймлайн"),
        qsTr("Готово")
    ]
    readonly property var columnDefinitions: [
        { key: "character", title: qsTr("Персонаж"), mandatory: true },
        { key: "lines", title: qsTr("Строк") },
        { key: "rings", title: qsTr("Колец") },
        { key: "words", title: qsTr("Слов") },
        { key: "scope", title: qsTr("Область") },
        { key: "actor", title: qsTr("Актёр") },
        { key: "preview", title: qsTr("Просмотр") }
    ]
    readonly property int lastStep: steps.length - 1

    signal configurationAccepted(
        string mode, int muteLevel, bool fullHeight, int markerShape,
        int markerSize, int scalePercent, string order, string hidden,
        string widths, bool compact, bool timelineVisible,
        bool timelineActorColors, int timelineColorMuteLevel,
        string timelinePlacement, int timelineHeight, string timelineSortMode
    )

    modal: true
    title: qsTr("Добро пожаловать в Dubbing Manager")
    standardButtons: Dialog.NoButton
    width: boundedWidth(900, 32)
    height: boundedHeight(650, 32)
    minimumWidth: 680
    minimumHeight: 540

    SystemPalette {
        id: systemPalette
        colorGroup: SystemPalette.Active
    }

    component SelectionCard: Item {
        id: card
        property string title: ""
        property string subtitle: ""
        property bool selected: false
        signal chosen()

        implicitHeight: 88
        opacity: enabled ? 1 : 0.55
        Accessible.role: Accessible.RadioButton
        Accessible.name: title
        Accessible.description: subtitle
        Accessible.checked: selected

        Rectangle {
            anchors.fill: parent
            radius: dialog.macOSStyle ? 10 : 6
            color: card.selected
                ? Qt.rgba(
                    systemPalette.highlight.r,
                    systemPalette.highlight.g,
                    systemPalette.highlight.b,
                    dialog.darkPalette ? 0.22 : 0.11
                )
                : cardMouse.containsMouse && card.enabled
                    ? Qt.rgba(
                        systemPalette.text.r,
                        systemPalette.text.g,
                        systemPalette.text.b,
                        0.045
                    )
                    : systemPalette.base
            border.width: card.selected ? 2 : 1
            border.color: card.selected ? systemPalette.highlight : dialog.softBorder
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10

            RadioButton {
                checked: card.selected
                enabled: card.enabled
                onClicked: card.chosen()
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Label {
                    Layout.fillWidth: true
                    text: card.title
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    text: card.subtitle
                    color: dialog.softMuted
                    wrapMode: Text.WordWrap
                }
            }
        }

        MouseArea {
            id: cardMouse
            anchors.fill: parent
            enabled: card.enabled
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: card.chosen()
        }
    }

    component PreviewSidebar: Rectangle {
        radius: 5
        color: dialog.softAltRow

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 9
            spacing: 6

            Repeater {
                model: [0.72, 0.90, 0.58]
                Rectangle {
                    required property real modelData
                    width: parent.width * modelData
                    height: 6
                    radius: 3
                    color: dialog.softMuted
                    opacity: 0.28
                }
            }
        }
    }

    component PreviewTable: Rectangle {
        radius: 5
        color: dialog.softRow
        border.width: 1
        border.color: dialog.softBorder

        Label {
            anchors.centerIn: parent
            text: qsTr("Главная таблица")
            color: dialog.softMuted
        }
    }

    component PreviewTimeline: Rectangle {
        id: timelinePreview
        property string caption: ""

        radius: 5
        color: dialog.softHeader
        border.width: 1
        border.color: dialog.softBorder

        Label {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 9
            anchors.topMargin: 5
            text: timelinePreview.caption
            color: dialog.softMuted
            font.pixelSize: 10
        }
        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: 9
            anchors.rightMargin: 9
            anchors.topMargin: 23
            anchors.bottomMargin: 8
            spacing: 5

            Repeater {
                model: [0.26, 0.17, 0.34, 0.13]
                Rectangle {
                    required property real modelData
                    width: Math.max(24, (parent.width - 20) * modelData)
                    height: parent.height
                    radius: 4
                    color: dialog.episodeTimelineActorColorsDraft
                        ? systemPalette.highlight : dialog.softMuted
                    opacity: dialog.episodeTimelineActorColorsDraft
                        ? dialog.colorOpacity(dialog.episodeTimelineColorMuteLevelDraft) + 0.2
                        : 0.22
                }
            }
        }
    }

    function arrayPreference(value, fallback) {
        try {
            var parsed = JSON.parse(value)
            return Array.isArray(parsed) ? parsed : fallback
        } catch (error) {
            return fallback
        }
    }

    function objectPreference(value, fallback) {
        try {
            var parsed = JSON.parse(value)
            return parsed && typeof parsed === "object" && !Array.isArray(parsed)
                ? parsed : fallback
        } catch (error) {
            return fallback
        }
    }

    function resetDrafts() {
        actorColorDisplayDraft = actorColorDisplayMode
        actorColorMuteLevelDraft = actorColorMuteLevel
        actorColorCellFillFullHeightDraft = actorColorCellFillFullHeight
        actorMarkerShapeDraft = actorMarkerShape
        actorMarkerSizeDraft = actorMarkerSize
        uiScalePercentDraft = uiScalePercent
        characterColumnsOrderDraft = arrayPreference(characterColumnsOrder, [
            "character", "lines", "rings", "words", "scope", "actor", "preview"
        ])
        characterColumnsHiddenDraft = arrayPreference(characterColumnsHidden, [])
        characterColumnWidthsDraft = objectPreference(characterColumnWidths, {})
        characterCompactRowsDraft = characterCompactRows
        episodeTimelineVisibleDraft = episodeTimelineVisible
        episodeTimelineActorColorsDraft = episodeTimelineActorColors
        episodeTimelineColorMuteLevelDraft = episodeTimelineColorMuteLevel
        episodeTimelinePlacementDraft = episodeTimelinePlacement
        episodeTimelineHeightDraft = episodeTimelineHeight
        episodeTimelineSortModeDraft = episodeTimelineSortMode
    }

    function openForFirstRun() {
        firstRun = true
        currentStep = 0
        resetDrafts()
        // Showing the wizard once is enough: closing it is treated as deferring
        // to the regular Interface settings page.
        appBridge.uiState.setIntValue("onboarding.interfaceVersion", 1)
        open()
    }

    function openFromSettings() {
        firstRun = false
        currentStep = 0
        resetDrafts()
        open()
    }

    function columnVisible(key) {
        return characterColumnsHiddenDraft.indexOf(key) < 0
    }

    function setColumnVisible(key, visible) {
        if (key === "character")
            return
        var next = characterColumnsHiddenDraft.filter(function(item) {
            return item !== key
        })
        if (!visible)
            next.push(key)
        characterColumnsHiddenDraft = next
    }

    function useColumnPreset(preset) {
        if (preset === "essential")
            characterColumnsHiddenDraft = ["lines", "rings", "words", "scope"]
        else if (preset === "statistics")
            characterColumnsHiddenDraft = ["scope", "preview"]
        else
            characterColumnsHiddenDraft = []
    }

    function previewColumnWidth(key) {
        if (key === "actor") return 118
        if (key === "scope") return 78
        if (key === "preview") return 88
        if (key === "lines" || key === "rings") return 56
        if (key === "words") return 52
        return 132
    }

    function markerSizePixels() {
        if (actorMarkerSizeDraft === 1) return 8
        if (actorMarkerSizeDraft === 2) return 15
        return 11
    }

    function markerRadius(size) {
        if (actorMarkerShapeDraft <= 1) return size / 2
        if (actorMarkerShapeDraft === 2) return 4
        return 0
    }

    function colorOpacity(level) {
        if (level >= 2) return 0.22
        if (level === 1) return 0.36
        return 0.58
    }

    function finish() {
        appBridge.uiState.setBoolValue(
            "actorColorCellFill", actorColorDisplayDraft === "cell"
        )
        appBridge.uiState.setIntValue(
            "actorColorCellMuteLevel", actorColorMuteLevelDraft
        )
        appBridge.uiState.setBoolValue(
            "actorColorCellFillFullHeight", actorColorCellFillFullHeightDraft
        )
        appBridge.uiState.setIntValue("actorMarkerShape", actorMarkerShapeDraft)
        appBridge.uiState.setIntValue("actorMarkerSize", actorMarkerSizeDraft)
        appBridge.uiState.setIntValue("main.uiScalePercent", uiScalePercentDraft)
        appBridge.uiState.setStringValue(
            "main.characterColumnsOrder", JSON.stringify(characterColumnsOrderDraft)
        )
        appBridge.uiState.setStringValue(
            "main.characterColumnsHidden", JSON.stringify(characterColumnsHiddenDraft)
        )
        appBridge.uiState.setStringValue(
            "main.characterColumnWidths", JSON.stringify(characterColumnWidthsDraft)
        )
        appBridge.uiState.setBoolValue(
            "main.characterCompactRows", characterCompactRowsDraft
        )
        appBridge.uiState.setBoolValue(
            "main.episodeTimelineVisible", episodeTimelineVisibleDraft
        )
        appBridge.uiState.setBoolValue(
            "main.episodeTimelineActorColors", episodeTimelineActorColorsDraft
        )
        appBridge.uiState.setIntValue(
            "main.episodeTimelineColorMuteLevel", episodeTimelineColorMuteLevelDraft
        )
        appBridge.uiState.setStringValue(
            "main.episodeTimelinePlacement", episodeTimelinePlacementDraft
        )
        appBridge.uiState.setIntValue(
            "main.episodeTimelineHeight", episodeTimelineHeightDraft
        )
        appBridge.uiState.setStringValue(
            "main.episodeTimelineSortMode", episodeTimelineSortModeDraft
        )
        appBridge.uiState.setIntValue("onboarding.interfaceVersion", 1)
        configurationAccepted(
            actorColorDisplayDraft,
            actorColorMuteLevelDraft,
            actorColorCellFillFullHeightDraft,
            actorMarkerShapeDraft,
            actorMarkerSizeDraft,
            uiScalePercentDraft,
            JSON.stringify(characterColumnsOrderDraft),
            JSON.stringify(characterColumnsHiddenDraft),
            JSON.stringify(characterColumnWidthsDraft),
            characterCompactRowsDraft,
            episodeTimelineVisibleDraft,
            episodeTimelineActorColorsDraft,
            episodeTimelineColorMuteLevelDraft,
            episodeTimelinePlacementDraft,
            episodeTimelineHeightDraft,
            episodeTimelineSortModeDraft
        )
        close()
    }

    content: RowLayout {
        anchors.fill: parent
        spacing: dialog.macOSStyle ? 18 : 12

        Rectangle {
            Layout.preferredWidth: dialog.macOSStyle ? 196 : 204
            Layout.fillHeight: true
            radius: dialog.macOSStyle ? 11 : 6
            color: dialog.macOSStyle
                ? Qt.rgba(
                    systemPalette.text.r,
                    systemPalette.text.g,
                    systemPalette.text.b,
                    dialog.darkPalette ? 0.055 : 0.035
                )
                : dialog.softHeader
            border.width: dialog.macOSStyle ? 0 : 1
            border.color: dialog.softBorder

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 7

                Label {
                    text: qsTr("Настройка интерфейса")
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                Label {
                    text: qsTr("Все параметры позднее можно изменить в Настройках.")
                    color: dialog.softMuted
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    bottomPadding: 10
                }

                Repeater {
                    model: dialog.steps

                    delegate: Item {
                        id: stepItem
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: dialog.macOSStyle ? 32 : 36
                        readonly property bool selected: index === dialog.currentStep
                        readonly property bool complete: index < dialog.currentStep

                        Rectangle {
                            anchors.fill: parent
                            radius: dialog.macOSStyle ? 7 : 4
                            color: stepItem.selected
                                ? Qt.rgba(
                                    systemPalette.highlight.r,
                                    systemPalette.highlight.g,
                                    systemPalette.highlight.b,
                                    dialog.darkPalette ? 0.32 : 0.14
                                )
                                : "transparent"
                        }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 9
                            anchors.rightMargin: 8
                            spacing: 9
                            Rectangle {
                                Layout.preferredWidth: 20
                                Layout.preferredHeight: 20
                                radius: 10
                                color: stepItem.complete || stepItem.selected
                                    ? systemPalette.highlight : "transparent"
                                border.width: stepItem.complete || stepItem.selected ? 0 : 1
                                border.color: dialog.softMuted
                                Label {
                                    anchors.centerIn: parent
                                    text: stepItem.complete ? "✓" : String(stepItem.index + 1)
                                    color: stepItem.complete || stepItem.selected
                                        ? systemPalette.highlightedText : dialog.softMuted
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: stepItem.modelData
                                elide: Text.ElideRight
                                fontSizeMode: Text.HorizontalFit
                                minimumPixelSize: 11
                                font.weight: stepItem.selected ? Font.DemiBold : Font.Normal
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
                Label {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr("Шаг %1 из %2").arg(dialog.currentStep + 1).arg(dialog.steps.length)
                    color: dialog.softMuted
                }
                ProgressBar {
                    Layout.fillWidth: true
                    from: 0
                    to: dialog.lastStep
                    value: dialog.currentStep
                }
            }
        }

        StackLayout {
            id: pages
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: dialog.currentStep

            Item {
                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 40, 560)
                    spacing: 16

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 118
                        Layout.preferredHeight: 86
                        radius: 14
                        color: dialog.softHeader
                        border.width: 1
                        border.color: dialog.softBorder

                        Rectangle {
                            x: 10; y: 10; width: 23; height: 66
                            radius: 5; color: dialog.softAltRow
                        }
                        Rectangle {
                            x: 41; y: 10; width: 67; height: 13
                            radius: 4; color: systemPalette.highlight; opacity: 0.75
                        }
                        Repeater {
                            model: 3
                            Rectangle {
                                required property int index
                                x: 41; y: 31 + index * 15; width: 67; height: 10
                                radius: 3
                                color: index % 2 ? dialog.softAltRow : dialog.softRow
                                border.width: 1
                                border.color: dialog.softBorder
                            }
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Давайте настроим рабочее пространство")
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: dialog.macOSStyle ? 26 : 24
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Несколько коротких вопросов помогут подобрать плотность таблиц, цветовую разметку и таймлайн. Вы сразу увидите, как будет выглядеть результат.")
                        horizontalAlignment: Text.AlignHCenter
                        color: dialog.softMuted
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                        lineHeight: 1.15
                    }
                    Label {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("Это займёт около минуты")
                        color: systemPalette.highlight
                        font.weight: Font.DemiBold
                    }
                }
            }

            Item {
                PersistentScrollView {
                    anchors.fill: parent
                    contentWidth: availableWidth

                    ColumnLayout {
                        width: parent.width
                        spacing: 14
                        SettingsPageHeader {
                            title: qsTr("Какой должна быть плотность интерфейса?")
                            subtitle: qsTr("Выберите, сколько информации помещать на экране одновременно.")
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            SelectionCard {
                                Layout.fillWidth: true
                                title: qsTr("Комфортная")
                                subtitle: qsTr("Больше воздуха, удобнее для продолжительной работы.")
                                selected: !dialog.characterCompactRowsDraft
                                onChosen: dialog.characterCompactRowsDraft = false
                            }
                            SelectionCard {
                                Layout.fillWidth: true
                                title: qsTr("Компактная")
                                subtitle: qsTr("Больше строк и данных без прокрутки.")
                                selected: dialog.characterCompactRowsDraft
                                onChosen: dialog.characterCompactRowsDraft = true
                            }
                        }

                        Label { text: qsTr("Предварительный просмотр"); font.bold: true }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 178
                            radius: dialog.macOSStyle ? 10 : 6
                            color: systemPalette.base
                            border.width: 1
                            border.color: dialog.softBorder

                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 0
                                Rectangle {
                                    width: parent.width
                                    height: 30
                                    color: dialog.softHeader
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 8
                                        Label { text: qsTr("Персонаж"); font.bold: true; Layout.fillWidth: true }
                                        Label { text: qsTr("Актёр"); font.bold: true; Layout.preferredWidth: 150 }
                                        Label { text: qsTr("Слов"); font.bold: true; Layout.preferredWidth: 56 }
                                    }
                                }
                                Repeater {
                                    model: [
                                        [qsTr("Главный герой"), qsTr("Алексей Смирнов"), "184"],
                                        [qsTr("Рассказчик"), qsTr("Мария Волкова"), "126"],
                                        [qsTr("Офицер"), qsTr("Не назначен"), "47"]
                                    ]
                                    Rectangle {
                                        id: densityRow
                                        required property var modelData
                                        required property int index
                                        width: parent.width
                                        height: dialog.characterCompactRowsDraft ? 34 : 44
                                        color: index % 2 ? dialog.softAltRow : dialog.softRow
                                        RowLayout {
                                            anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
                                            Label { text: densityRow.modelData[0]; Layout.fillWidth: true }
                                            Label { text: densityRow.modelData[1]; Layout.preferredWidth: 150; color: densityRow.index === 2 ? dialog.softMuted : systemPalette.text }
                                            Label { text: densityRow.modelData[2]; Layout.preferredWidth: 56 }
                                        }
                                    }
                                }
                            }
                        }

                        FormSection {
                            visible: dialog.windowsStyle
                            title: qsTr("Масштаб в Windows")
                            Layout.fillWidth: true
                            RowLayout {
                                anchors.fill: parent
                                Label { text: qsTr("Размер элементов:") }
                                SpinBox {
                                    from: 50; to: 200; stepSize: 5; editable: true
                                    value: dialog.uiScalePercentDraft
                                    onValueModified: dialog.uiScalePercentDraft = value
                                }
                                Label { text: "%"; color: dialog.softMuted }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: qsTr("Применится после перезапуска")
                                    color: dialog.softMuted
                                }
                            }
                        }
                    }
                }
            }

            Item {
                PersistentScrollView {
                    anchors.fill: parent
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 14
                        SettingsPageHeader {
                            title: qsTr("Как показывать цвета актёров?")
                            subtitle: qsTr("Цвет помогает быстро замечать назначения в больших таблицах.")
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            SelectionCard {
                                Layout.fillWidth: true
                                title: qsTr("Цветной маркер")
                                subtitle: qsTr("Спокойный вариант: цвет занимает минимум места.")
                                selected: dialog.actorColorDisplayDraft === "marker"
                                onChosen: dialog.actorColorDisplayDraft = "marker"
                            }
                            SelectionCard {
                                Layout.fillWidth: true
                                title: qsTr("Фон ячейки")
                                subtitle: qsTr("Заметный вариант для быстрого поиска актёра.")
                                selected: dialog.actorColorDisplayDraft === "cell"
                                onChosen: dialog.actorColorDisplayDraft = "cell"
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 142
                            radius: dialog.macOSStyle ? 10 : 6
                            color: systemPalette.base
                            border.width: 1
                            border.color: dialog.softBorder
                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                Repeater {
                                    model: [
                                        [qsTr("Главный герой"), qsTr("Алексей Смирнов"), "#45a4f3"],
                                        [qsTr("Рассказчик"), qsTr("Мария Волкова"), "#e06cab"],
                                        [qsTr("Офицер"), qsTr("Илья Соколов"), "#51b47d"]
                                    ]
                                    Rectangle {
                                        id: actorRow
                                        required property var modelData
                                        required property int index
                                        readonly property color actorColor: modelData[2]
                                        width: parent.width
                                        height: dialog.characterCompactRowsDraft ? 36 : 42
                                        color: index % 2 ? dialog.softAltRow : dialog.softRow
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 10
                                            anchors.rightMargin: 10
                                            Label { text: actorRow.modelData[0]; Layout.fillWidth: true }
                                            Rectangle {
                                                Layout.preferredWidth: 210
                                                Layout.fillHeight: dialog.actorColorCellFillFullHeightDraft
                                                    && dialog.actorColorDisplayDraft === "cell"
                                                Layout.preferredHeight: dialog.actorColorDisplayDraft === "cell"
                                                    ? (dialog.actorColorCellFillFullHeightDraft ? actorRow.height : 28)
                                                    : 28
                                                radius: 5
                                                color: dialog.actorColorDisplayDraft === "cell"
                                                    ? Qt.rgba(
                                                        actorRow.actorColor.r,
                                                        actorRow.actorColor.g,
                                                        actorRow.actorColor.b,
                                                        dialog.colorOpacity(dialog.actorColorMuteLevelDraft)
                                                    ) : "transparent"
                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 8
                                                    anchors.rightMargin: 8
                                                    Rectangle {
                                                        visible: dialog.actorColorDisplayDraft === "marker"
                                                        Layout.preferredWidth: dialog.markerSizePixels()
                                                        Layout.preferredHeight: dialog.markerSizePixels()
                                                        radius: dialog.markerRadius(width)
                                                        color: actorRow.actorColor
                                                    }
                                                    Label { text: actorRow.modelData[1]; Layout.fillWidth: true }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 4
                            columnSpacing: 10
                            rowSpacing: 8
                            Label { text: qsTr("Форма маркера") }
                            PlatformComboBox {
                                Layout.fillWidth: true
                                model: [qsTr("Системная"), qsTr("Круг"), qsTr("Скруглённый квадрат"), qsTr("Квадрат")]
                                currentIndex: dialog.actorMarkerShapeDraft
                                enabled: dialog.actorColorDisplayDraft === "marker"
                                onActivated: dialog.actorMarkerShapeDraft = currentIndex
                            }
                            Label { text: qsTr("Размер") }
                            PlatformComboBox {
                                Layout.fillWidth: true
                                model: [qsTr("Обычный"), qsTr("Мелкий"), qsTr("Крупный")]
                                currentIndex: dialog.actorMarkerSizeDraft
                                enabled: dialog.actorColorDisplayDraft === "marker"
                                onActivated: dialog.actorMarkerSizeDraft = currentIndex
                            }
                            Label {
                                text: qsTr("Яркость цвета")
                                visible: dialog.actorColorDisplayDraft === "cell"
                            }
                            Slider {
                                Layout.fillWidth: true
                                visible: dialog.actorColorDisplayDraft === "cell"
                                from: 0; to: 2; stepSize: 1; snapMode: Slider.SnapAlways
                                value: 2 - dialog.actorColorMuteLevelDraft
                                onMoved: dialog.actorColorMuteLevelDraft = 2 - Math.round(value)
                            }
                            CheckBox {
                                Layout.columnSpan: 2
                                text: qsTr("Заливать всю высоту ячейки")
                                visible: dialog.actorColorDisplayDraft === "cell"
                                checked: dialog.actorColorCellFillFullHeightDraft
                                onToggled: dialog.actorColorCellFillFullHeightDraft = checked
                            }
                        }
                    }
                }
            }

            Item {
                PersistentScrollView {
                    anchors.fill: parent
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 13
                        SettingsPageHeader {
                            title: qsTr("Что должно быть в главной таблице?")
                            subtitle: qsTr("Оставьте только те колонки, которые нужны в ежедневной работе.")
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Быстрый выбор:"); color: dialog.softMuted }
                            Button { text: qsTr("Основное"); onClicked: dialog.useColumnPreset("essential") }
                            Button { text: qsTr("Со статистикой"); onClicked: dialog.useColumnPreset("statistics") }
                            Button { text: qsTr("Показать всё"); onClicked: dialog.useColumnPreset("all") }
                            Item { Layout.fillWidth: true }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 24
                            rowSpacing: 2
                            Repeater {
                                model: dialog.columnDefinitions
                                CheckBox {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    text: modelData.title
                                    enabled: !Boolean(modelData.mandatory)
                                    checked: dialog.columnVisible(modelData.key)
                                    onToggled: dialog.setColumnVisible(modelData.key, checked)
                                }
                            }
                        }
                        Label { text: qsTr("Предварительный просмотр заголовка"); font.bold: true }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: dialog.characterCompactRowsDraft ? 96 : 112
                            radius: dialog.macOSStyle ? 10 : 6
                            color: systemPalette.base
                            border.width: 1
                            border.color: dialog.softBorder
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 0
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 32
                                    spacing: 1
                                    Repeater {
                                        model: dialog.columnDefinitions
                                        Rectangle {
                                            id: headerPreviewCell
                                            required property var modelData
                                            visible: dialog.columnVisible(modelData.key)
                                            Layout.fillWidth: modelData.key === "character"
                                            Layout.preferredWidth: dialog.previewColumnWidth(modelData.key)
                                            Layout.fillHeight: true
                                            color: dialog.softHeader
                                            Label {
                                                anchors.fill: parent
                                                anchors.margins: 5
                                                text: headerPreviewCell.modelData.title
                                                font.bold: true
                                                elide: Text.ElideRight
                                                horizontalAlignment:
                                                    headerPreviewCell.modelData.key === "character"
                                                    || headerPreviewCell.modelData.key === "actor"
                                                        ? Text.AlignLeft : Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: dialog.characterCompactRowsDraft ? 34 : 44
                                    spacing: 1
                                    Repeater {
                                        model: dialog.columnDefinitions
                                        Rectangle {
                                            id: rowPreviewCell
                                            required property var modelData
                                            visible: dialog.columnVisible(modelData.key)
                                            Layout.fillWidth: modelData.key === "character"
                                            Layout.preferredWidth: dialog.previewColumnWidth(modelData.key)
                                            Layout.fillHeight: true
                                            color: dialog.softRow
                                            Label {
                                                anchors.fill: parent
                                                anchors.margins: 5
                                                text: rowPreviewCell.modelData.key === "character" ? qsTr("Рассказчик")
                                                    : rowPreviewCell.modelData.key === "actor" ? qsTr("М. Волкова")
                                                    : rowPreviewCell.modelData.key === "preview" ? "•••" : "126"
                                                elide: Text.ElideRight
                                                horizontalAlignment:
                                                    rowPreviewCell.modelData.key === "character"
                                                    || rowPreviewCell.modelData.key === "actor"
                                                        ? Text.AlignLeft : Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr("Порядок и ширину колонок можно тонко настроить позже в разделе «Интерфейс».")
                            color: dialog.softMuted
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Item {
                PersistentScrollView {
                    anchors.fill: parent
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 13
                        SettingsPageHeader {
                            title: qsTr("Как показывать таймлайн серии?")
                            subtitle: qsTr("Таймлайн даёт быстрый обзор занятости актёров по ходу серии.")
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            SelectionCard {
                                Layout.fillWidth: true
                                Layout.preferredHeight: dialog.windowsStyle ? 116 : 88
                                title: qsTr("Под таблицей")
                                subtitle: qsTr("В рабочей области.")
                                selected: dialog.episodeTimelineVisibleDraft
                                    && dialog.episodeTimelinePlacementDraft === "table"
                                onChosen: {
                                    dialog.episodeTimelineVisibleDraft = true
                                    dialog.episodeTimelinePlacementDraft = "table"
                                }
                            }
                            SelectionCard {
                                Layout.fillWidth: true
                                Layout.preferredHeight: dialog.windowsStyle ? 116 : 88
                                title: qsTr("Внизу окна")
                                subtitle: qsTr("Отдельной полосой снизу.")
                                selected: dialog.episodeTimelineVisibleDraft
                                    && dialog.episodeTimelinePlacementDraft === "bottom"
                                onChosen: {
                                    dialog.episodeTimelineVisibleDraft = true
                                    dialog.episodeTimelinePlacementDraft = "bottom"
                                }
                            }
                            SelectionCard {
                                Layout.fillWidth: true
                                Layout.preferredHeight: dialog.windowsStyle ? 116 : 88
                                title: qsTr("Не показывать")
                                subtitle: qsTr("Больше места таблицам.")
                                selected: !dialog.episodeTimelineVisibleDraft
                                onChosen: dialog.episodeTimelineVisibleDraft = false
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 170
                            radius: dialog.macOSStyle ? 10 : 6
                            color: systemPalette.base
                            border.width: 1
                            border.color: dialog.softBorder

                            StackLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                currentIndex: !dialog.episodeTimelineVisibleDraft ? 2
                                    : dialog.episodeTimelinePlacementDraft === "bottom" ? 1 : 0

                                Item {
                                    RowLayout {
                                        anchors.fill: parent
                                        spacing: 8
                                        PreviewSidebar {
                                            Layout.preferredWidth: 72
                                            Layout.fillHeight: true
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            spacing: 7
                                            PreviewTable {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                            }
                                            PreviewTimeline {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 64
                                                caption: qsTr("Таймлайн под таблицей")
                                            }
                                        }
                                    }
                                }

                                Item {
                                    ColumnLayout {
                                        anchors.fill: parent
                                        spacing: 7
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            spacing: 8
                                            PreviewSidebar {
                                                Layout.preferredWidth: 72
                                                Layout.fillHeight: true
                                            }
                                            PreviewTable {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                            }
                                        }
                                        PreviewTimeline {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 64
                                            caption: qsTr("Таймлайн внизу всего окна")
                                        }
                                    }
                                }

                                Item {
                                    RowLayout {
                                        anchors.fill: parent
                                        spacing: 8
                                        PreviewSidebar {
                                            Layout.preferredWidth: 72
                                            Layout.fillHeight: true
                                        }
                                        PreviewTable {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                        }
                                    }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            enabled: dialog.episodeTimelineVisibleDraft
                            CheckBox {
                                text: qsTr("Окрашивать блоки в цвета актёров")
                                checked: dialog.episodeTimelineActorColorsDraft
                                onToggled: dialog.episodeTimelineActorColorsDraft = checked
                            }
                            Label { text: qsTr("Яркость"); color: dialog.softMuted }
                            Slider {
                                Layout.preferredWidth: 100
                                from: 0; to: 2; stepSize: 1; snapMode: Slider.SnapAlways
                                value: 2 - dialog.episodeTimelineColorMuteLevelDraft
                                enabled: dialog.episodeTimelineActorColorsDraft
                                onMoved: dialog.episodeTimelineColorMuteLevelDraft = 2 - Math.round(value)
                            }
                            Item { Layout.fillWidth: true }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            enabled: dialog.episodeTimelineVisibleDraft
                            Label { text: qsTr("Сортировать дорожки") }
                            PlatformComboBox {
                                Layout.preferredWidth: 250
                                model: [
                                    qsTr("По появлению в серии"),
                                    qsTr("По количеству слов"),
                                    qsTr("По количеству реплик"),
                                    qsTr("По имени актёра")
                                ]
                                currentIndex: ["appearance", "words", "lines", "name"]
                                    .indexOf(dialog.episodeTimelineSortModeDraft)
                                onActivated: dialog.episodeTimelineSortModeDraft =
                                    ["appearance", "words", "lines", "name"][currentIndex]
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 40, 570)
                    spacing: 16
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 72
                        Layout.preferredHeight: 72
                        radius: 36
                        color: Qt.rgba(
                            systemPalette.highlight.r,
                            systemPalette.highlight.g,
                            systemPalette.highlight.b,
                            dialog.darkPalette ? 0.34 : 0.16
                        )
                        Label {
                            anchors.centerIn: parent
                            text: "✓"
                            color: systemPalette.highlight
                            font.pixelSize: 34
                            font.weight: Font.DemiBold
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Всё готово")
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: dialog.macOSStyle ? 26 : 24
                        font.weight: Font.DemiBold
                    }
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Dubbing Manager будет выглядеть так, как удобно именно вам. Эти параметры не затрагивают проекты и могут быть изменены в любое время.")
                        horizontalAlignment: Text.AlignHCenter
                        color: dialog.softMuted
                        wrapMode: Text.WordWrap
                        font.pixelSize: 14
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 104
                        radius: dialog.macOSStyle ? 10 : 6
                        color: dialog.softHeader
                        border.width: 1
                        border.color: dialog.softBorder
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 16
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label { text: qsTr("Строки"); color: dialog.softMuted }
                                Label { text: dialog.characterCompactRowsDraft ? qsTr("Компактные") : qsTr("Комфортные"); font.bold: true }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label { text: qsTr("Цвета актёров"); color: dialog.softMuted }
                                Label { text: dialog.actorColorDisplayDraft === "cell" ? qsTr("Фон ячейки") : qsTr("Маркер"); font.bold: true }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label { text: qsTr("Таймлайн"); color: dialog.softMuted }
                                Label {
                                    text: !dialog.episodeTimelineVisibleDraft ? qsTr("Скрыт")
                                        : dialog.episodeTimelinePlacementDraft === "bottom"
                                            ? qsTr("Внизу окна") : qsTr("Под таблицей")
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        spacing: 8

        AdaptiveButton {
            text: dialog.currentStep === 0 ? qsTr("Не сейчас") : qsTr("Назад")
            Layout.preferredWidth: dialog.windowsStyle ? 110 : implicitWidth
            onClicked: {
                if (dialog.currentStep === 0)
                    dialog.close()
                else
                    dialog.currentStep--
            }
        }
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: dialog.currentStep === dialog.lastStep ? qsTr("Готово")
                : dialog.currentStep === 0 ? qsTr("Начать") : qsTr("Далее")
            highlighted: true
            Layout.preferredWidth: dialog.windowsStyle ? 110 : implicitWidth
            onClicked: {
                if (dialog.currentStep === dialog.lastStep)
                    dialog.finish()
                else
                    dialog.currentStep++
            }
        }
    }
}
