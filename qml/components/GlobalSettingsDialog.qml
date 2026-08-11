pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog

    required property var appBridge
    property var layoutDesignerWindow
    readonly property var backend: appBridge ? appBridge.settings : null
    required property color softMuted

    signal actorBaseExportRequested()
    signal actorBaseImportRequested()
    signal actorColorDisplayModeAccepted(
        string mode, int muteLevel, bool fullHeight, int markerShape, int markerSize
    )
    signal characterTableConfigurationAccepted(
        string order, string hidden, string widths, bool compact, bool timelineVisible,
        bool timelineActorColors, int timelineColorMuteLevel,
        string timelinePlacement, int timelineHeight, string timelineSortMode
    )

    property var montageDraft: ({})
    property var prompterDraft: ({})
    property var mergeDraft: ({})
    property var assDraft: ({})
    property var srtDraft: ({})
    property var docxDraft: ({})
    property var backupDraft: ({})
    property string actorColorDisplayDraft: "marker"
    property string actorColorDisplayMode: "marker"
    property int actorColorMuteLevelDraft: 2
    property int actorColorMuteLevel: 2
    property bool actorColorCellFillFullHeightDraft: false
    property bool actorColorCellFillFullHeight: false
    property int actorMarkerShapeDraft: 0
    property int actorMarkerShape: 0
    property int actorMarkerSizeDraft: 0
    property int actorMarkerSize: 0
    property int uiScalePercent: 75
    property int uiScalePercentDraft: 75
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

    modal: true
    title: qsTr("Глобальные настройки")
    standardButtons: Dialog.NoButton
    width: boundedWidth(820, 36)
    height: boundedHeight(590, 36)

    function arrayPreference(value, fallback) {
        try {
            var parsed = JSON.parse(value)
            return Array.isArray(parsed) ? parsed : fallback
        } catch (error) { return fallback }
    }

    function objectPreference(value, fallback) {
        try {
            var parsed = JSON.parse(value)
            return parsed && typeof parsed === "object" && !Array.isArray(parsed)
                ? parsed : fallback
        } catch (error) { return fallback }
    }

    function openSettings() {
        keywordsArea.text = backend.audiobookKeywords
        montageDraft = Object.assign({}, backend.globalMontageConfig)
        prompterDraft = Object.assign({}, backend.globalPrompterConfig)
        mergeDraft = Object.assign({}, backend.globalMergeConfig)
        assDraft = Object.assign({}, backend.globalAssImportConfig)
        srtDraft = Object.assign({}, backend.globalSrtImportConfig)
        docxDraft = Object.assign({}, backend.globalDocxImportConfig)
        backupDraft = Object.assign({}, backend.globalBackupConfig)
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
        backupModeCombo.currentIndex = backupModeCombo.indexOfValue(
            backupDraft.path_mode || "relative"
        )
        globalNavigation.currentIndex = 0
        open()
    }

    content: RowLayout {
        anchors.fill: parent
        spacing: dialog.macOSStyle ? 16 : 12

        SettingsNavigation {
            id: globalNavigation
            Layout.preferredWidth: implicitWidth
            Layout.fillHeight: true
            sections: [
                "Интерфейс",
                "Резервные копии",
                "Аудиокниги",
                "Актёры",
                "Импорт",
                "Монтажный лист",
                "Вид телесуфлёра",
                "Автоматика телесуфлёра",
                "REAPER / OSC"
            ]
            softMuted: dialog.softMuted
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: globalNavigation.currentIndex

            PersistentScrollView {
                id: interfaceSettingsScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: interfaceSettingsScroll.availableWidth
                    spacing: 12
                SettingsPageHeader {
                    title: qsTr("Интерфейс")
                    subtitle: qsTr("Отображение цветов актёров в главной таблице.")
                }

                FormSection {
                    visible: Qt.platform.os === "windows"
                    title: qsTr("Масштаб интерфейса")
                    Layout.fillWidth: true

                    GridLayout {
                        anchors.fill: parent
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 8

                        Label { text: qsTr("Масштаб:") }
                        RowLayout {
                            SpinBox {
                                from: 50
                                to: 200
                                stepSize: 5
                                editable: true
                                value: dialog.uiScalePercentDraft
                                onValueModified: dialog.uiScalePercentDraft = value
                            }
                            Label { text: qsTr("%"); color: dialog.softMuted }
                            Item { Layout.fillWidth: true }
                        }
                        Label {
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            text: qsTr("Изменение применяется после перезапуска программы.")
                            wrapMode: Text.WordWrap
                            color: dialog.softMuted
                        }
                    }
                }

                CheckBox {
                    text: qsTr("Компактные строки в таблицах")
                    checked: dialog.characterCompactRowsDraft
                    onToggled: dialog.characterCompactRowsDraft = checked
                }

                Label {
                    text: qsTr("Цветовая разметка актёров")
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true

                    Label { text: qsTr("Форма") }

                    PlatformComboBox {
                        id: actorMarkerShapeCombo
                        Layout.preferredWidth: 190
                        model: [
                            qsTr("Системная"),
                            qsTr("Круг"),
                            qsTr("Скруглённый квадрат"),
                            qsTr("Квадрат")
                        ]
                        currentIndex: dialog.actorMarkerShapeDraft
                        onActivated: dialog.actorMarkerShapeDraft = currentIndex
                    }

                    Item { Layout.fillWidth: true }

                    Label { text: qsTr("Размер") }

                    PlatformComboBox {
                        id: actorMarkerSizeCombo
                        Layout.preferredWidth: 130
                        model: [qsTr("Обычный"), qsTr("Мелкий"), qsTr("Крупный")]
                        currentIndex: dialog.actorMarkerSizeDraft
                        onActivated: dialog.actorMarkerSizeDraft = currentIndex
                    }
                }

                Label {
                    text: qsTr("Цвета актёров в главной таблице")
                    font.bold: true
                }

                ButtonGroup { id: actorColorDisplayGroup }

                RadioButton {
                    id: markerColorRadio
                    text: qsTr("Цветной маркер")
                    checked: dialog.actorColorDisplayDraft === "marker"
                    ButtonGroup.group: actorColorDisplayGroup
                    onClicked: dialog.actorColorDisplayDraft = "marker"
                }

                RowLayout {
                    Layout.fillWidth: true

                    RadioButton {
                        id: cellColorRadio
                        text: qsTr("Цветной фон ячейки «Актёр»")
                        checked: dialog.actorColorDisplayDraft === "cell"
                        ButtonGroup.group: actorColorDisplayGroup
                        onClicked: dialog.actorColorDisplayDraft = "cell"
                    }

                    Item { Layout.fillWidth: true }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: cellColorRadio.checked

                    Label { text: qsTr("Яркость заливки") }
                    Rectangle {
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 10
                        radius: width / 2
                        color: dialog.palette.highlight
                        opacity: 0.20
                        visible: cellColorRadio.checked
                    }

                    Rectangle {
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 10
                        radius: width / 2
                        color: dialog.palette.highlight
                        opacity: 0.55
                        visible: cellColorRadio.checked
                    }

                    Rectangle {
                        Layout.preferredWidth: 10
                        Layout.preferredHeight: 10
                        radius: width / 2
                        color: dialog.palette.highlight
                        visible: cellColorRadio.checked
                    }

                    Slider {
                        id: actorColorMuteSlider
                        Layout.preferredWidth: 86
                        Layout.maximumWidth: 86
                        enabled: cellColorRadio.checked
                        // Keep the visual scale conventional. The persisted
                        // value describes muting, so it is inverted below.
                        from: 0
                        to: 2
                        stepSize: 1
                        snapMode: Slider.SnapAlways
                        value: 2 - dialog.actorColorMuteLevelDraft
                        onMoved: dialog.actorColorMuteLevelDraft = 2 - Math.round(value)
                        PlatformToolTip {
                            target: actorColorMuteSlider
                            text: actorColorMuteSlider.value >= 2
                                ? qsTr("Яркие цвета")
                                : actorColorMuteSlider.value > 0
                                    ? qsTr("Умеренно приглушённые цвета")
                                    : qsTr("Приглушённые цвета")
                        }
                    }

                    CheckBox {
                        text: qsTr("Во всю ячейку")
                        checked: dialog.actorColorCellFillFullHeightDraft
                        onToggled: dialog.actorColorCellFillFullHeightDraft = checked
                    }

                    Item { Layout.fillWidth: true }
                }

                Label {
                    Layout.fillWidth: true
                    text: qsTr("При нескольких актёрах цвет применяется отдельно к каждой строке.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }

                CharacterTableSettingsPane {
                    Layout.fillWidth: true
                    columnOrder: dialog.characterColumnsOrderDraft
                    hiddenColumns: dialog.characterColumnsHiddenDraft
                    widthModes: dialog.characterColumnWidthsDraft
                    compactRows: dialog.characterCompactRowsDraft
                    timelineVisible: dialog.episodeTimelineVisibleDraft
                    timelineActorColors: dialog.episodeTimelineActorColorsDraft
                    timelineColorMuteLevel: dialog.episodeTimelineColorMuteLevelDraft
                    timelinePlacement: dialog.episodeTimelinePlacementDraft
                    timelineHeight: dialog.episodeTimelineHeightDraft
                    timelineSortMode: dialog.episodeTimelineSortModeDraft
                    onConfigurationChanged: function(
                        order, hidden, widths, compact, timelineVisible,
                        timelineActorColors, timelineColorMuteLevel,
                        timelinePlacement, timelineHeight, timelineSortMode
                    ) {
                        dialog.characterColumnsOrderDraft = order
                        dialog.characterColumnsHiddenDraft = hidden
                        dialog.characterColumnWidthsDraft = widths
                        dialog.characterCompactRowsDraft = compact
                        dialog.episodeTimelineVisibleDraft = timelineVisible
                        dialog.episodeTimelineActorColorsDraft = timelineActorColors
                        dialog.episodeTimelineColorMuteLevelDraft = timelineColorMuteLevel
                        dialog.episodeTimelinePlacementDraft = timelinePlacement
                        dialog.episodeTimelineHeightDraft = timelineHeight
                        dialog.episodeTimelineSortModeDraft = timelineSortMode
                    }
                }
                }
            }

            ColumnLayout {
                spacing: 12

                SettingsPageHeader {
                    title: qsTr("Резервные копии")
                    subtitle: qsTr("Автоматическое сохранение полных копий проектов.")
                }

                CheckBox {
                    id: backupEnabled
                    text: qsTr("Создавать резервные копии проектов")
                    checked: Boolean(dialog.backupDraft.enabled)
                    onToggled: {
                        var next = Object.assign({}, dialog.backupDraft)
                        next.enabled = checked
                        dialog.backupDraft = next
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10
                    enabled: backupEnabled.checked

                    Label { text: qsTr("Расположение:") }
                    PlatformComboBox {
                        id: backupModeCombo
                        Layout.fillWidth: true
                        textRole: "label"
                        valueRole: "value"
                        model: ListModel {
                            ListElement { label: "Относительно папки проекта"; value: "relative" }
                            ListElement { label: "Абсолютный путь"; value: "absolute" }
                        }
                        onActivated: function(index) {
                            var next = Object.assign({}, dialog.backupDraft)
                            next.path_mode = currentValue
                            var oldPath = String(next.directory || "")
                            if (currentValue === "relative") {
                                if (oldPath.length === 0 || oldPath.startsWith("/")
                                        || /^[A-Za-z]:[\\/]/.test(oldPath))
                                    next.directory = ".backups"
                            } else if (!oldPath.startsWith("/")
                                    && !/^[A-Za-z]:[\\/]/.test(oldPath)) {
                                next.directory = ""
                            }
                            dialog.backupDraft = next
                        }
                    }

                    Label {
                        text: backupModeCombo.currentValue === "absolute"
                            ? "Папка:" : "Относительный путь:"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: backupDirectoryField
                            Layout.fillWidth: true
                            text: String(dialog.backupDraft.directory || "")
                            placeholderText: backupModeCombo.currentValue === "absolute"
                                ? "/путь/к/копиям" : ".backups"
                            selectByMouse: true
                            onEditingFinished: {
                                var next = Object.assign({}, dialog.backupDraft)
                                next.directory = text
                                dialog.backupDraft = next
                            }
                        }
                        AdaptiveButton {
                            text: qsTr("Выбрать...")
                            visible: backupModeCombo.currentValue === "absolute"
                            onClicked: backupFolderDialog.open()
                        }
                    }

                    Label { text: qsTr("Интервал:") }
                    RowLayout {
                        SpinBox {
                            from: 1
                            to: 1440
                            editable: true
                            value: Number(dialog.backupDraft.interval_minutes || 5)
                            onValueModified: {
                                var next = Object.assign({}, dialog.backupDraft)
                                next.interval_minutes = value
                                dialog.backupDraft = next
                            }
                        }
                        Label { text: qsTr("минут"); color: dialog.softMuted }
                        Item { Layout.fillWidth: true }
                    }

                    Label { text: qsTr("Хранить копий:") }
                    SpinBox {
                        from: 1
                        to: 100
                        editable: true
                        value: Number(dialog.backupDraft.max_backups || 10)
                        onValueModified: {
                            var next = Object.assign({}, dialog.backupDraft)
                            next.max_backups = value
                            dialog.backupDraft = next
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: backupModeCombo.currentValue === "absolute"
                        ? "В выбранной папке программа создаст отдельную подпапку для каждого проекта."
                        : "Путь вычисляется от папки каждого файла .dub. Например, .backups или Backup/Projects."
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Копии имеют расширение .dub_backup и содержат полный сохраняемый проект.")
                    wrapMode: Text.WordWrap
                    color: dialog.softMuted
                }
                Item { Layout.fillHeight: true }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Аудиокниги")
                    subtitle: qsTr("Слова для распознавания начала главы. По одному варианту на строку.")
                }
                TextArea {
                    id: keywordsArea
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    placeholderText: qsTr("Глава\nChapter")
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Актёры")
                    subtitle: qsTr("Глобальная база хранит имена и пол отдельно от проектов. Цвета остаются настройкой проекта.")
                }
                PersistentListView {
                    id: globalActorsView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: dialog.appBridge.actorLibrary.globalActorsModel
                    delegate: ItemDelegate {
                        id: actorRow
                        required property string name
                        required property string gender
                        width: globalActorsView.viewportWidth
                        text: name + (gender ? " · " + gender : "")
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: globalActorsView.count === 0
                        text: qsTr("Глобальная база пуста")
                        color: dialog.softMuted
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    AdaptiveButton {
                        text: qsTr("Экспорт...")
                        enabled: globalActorsView.count > 0
                        onClicked: dialog.actorBaseExportRequested()
                    }
                    AdaptiveButton {
                        text: qsTr("Импорт...")
                        onClicked: dialog.actorBaseImportRequested()
                    }
                    Item { Layout.fillWidth: true }
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Импорт")
                    subtitle: qsTr("Общие правила для ASS, SRT, DOCX и объединения реплик.")
                }
                ImportSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    mergeConfiguration: dialog.mergeDraft
                    assConfiguration: dialog.assDraft
                    srtConfiguration: dialog.srtDraft
                    docxConfiguration: dialog.docxDraft
                    docxPresets: dialog.backend.globalDocxImportPresets
                    softMuted: dialog.softMuted
                    onMergeEdited: function(config) { dialog.mergeDraft = config }
                    onAssEdited: function(config) { dialog.assDraft = config }
                    onSrtEdited: function(config) { dialog.srtDraft = config }
                    onDocxEdited: function(config) { dialog.docxDraft = config }
                    onSaveDocxPresetRequested: function(name, config) {
                        dialog.backend.saveDocxImportPreset(name, config)
                    }
                    onDeleteDocxPresetRequested: function(name) {
                        dialog.backend.deleteDocxImportPreset(name)
                    }
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Монтажный лист")
                    subtitle: qsTr("Единые настройки предпросмотра и экспорта для всех проектов.")
                }
                AdaptiveButton {
                    text: qsTr("Открыть конструктор макетов…")
                    onClicked: if (dialog.layoutDesignerWindow)
                        dialog.layoutDesignerWindow.openFor("montage", dialog)
                }
                MontageSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    configuration: dialog.montageDraft
                    onConfigEdited: function(config) { dialog.montageDraft = config }
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Вид телесуфлёра")
                    subtitle: qsTr("Оформление, разметка и размеры текста для всех проектов.")
                }
                AdaptiveButton {
                    text: qsTr("Открыть конструктор макетов…")
                    onClicked: if (dialog.layoutDesignerWindow)
                        dialog.layoutDesignerWindow.openFor("teleprompter", dialog)
                }
                TeleprompterSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    globalScope: true
                    appearanceScope: true
                    automationScope: false
                    configuration: dialog.prompterDraft
                    onConfigEdited: function(config) { dialog.prompterDraft = config }
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("Автоматика телесуфлёра")
                    subtitle: qsTr("Прокрутка, постраничные паузы, диагностика и клавиши навигации.")
                }
                TeleprompterSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    globalScope: false
                    appearanceScope: false
                    automationScope: true
                    configuration: dialog.prompterDraft
                    onConfigEdited: function(config) { dialog.prompterDraft = config }
                }
            }

            ColumnLayout {
                spacing: 8
                SettingsPageHeader {
                    title: qsTr("REAPER / OSC")
                    subtitle: qsTr("Подключение REAPER и синхронизация телесуфлёра на этом компьютере.")
                }
                ReaperOscSettingsPane {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    configuration: dialog.prompterDraft
                    softMuted: dialog.softMuted
                    onConfigEdited: function(config) {
                        dialog.prompterDraft = config
                    }
                }
            }
        }
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        AdaptiveButton {
            text: qsTr("Сохранить")
            highlighted: dialog.macOSStyle
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                dialog.appBridge.uiState.setBoolValue(
                    "actorColorCellFill",
                    cellColorRadio.checked
                )
                dialog.appBridge.uiState.setIntValue(
                    "actorColorCellMuteLevel",
                    dialog.actorColorMuteLevelDraft
                )
                dialog.appBridge.uiState.setBoolValue(
                    "actorColorCellFillFullHeight",
                    dialog.actorColorCellFillFullHeightDraft
                )
                dialog.appBridge.uiState.setIntValue(
                    "actorMarkerShape",
                    dialog.actorMarkerShapeDraft
                )
                dialog.appBridge.uiState.setIntValue(
                    "actorMarkerSize",
                    dialog.actorMarkerSizeDraft
                )
                dialog.appBridge.uiState.setIntValue(
                    "main.uiScalePercent",
                    dialog.uiScalePercentDraft
                )
                dialog.actorColorDisplayModeAccepted(
                    cellColorRadio.checked ? "cell" : "marker",
                    dialog.actorColorMuteLevelDraft,
                    dialog.actorColorCellFillFullHeightDraft,
                    dialog.actorMarkerShapeDraft,
                    dialog.actorMarkerSizeDraft
                )
                dialog.appBridge.uiState.setStringValue(
                    "main.characterColumnsOrder",
                    JSON.stringify(dialog.characterColumnsOrderDraft)
                )
                dialog.appBridge.uiState.setStringValue(
                    "main.characterColumnsHidden",
                    JSON.stringify(dialog.characterColumnsHiddenDraft)
                )
                dialog.appBridge.uiState.setStringValue(
                    "main.characterColumnWidths",
                    JSON.stringify(dialog.characterColumnWidthsDraft)
                )
                dialog.appBridge.uiState.setBoolValue(
                    "main.characterCompactRows", dialog.characterCompactRowsDraft
                )
                dialog.appBridge.uiState.setBoolValue(
                    "main.episodeTimelineVisible", dialog.episodeTimelineVisibleDraft
                )
                dialog.appBridge.uiState.setBoolValue(
                    "main.episodeTimelineActorColors", dialog.episodeTimelineActorColorsDraft
                )
                dialog.appBridge.uiState.setIntValue(
                    "main.episodeTimelineColorMuteLevel",
                    dialog.episodeTimelineColorMuteLevelDraft
                )
                dialog.appBridge.uiState.setStringValue(
                    "main.episodeTimelinePlacement", dialog.episodeTimelinePlacementDraft
                )
                dialog.appBridge.uiState.setIntValue(
                    "main.episodeTimelineHeight", dialog.episodeTimelineHeightDraft
                )
                dialog.appBridge.uiState.setStringValue(
                    "main.episodeTimelineSortMode", dialog.episodeTimelineSortModeDraft
                )
                dialog.characterTableConfigurationAccepted(
                    JSON.stringify(dialog.characterColumnsOrderDraft),
                    JSON.stringify(dialog.characterColumnsHiddenDraft),
                    JSON.stringify(dialog.characterColumnWidthsDraft),
                    dialog.characterCompactRowsDraft,
                    dialog.episodeTimelineVisibleDraft,
                    dialog.episodeTimelineActorColorsDraft,
                    dialog.episodeTimelineColorMuteLevelDraft,
                    dialog.episodeTimelinePlacementDraft,
                    dialog.episodeTimelineHeightDraft,
                    dialog.episodeTimelineSortModeDraft
                )
                if (dialog.backend.applyGlobalSettingsComplete(
                    "ru",
                    keywordsArea.text,
                    dialog.montageDraft,
                    dialog.prompterDraft,
                    dialog.mergeDraft,
                    dialog.assDraft,
                    dialog.srtDraft,
                    dialog.docxDraft,
                    dialog.backupDraft
                )) {
                    dialog.close()
                }
            }
        }
        AdaptiveButton {
            text: qsTr("Отмена")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }

    FolderDialog {
        id: backupFolderDialog
        title: qsTr("Папка резервных копий")
        currentFolder: dialog.appBridge.uiState.folderUrl("backupFolders")
        onVisibleChanged: if (visible)
            currentFolder = dialog.appBridge.uiState.folderUrl("backupFolders")
        onAccepted: {
            dialog.appBridge.uiState.rememberFolder(
                "backupFolders", selectedFolder.toString()
            )
            var next = Object.assign({}, dialog.backupDraft)
            next.directory = dialog.appBridge.uiState.localPath(
                selectedFolder.toString()
            )
            next.path_mode = "absolute"
            dialog.backupDraft = next
            backupModeCombo.currentIndex = backupModeCombo.indexOfValue("absolute")
        }
    }
}
