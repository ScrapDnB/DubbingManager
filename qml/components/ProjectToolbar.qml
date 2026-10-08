import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolBar {
    id: toolbar

    required property var appBridge
    readonly property var projectBackend: appBridge ? appBridge.project : null
    required property color softMuted
    property int rootWidth: width
    property bool quickConverterVisible: true
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property bool wrappedWindowsToolbar: !macOSStyle && width < 1120
    readonly property int controlHeight: Math.max(
        40, Math.ceil(toolbarFontMetrics.height + 18)
    )
    implicitHeight: wrappedWindowsToolbar
        ? controlHeight * 2 + 20
        : controlHeight + (macOSStyle ? 8 : 16)

    FontMetrics {
        id: toolbarFontMetrics
        font: toolbar.font
    }

    signal openProjectRequested()
    signal saveProjectAsRequested()
    signal globalSettingsRequested()
    signal projectSettingsRequested()
    signal healthRequested()
    signal aboutRequested()
    signal teleprompterRequested()
    signal montagePreviewRequested()
    signal reaperExportRequested()
    signal audiobookRequested()
    signal episodeSummaryRequested()
    signal rolesRequested()
    signal quickConverterVisibilityRequested(bool visible)

    component ToolbarSeparator: ToolSeparator {
        height: toolbar.controlHeight
    }

    component ProjectControls: Row {
        spacing: 4
        height: toolbar.controlHeight

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/file-plus.svg")
            toolTipText: qsTr("Новый проект")
            onClicked: toolbar.projectBackend.create()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/folder-open.svg")
            toolTipText: qsTr("Открыть проект")
            onClicked: toolbar.openProjectRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/save.svg")
            toolTipText: qsTr("Сохранить проект")
            enabled: toolbar.projectBackend && toolbar.projectBackend.path.length > 0
            onClicked: if (toolbar.projectBackend) toolbar.projectBackend.save()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/save-as.svg")
            toolTipText: qsTr("Сохранить проект как")
            onClicked: toolbar.saveProjectAsRequested()
        }
    }

    component ProjectSettingsControls: Row {
        spacing: 4
        height: toolbar.controlHeight

        ToolbarSeparator { }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/project-settings.svg")
            toolTipText: qsTr("Настройки проекта")
            onClicked: toolbar.projectSettingsRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/clipboard-check.svg")
            toolTipText: qsTr("Проект: файлы и проверка")
            onClicked: toolbar.healthRequested()
        }
    }

    component HistoryControls: Row {
        spacing: 4
        height: toolbar.controlHeight

        ToolbarSeparator { }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/undo.svg")
            toolTipText: qsTr("Отменить")
            enabled: toolbar.projectBackend && toolbar.projectBackend.canUndo
            onClicked: if (toolbar.projectBackend) toolbar.projectBackend.undo()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/redo.svg")
            toolTipText: qsTr("Повторить")
            enabled: toolbar.projectBackend && toolbar.projectBackend.canRedo
            onClicked: if (toolbar.projectBackend) toolbar.projectBackend.redo()
        }
    }

    component ScenarioControls: Row {
        spacing: 4
        height: toolbar.controlHeight

        ToolbarSeparator { }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/teleprompter.svg")
            toolTipText: qsTr("Телесуфлёр")
            enabled: toolbar.projectBackend
                && toolbar.projectBackend.currentEpisode.length > 0
            onClicked: toolbar.teleprompterRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/montage.svg")
            toolTipText: qsTr("Монтажный лист")
            enabled: toolbar.projectBackend
                && toolbar.projectBackend.currentEpisode.length > 0
            onClicked: toolbar.montagePreviewRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl(toolbar.macOSStyle
                ? "../icons/reaper.svg"
                : "../icons/reaper-windows.svg")
            toolTipText: qsTr("Экспорт в Reaper")
            glyphSize: toolbar.macOSStyle ? 16 : 24
            enabled: toolbar.projectBackend
                && toolbar.projectBackend.currentEpisode.length > 0
            onClicked: toolbar.reaperExportRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/audiobook.svg")
            toolTipText: qsTr("Аудиокнига")
            enabled: toolbar.appBridge !== null
            onClicked: toolbar.audiobookRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/report.svg")
            toolTipText: qsTr("Отчёт серии")
            enabled: toolbar.projectBackend
                && toolbar.projectBackend.currentEpisode.length > 0
            onClicked: toolbar.episodeSummaryRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/roles.svg")
            toolTipText: qsTr("Назначить роли")
            enabled: toolbar.appBridge && toolbar.appBridge.casting
            onClicked: toolbar.rolesRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/converter.svg")
            toolTipText: toolbar.quickConverterVisible
                ? qsTr("Скрыть быстрый конвертер")
                : qsTr("Показать быстрый конвертер")
            checkable: true
            checked: toolbar.quickConverterVisible
            onClicked: toolbar.quickConverterVisibilityRequested(checked)
        }
    }

    component AppControls: Row {
        spacing: 4
        height: toolbar.controlHeight

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/settings.svg")
            toolTipText: qsTr("Настройки программы")
            onClicked: toolbar.globalSettingsRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/info.svg")
            toolTipText: qsTr("О программе")
            onClicked: toolbar.aboutRequested()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 4
        visible: !toolbar.wrappedWindowsToolbar

        PlatformComboBox {
            id: recentProjectsWide
            Layout.preferredWidth: 180
            Layout.minimumHeight: toolbar.controlHeight
            Layout.preferredHeight: toolbar.controlHeight
            Layout.maximumHeight: toolbar.controlHeight
            Layout.alignment: Qt.AlignVCenter
            visible: toolbar.rootWidth >= 620
            model: toolbar.projectBackend
                ? toolbar.projectBackend.recentProjectsModel : null
            textRole: "display"
            valueRole: "path"
            onActivated: function(index) {
                var path = currentValue || ""
                currentIndex = 0
                if (path.length > 0 && toolbar.appBridge)
                    toolbar.projectBackend.openRecent(path)
            }
        }
        ProjectControls { }
        ProjectSettingsControls { }
        HistoryControls { }
        ScenarioControls { }
        Item { Layout.fillWidth: true }
        AppControls { }
    }

    Column {
        id: compactControls
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 8
        spacing: 4
        visible: toolbar.wrappedWindowsToolbar
        height: toolbar.controlHeight * 2 + spacing

        Row {
            id: primaryRow
            spacing: 4
            height: toolbar.controlHeight

            PlatformComboBox {
                id: recentProjectsCompact
                width: 180
                height: toolbar.controlHeight
                visible: toolbar.rootWidth >= 620
                model: toolbar.projectBackend
                    ? toolbar.projectBackend.recentProjectsModel : null
                textRole: "display"
                valueRole: "path"
                onActivated: function(index) {
                    var path = currentValue || ""
                    currentIndex = 0
                    if (path.length > 0 && toolbar.appBridge)
                        toolbar.projectBackend.openRecent(path)
                }
            }
            ProjectControls { }
            ProjectSettingsControls { }
            HistoryControls { }
            AppControls { }
        }

        Row {
            id: scenarioRow
            spacing: 4
            height: toolbar.controlHeight

            ScenarioControls { }
        }
    }

    Connections {
        target: toolbar.projectBackend
        function onRecentProjectsChanged() {
            recentProjectsWide.currentIndex = 0
            recentProjectsCompact.currentIndex = 0
        }
    }
}
