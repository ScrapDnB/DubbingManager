pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

NativeDialogWindow {
    id: dialog
    objectName: "reaperExportDialog"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    readonly property var reaper: appBridge.reaper
    property var preview: ({})
    readonly property string outputFormat: outputTabs.currentIndex === 1 ? "csv" : "rpp"
    readonly property bool batchMode: scopeTabs.currentIndex === 1
    property bool batchCompleted: false

    modal: true
    title: batchMode
        ? "Экспорт в Reaper · все серии"
        : "Экспорт в Reaper · серия " + reaper.episode
    standardButtons: Dialog.NoButton
    width: boundedWidth(900, 32)
    height: boundedHeight(610, 32)

    function markerMode() {
        return sourceMarkers.checked ? "source" : "merged"
    }

    function refreshPreview(formatIndex) {
        var rppMode = Number(formatIndex) === 0
        preview = reaper.updatePreview(
            rppMode && videoCheck.checked,
            !rppMode || regionsCheck.checked,
            rppMode && transliterateCheck.checked,
            markerMode()
        )
    }

    function openForCurrentEpisode() {
        if (!reaper.prepare()) {
            return
        }
        outputTabs.currentIndex = 0
        scopeTabs.currentIndex = 0
        mergedMarkers.checked = true
        regionsCheck.checked = true
        transliterateCheck.checked = false
        videoCheck.checked = reaper.videoAvailable
        open()
        refreshPreview(outputTabs.currentIndex)
    }

    FileDialog {
        id: saveDialog
        title: dialog.outputFormat === "csv"
            ? "Сохранить маркеры Reaper"
            : "Сохранить проект Reaper"
        fileMode: FileDialog.SaveFile
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible) currentFolder = dialog.appBridge.uiState.folderUrl("exports")
        nameFilters: dialog.outputFormat === "csv"
            ? ["Reaper marker CSV (*.csv)"]
            : ["Reaper project (*.rpp)"]
        defaultSuffix: dialog.outputFormat

        onAccepted: {
            dialog.batchCompleted = false
            dialog.appBridge.uiState.rememberFile("exports", selectedFile.toString())
            var success = dialog.reaper.export(
                dialog.outputFormat,
                selectedFile.toString(),
                dialog.outputFormat === "rpp" && videoCheck.checked,
                dialog.outputFormat === "csv" || regionsCheck.checked,
                dialog.outputFormat === "rpp" && transliterateCheck.checked,
                dialog.markerMode()
            )
            if (!success) {
                return
            }
            if (dialog.outputFormat === "rpp") {
                completedDialog.open()
            } else {
                dialog.close()
            }
        }
    }

    FolderDialog {
        id: batchFolderDialog
        title: qsTr("Папка экспорта всех серий")
        currentFolder: dialog.appBridge.uiState.folderUrl("exports")
        onVisibleChanged: if (visible)
            currentFolder = dialog.appBridge.uiState.folderUrl("exports")

        onAccepted: {
            dialog.appBridge.uiState.rememberFolder(
                "exports", selectedFolder.toString()
            )
            var success = dialog.reaper.exportAll(
                dialog.outputFormat,
                selectedFolder.toString(),
                dialog.outputFormat === "rpp" && videoCheck.checked,
                dialog.outputFormat === "csv" || regionsCheck.checked,
                dialog.outputFormat === "rpp" && transliterateCheck.checked,
                dialog.markerMode()
            )
            if (success) {
                dialog.batchCompleted = true
                completedDialog.open()
            }
        }
    }

    NativeDialogWindow {
        id: completedDialog
        ownerWindow: dialog
        modal: true
        title: dialog.batchCompleted
            ? "Экспорт Reaper завершён"
            : "Проект Reaper готов"
        standardButtons: Dialog.NoButton
        width: boundedWidth(430, 32)

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            Label {
                text: dialog.batchCompleted
                    ? "Сохранено файлов: " + dialog.reaper.lastExportCount
                        + ". Открыть папку экспорта?"
                    : "RPP сохранён. Открыть его в приложении, связанном с файлами Reaper?"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                text: dialog.reaper.lastExportPath
                color: dialog.softMuted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
        }

        footer: DialogButtonBox {
            anchors.fill: parent
            Button {
                text: dialog.batchCompleted ? "Открыть папку" : "Открыть"
                onClicked: {
                    dialog.reaper.openLastExport()
                    completedDialog.close()
                    dialog.close()
                }
            }
            Button {
                text: qsTr("Готово")
                onClicked: {
                    completedDialog.close()
                    dialog.close()
                }
            }
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label { text: qsTr("Формат:") }
            NavigationTabBar {
                id: outputTabs
                Layout.preferredWidth: implicitWidth
                model: ["Проект RPP", "Маркеры CSV"]
                tabWidth: 140
                softMuted: dialog.softMuted

                onActivated: function(index) {
                    if (index === 0) {
                        videoCheck.checked = dialog.reaper.videoAvailable
                        dialog.refreshPreview(0)
                    } else {
                        videoCheck.checked = false
                        transliterateCheck.checked = false
                        dialog.refreshPreview(1)
                    }
                }
            }
            Item { Layout.fillWidth: true }
            Label {
                visible: dialog.width > 720
                text: dialog.batchMode
                    ? dialog.reaper.anyVideoAvailable
                        ? "Видео будет подобрано для каждой серии"
                        : "Видео в сериях не привязано"
                    : dialog.reaper.videoAvailable
                        ? "Видео: " + dialog.reaper.videoName
                        : "Видео не привязано"
                color: dialog.softMuted
                elide: Text.ElideMiddle
                Layout.maximumWidth: 260
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            ScrollView {
                id: optionsScroll
                SplitView.preferredWidth: 300
                SplitView.minimumWidth: 245
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                ColumnLayout {
                    width: optionsScroll.availableWidth
                    spacing: 10

                    Label {
                        text: qsTr("Серии")
                        font.bold: true
                    }

                    NavigationTabBar {
                        id: scopeTabs
                        Layout.fillWidth: true
                        model: ["Текущая", "Все серии"]
                        tabWidth: Math.max(112, width / 2)
                        softMuted: dialog.softMuted

                        onActivated: function(index) {
                            if (index === 1 && sourceMarkers.checked
                                    && !dialog.reaper.allSourceMarkersAvailable) {
                                mergedMarkers.checked = true
                            }
                            dialog.refreshPreview(outputTabs.currentIndex)
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: dialog.softBorder
                    }

                    Label {
                        text: qsTr("Содержимое проекта")
                        font.bold: true
                    }

                    CheckBox {
                        id: videoCheck
                        text: dialog.batchMode
                            ? dialog.reaper.anyVideoAvailable
                                ? "Добавлять видео, где оно найдено"
                                : "Видео в сериях не найдено"
                            : dialog.reaper.videoAvailable
                                ? "Добавить дорожку с видео"
                                : "Видео не найдено"
                        enabled: dialog.outputFormat === "rpp"
                            && (dialog.batchMode
                                ? dialog.reaper.anyVideoAvailable
                                : dialog.reaper.videoAvailable)
                        onToggled: dialog.refreshPreview(outputTabs.currentIndex)
                    }

                    CheckBox {
                        id: regionsCheck
                        text: qsTr("Создать регионы с текстом")
                        enabled: dialog.outputFormat === "rpp"
                        onToggled: dialog.refreshPreview(outputTabs.currentIndex)
                    }

                    CheckBox {
                        id: transliterateCheck
                        text: qsTr("Имена дорожек латиницей")
                        enabled: dialog.outputFormat === "rpp"
                        onToggled: dialog.refreshPreview(outputTabs.currentIndex)
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Транслитерация применяется только к именам актёрских дорожек.")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: dialog.softBorder
                    }

                    Label {
                        text: qsTr("Источник маркеров")
                        font.bold: true
                    }

                    ButtonGroup { id: markerGroup }

                    RadioButton {
                        id: mergedMarkers
                        text: qsTr("Объединённые реплики")
                        checked: true
                        ButtonGroup.group: markerGroup
                        onToggled: if (checked) dialog.refreshPreview(outputTabs.currentIndex)
                    }

                    RadioButton {
                        id: sourceMarkers
                        text: qsTr("Точные строки исходника")
                        enabled: dialog.batchMode
                            ? dialog.reaper.allSourceMarkersAvailable
                            : dialog.reaper.sourceMarkersAvailable
                        ButtonGroup.group: markerGroup
                        onToggled: if (checked) dialog.refreshPreview(outputTabs.currentIndex)
                        ToolTip.visible: hovered && !enabled
                        ToolTip.text: qsTr("Точные строки доступны после импорта ASS/SRT с сохранённым исходником.")
                    }

                    Label {
                        visible: dialog.batchMode
                            ? !dialog.reaper.allSourceMarkersAvailable
                            : !dialog.reaper.sourceMarkersAvailable
                        text: dialog.batchMode
                            ? "Точные строки доступны только когда исходник сохранён для каждой экспортируемой серии."
                            : "В этой серии исходные строки не сохранены. Доступны маркеры рабочего текста."
                        color: dialog.softMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Item { Layout.fillHeight: true }

                    Label {
                        visible: dialog.batchMode
                        text: qsTr("Будет создано файлов: ")
                            + dialog.reaper.exportableEpisodeCount
                            + ". Предпросмотр показывает текущую серию."
                        color: dialog.softMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 320
                color: dialog.softRow
                border.color: dialog.softBorder

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Label {
                        text: dialog.batchMode
                            ? "Предпросмотр серии " + dialog.reaper.episode
                            : "Предпросмотр"
                        font.bold: true
                        font.pixelSize: 16
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 18
                        rowSpacing: 6

                        Label { text: qsTr("Регионов"); color: dialog.softMuted }
                        Label {
                            text: dialog.outputFormat === "rpp" && !regionsCheck.checked
                                ? "0"
                                : String(dialog.preview.regions || 0)
                            font.bold: true
                        }
                        Label { text: qsTr("Актёрских дорожек"); color: dialog.softMuted }
                        Label { text: String(dialog.preview.tracks || 0); font.bold: true }
                        Label { text: qsTr("Видео"); color: dialog.softMuted }
                        Label {
                            text: dialog.outputFormat === "csv"
                                ? "не добавляется"
                                : dialog.preview.video ? "будет добавлено" : "нет"
                        }
                    }

                    Label {
                        visible: Number(dialog.preview.invalid_lines || 0) > 0
                        text: qsTr("Некорректных таймингов: ") + dialog.preview.invalid_lines
                        color: palette.brightText
                        background: Rectangle {
                            color: palette.highlight
                            radius: 3
                        }
                        padding: 6
                        Layout.fillWidth: true
                    }

                    Label {
                        text: qsTr("Актёры")
                        font.bold: true
                    }
                    Label {
                        text: dialog.preview.actors && dialog.preview.actors.length
                            ? dialog.preview.actors.join(", ")
                            : "Назначенные актёры не найдены"
                        color: dialog.preview.actors && dialog.preview.actors.length
                            ? palette.text
                            : dialog.softMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: dialog.softBorder
                    }

                    Label {
                        text: qsTr("Первые регионы")
                        font.bold: true
                    }

                    ListView {
                        id: sampleList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 1
                        model: dialog.outputFormat === "rpp" && !regionsCheck.checked
                            ? []
                            : dialog.preview.sample_regions || []

                        delegate: Rectangle {
                            id: sampleDelegate
                            required property int index
                            required property string modelData
                            width: sampleList.width
                            height: sampleText.implicitHeight + 12
                            color: index % 2 === 0
                                ? dialog.softRow
                                : dialog.softAltRow

                            Label {
                                id: sampleText
                                anchors.fill: parent
                                anchors.margins: 6
                                text: sampleDelegate.modelData
                                wrapMode: Text.Wrap
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: sampleList.count === 0
                            text: dialog.outputFormat === "rpp" && !regionsCheck.checked
                                ? "Регионы отключены"
                                : "Нет регионов для предпросмотра"
                            color: dialog.softMuted
                        }
                    }
                }
            }
        }

        DialogButtonBox {
            Layout.fillWidth: true

            Button {
                text: dialog.batchMode
                    ? dialog.outputFormat === "csv"
                        ? "Экспортировать все CSV..."
                        : "Экспортировать все RPP..."
                    : dialog.outputFormat === "csv"
                        ? "Сохранить CSV"
                        : "Сохранить RPP"
                enabled: !dialog.batchMode
                    || dialog.reaper.exportableEpisodeCount > 0
                onClicked: dialog.batchMode
                    ? batchFolderDialog.open()
                    : saveDialog.open()
            }
            Button {
                text: qsTr("Отмена")
                onClicked: dialog.close()
            }
        }
    }
}
