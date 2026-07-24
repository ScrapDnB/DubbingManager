import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolBar {
    id: toolbar

    required property var appBridge
    readonly property var projectBackend: appBridge ? appBridge.project : null
    required property color softMuted
    property int rootWidth: width
    readonly property int controlHeight: Math.max(
        40, Math.ceil(toolbarFontMetrics.height + 18)
    )
    implicitHeight: controlHeight + 16

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

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 4

        ComboBox {
            id: recentProjectsCombo
            Layout.preferredWidth: 180
            Layout.minimumHeight: toolbar.controlHeight
            Layout.preferredHeight: toolbar.controlHeight
            Layout.maximumHeight: toolbar.controlHeight
            Layout.alignment: Qt.AlignVCenter
            visible: toolbar.rootWidth >= 760
            model: toolbar.projectBackend ? toolbar.projectBackend.recentProjectsModel : null
            textRole: "display"
            valueRole: "path"
            onActivated: function(index) {
                var path = currentValue || ""
                currentIndex = 0
                if (path.length > 0 && toolbar.appBridge) {
                    toolbar.projectBackend.openRecent(path)
                }
            }

            Connections {
                target: toolbar.projectBackend
                function onRecentProjectsChanged() {
                    recentProjectsCombo.currentIndex = 0
                }
            }
        }

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

        ToolSeparator {}

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/settings.svg")
            toolTipText: qsTr("Настройки программы")
            onClicked: toolbar.globalSettingsRequested()
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/project-settings.svg")
            toolTipText: qsTr("Настройки проекта")
            onClicked: toolbar.projectSettingsRequested()
        }

        ToolSeparator {}

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

        Item { Layout.fillWidth: true }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/clipboard-check.svg")
            toolTipText: qsTr("Проект: файлы и проверка")
            onClicked: toolbar.healthRequested()
        }

        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/info.svg")
            toolTipText: qsTr("О программе")
            onClicked: toolbar.aboutRequested()
        }
    }
}
