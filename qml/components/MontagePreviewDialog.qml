pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtWebChannel
import QtWebEngine

NativeDialogWindow {
    id: dialog
    objectName: "montagePreviewDialog"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    property string singleFormat: "html"
    property bool settingsVisible: true
    property real settingsWidth: 350
    readonly property var montageBackend: appBridge ? appBridge.montage : null
    readonly property var config: montageBackend ? montageBackend.config : ({})

    modal: true
    title: qsTr("Монтажный лист: серия ") + (montageBackend ? montageBackend.episode : "")
    standardButtons: Dialog.Close
    width: boundedWidth(1160, 28)
    height: boundedHeight(760, 28)

    ListModel {
        id: layoutModel
        ListElement { label: "Таблица"; value: "Таблица" }
        ListElement { label: "Сценарий 1"; value: "Сценарий 1" }
        ListElement { label: "Сценарий 2"; value: "Сценарий 2" }
        ListElement { label: "Сценарий 3"; value: "Сценарий 3" }
    }

    ListModel {
        id: timeModeModel
        ListElement { label: "Диапазон"; value: "range" }
        ListElement { label: "Только начало"; value: "start" }
    }

    QtObject {
        id: previewBackend
        WebChannel.id: "backend"

        function update_text(lineId, newText) {
            dialog.montageBackend.updateText(String(lineId), String(newText))
        }
    }

    WebChannel {
        id: previewChannel
        registeredObjects: [previewBackend]
    }

    ActorHighlightDialog {
        id: actorHighlightDialog
        ownerWindow: dialog
        montageBackend: dialog.montageBackend
        softBorder: dialog.softBorder
        softHeader: dialog.softHeader
        softRow: dialog.softRow
        softAltRow: dialog.softAltRow
        softMuted: dialog.softMuted
    }

    FileDialog {
        id: singleFileDialog
        title: qsTr("Сохранить монтажный лист")
        fileMode: FileDialog.SaveFile
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        nameFilters: dialog.singleFormat === "html" ? ["HTML (*.html)"]
            : dialog.singleFormat === "xlsx" ? ["Excel (*.xlsx)"]
            : dialog.singleFormat === "docx" ? ["Word (*.docx)"]
            : ["PDF (*.pdf)"]
        defaultSuffix: dialog.singleFormat
        onAccepted: {
            dialog.appBridge.uiState.rememberFile("exports", selectedFile.toString())
            dialog.montageBackend.exportFile(
                dialog.singleFormat,
                selectedFile.toString()
            )
        }
    }

    FolderDialog {
        id: batchFolderDialog
        title: qsTr("Выберите папку экспорта")
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        onAccepted: {
            dialog.appBridge.uiState.rememberFolder("exports", selectedFolder.toString())
            dialog.montageBackend.exportBatch(
                selectedFolder.toString(),
                formatHtml.checked,
                formatXlsx.checked,
                formatDocx.checked,
                formatPdf.checked,
                allEpisodes.checked
            )
        }
    }

    function openFor(episode) {
        montageBackend.clearBatchResults()
        montageBackend.prepare(episode)
        layoutCombo.syncValue()
        timeModeCombo.syncValue()
        open()
        reloadPreview()
    }

    function reloadPreview() {
        if (montageBackend && previewBrowser) {
            previewBrowser.loadHtml(montageBackend.html)
        }
    }

    function selectedFormatCount() {
        return Number(formatHtml.checked) + Number(formatXlsx.checked)
            + Number(formatDocx.checked) + Number(formatPdf.checked)
    }

    function runExport() {
        var count = selectedFormatCount()
        if (count === 0) {
            return
        }
        if (currentEpisode.checked && count === 1) {
            singleFormat = formatHtml.checked ? "html"
                : formatXlsx.checked ? "xlsx"
                : formatDocx.checked ? "docx"
                : "pdf"
            singleFileDialog.open()
            return
        }
        batchFolderDialog.open()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            CompactToolButton {
                iconSource: Qt.resolvedUrl("../icons/settings.svg")
                toolTipText: dialog.settingsVisible
                    ? qsTr("Скрыть настройки") : qsTr("Показать настройки")
                checked: dialog.settingsVisible
                onClicked: dialog.settingsVisible = !dialog.settingsVisible
            }

            Label { text: qsTr("Серия:") }

            PlatformComboBox {
                id: episodeCombo
                Layout.preferredWidth: 150
                model: dialog.montageBackend ? dialog.montageBackend.episodesModel : null
                textRole: "name"
                valueRole: "name"
                onActivated: dialog.montageBackend.prepare(currentValue)

                function syncEpisode() {
                    if (!dialog.montageBackend) {
                        return
                    }
                    var episodeIndex = indexOfValue(dialog.montageBackend.episode)
                    currentIndex = episodeIndex >= 0 ? episodeIndex : 0
                }

                Connections {
                    target: dialog.montageBackend
                    function onEpisodeChanged() { episodeCombo.syncEpisode() }
                }
            }

            Label {
                text: (dialog.montageBackend ? dialog.montageBackend.count : 0)
                    + " реплик"
                color: dialog.softMuted
            }

            Item { Layout.fillWidth: true }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Rectangle {
                visible: dialog.settingsVisible
                SplitView.preferredWidth: dialog.settingsWidth
                SplitView.minimumWidth: 300
                color: palette.window
                border.width: 1
                border.color: dialog.softBorder
                clip: true
                onWidthChanged: {
                    if (visible && width >= 300)
                        dialog.settingsWidth = width
                }

                PersistentScrollView {
                    id: settingsPane
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    contentWidth: availableWidth
                    contentHeight: settingsColumn.implicitHeight

                    ColumnLayout {
                        id: settingsColumn
                        width: settingsPane.availableWidth
                        spacing: 5

                        Label {
                            text: qsTr("Просмотр")
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: qsTr("Макет") }
                            PlatformComboBox {
                                id: layoutCombo
                                Layout.fillWidth: true
                                model: layoutModel
                                textRole: "label"
                                valueRole: "value"
                                onActivated: dialog.montageBackend.setOption(
                                    "layout_type", currentValue
                                )

                                function syncValue() {
                                    var layoutIndex = indexOfValue(
                                        dialog.config.layout_type
                                    )
                                    currentIndex = layoutIndex >= 0
                                        ? layoutIndex : 0
                                }

                                Connections {
                                    target: dialog.montageBackend
                                    function onConfigChanged() {
                                        layoutCombo.syncValue()
                                    }
                                }
                            }
                        }

                        CollapsibleSection {
                            title: qsTr("Колонки")
                            expanded: true
                            Layout.fillWidth: true

                            WinUiCheckBox {
                                text: qsTr("Таймкод")
                                checked: Boolean(dialog.config.col_tc)
                                onToggled: dialog.montageBackend.setOption(
                                    "col_tc", checked
                                )
                            }
                            WinUiCheckBox {
                                text: qsTr("Персонаж")
                                checked: Boolean(dialog.config.col_char)
                                onToggled: dialog.montageBackend.setOption(
                                    "col_char", checked
                                )
                            }
                            WinUiCheckBox {
                                text: qsTr("Актёр")
                                checked: Boolean(dialog.config.col_actor)
                                onToggled: dialog.montageBackend.setOption(
                                    "col_actor", checked
                                )
                            }
                            WinUiCheckBox {
                                text: qsTr("Реплика")
                                checked: Boolean(dialog.config.col_text)
                                onToggled: dialog.montageBackend.setOption(
                                    "col_text", checked
                                )
                            }
                        }

                        CollapsibleSection {
                            title: qsTr("Таймкод")
                            expanded: true
                            Layout.fillWidth: true

                            PlatformComboBox {
                                id: timeModeCombo
                                Layout.fillWidth: true
                                model: timeModeModel
                                textRole: "label"
                                valueRole: "value"
                                onActivated: dialog.montageBackend.setOption(
                                    "time_display", currentValue
                                )

                                function syncValue() {
                                    var modeIndex = indexOfValue(
                                        dialog.config.time_display
                                    )
                                    currentIndex = modeIndex >= 0
                                        ? modeIndex : 0
                                }

                                Connections {
                                    target: dialog.montageBackend
                                    function onConfigChanged() {
                                        timeModeCombo.syncValue()
                                    }
                                }
                            }

                            WinUiCheckBox {
                                text: qsTr("Округлять")
                                checked: Boolean(dialog.config.round_time)
                                onToggled: dialog.montageBackend.setOption(
                                    "round_time", checked
                                )
                            }
                        }

                        CollapsibleSection {
                            title: qsTr("Цвета и подсветка")
                            Layout.fillWidth: true

                            WinUiCheckBox {
                                text: qsTr("Цвета актёров")
                                checked: Boolean(dialog.config.use_color)
                                onToggled: dialog.montageBackend.setOption(
                                    "use_color", checked
                                )
                            }
                            WinUiCheckBox {
                                text: qsTr("Смягчать фон")
                                enabled: Boolean(dialog.config.use_color)
                                checked: Boolean(dialog.config.soften_colors)
                                onToggled: dialog.montageBackend.setOption(
                                    "soften_colors", checked
                                )
                            }
                            FluentButton {
                                Layout.fillWidth: true
                                text: qsTr("Подсветка: ")
                                    + dialog.montageBackend.highlightSummary
                                enabled: Boolean(dialog.config.use_color)
                                    && dialog.montageBackend.highlightSummary !== "Нет актёров"
                                onClicked: actorHighlightDialog.open()
                            }
                        }

                        CollapsibleSection {
                            title: qsTr("Размер текста")
                            Layout.fillWidth: true

                            Repeater {
                                model: [
                                    { label: "Таймкод", key: "f_time", value: Number(dialog.config.f_time || 21) },
                                    { label: "Персонаж", key: "f_char", value: Number(dialog.config.f_char || 20) },
                                    { label: "Актёр", key: "f_actor", value: Number(dialog.config.f_actor || 14) },
                                    { label: "Реплика", key: "f_text", value: Number(dialog.config.f_text || 30) }
                                ]

                                delegate: RowLayout {
                                    id: fontRow
                                    required property var modelData
                                    Layout.fillWidth: true

                                    Label {
                                        text: fontRow.modelData.label
                                        Layout.fillWidth: true
                                    }
                                    WinUiSpinBox {
                                        from: 8
                                        to: 72
                                        editable: true
                                        value: fontRow.modelData.value
                                        onValueModified: dialog.montageBackend.setOption(
                                            fontRow.modelData.key, value
                                        )
                                    }
                                }
                            }
                        }

                        CollapsibleSection {
                            title: qsTr("Экспорт")
                            expanded: true
                            Layout.fillWidth: true

                            WinUiCheckBox {
                                text: qsTr("Разрешить правку текста")
                                checked: Boolean(dialog.config.allow_edit)
                                onToggled: dialog.montageBackend.setOption(
                                    "allow_edit", checked
                                )
                            }

                            WinUiCheckBox {
                                text: qsTr("Открывать после экспорта")
                                checked: Boolean(dialog.config.open_auto)
                                onToggled: dialog.montageBackend.setOption(
                                    "open_auto", checked
                                )
                            }
                        }
                    }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                color: palette.base
                border.color: dialog.softBorder
                clip: true

                WebEngineView {
                    id: previewBrowser
                    anchors.fill: parent
                    anchors.margins: 1
                    webChannel: previewChannel
                    backgroundColor: "#f6f7f8"
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: dialog.montageBackend && (
                dialog.montageBackend.batchBusy || batchResults.count > 0
            )
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: dialog.montageBackend
                        ? dialog.montageBackend.batchSummary : ""
                    color: dialog.softMuted
                    elide: Text.ElideRight
                }
                ProgressBar {
                    Layout.preferredWidth: 180
                    visible: dialog.montageBackend
                        && dialog.montageBackend.batchBusy
                    value: dialog.montageBackend
                        ? dialog.montageBackend.batchProgress : 0
                }
                FluentButton {
                    text: qsTr("Отменить")
                    visible: dialog.montageBackend
                        && dialog.montageBackend.batchBusy
                    onClicked: dialog.montageBackend.cancelBatch()
                }
            }

            PersistentListView {
                id: batchResults
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(96, count * 30)
                visible: count > 0
                clip: true
                model: dialog.montageBackend
                    ? dialog.montageBackend.batchResultModel : null

                delegate: ItemDelegate {
                    required property int index
                    required property string fileName
                    required property string status
                    required property string detail
                    width: batchResults.viewportWidth
                    height: 30
                    text: fileName + " · " + status
                    ToolTip.visible: hovered
                    ToolTip.text: detail
                    onClicked: dialog.montageBackend.openBatchResult(index)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label { text: qsTr("Форматы:") }
            WinUiCheckBox {
                id: formatHtml
                text: qsTr("HTML")
                checked: Boolean(dialog.config.format_html)
                onToggled: dialog.montageBackend.setOption("format_html", checked)
            }
            WinUiCheckBox {
                id: formatXlsx
                text: qsTr("XLSX")
                checked: Boolean(dialog.config.format_xls)
                onToggled: dialog.montageBackend.setOption("format_xls", checked)
            }
            WinUiCheckBox {
                id: formatDocx
                text: qsTr("DOCX")
                checked: Boolean(dialog.config.format_docx)
                onToggled: dialog.montageBackend.setOption("format_docx", checked)
            }
            WinUiCheckBox {
                id: formatPdf
                text: qsTr("PDF")
                checked: Boolean(dialog.config.format_pdf)
                onToggled: dialog.montageBackend.setOption("format_pdf", checked)
            }

            ToolSeparator {}

            WinUiRadioButton {
                id: currentEpisode
                text: qsTr("Текущая серия")
                checked: true
                onToggled: function(value) {
                    if (value) allEpisodes.checked = false
                }
            }
            WinUiRadioButton {
                id: allEpisodes
                text: qsTr("Все серии")
                onToggled: function(value) {
                    if (value) currentEpisode.checked = false
                }
            }

            Item { Layout.fillWidth: true }

            FluentButton {
                text: qsTr("Экспортировать")
                primary: true
                Layout.preferredWidth: 120
                enabled: dialog.selectedFormatCount() > 0
                    && !dialog.montageBackend.batchBusy
                onClicked: dialog.runExport()
            }
        }
    }

    Connections {
        target: dialog.montageBackend
        function onChanged() { dialog.reloadPreview() }
    }
}
