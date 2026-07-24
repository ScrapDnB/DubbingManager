import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: sidebar

    required property var appBridge
    readonly property var castingBackend: appBridge ? appBridge.casting : null
    required property color softBorder
    required property color softHeader
    required property color softMuted
    required property color panelSurface
    signal montagePreviewRequested()
    signal reaperExportRequested()
    signal episodeSummaryRequested()
    signal teleprompterRequested()
    signal audiobookRequested()
    signal rolesRequested()
    signal converterResultsRequested()

    SplitView.preferredWidth: 235
    SplitView.minimumWidth: 150
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    readonly property color commandHover: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.12
    )
    readonly property color commandPressed: Qt.rgba(
        palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.20
    )

    Rectangle {
        anchors.fill: parent
        color: sidebar.macOSStyle
            ? Qt.rgba(
                palette.window.r,
                palette.window.g,
                palette.window.b,
                0.72
            )
            : sidebar.panelSurface
        border.color: sidebar.macOSStyle ? "transparent" : sidebar.softBorder

        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            width: 1
            visible: sidebar.macOSStyle
            color: sidebar.softBorder
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: sidebar.macOSStyle ? 8 : 6
        spacing: sidebar.macOSStyle ? 5 : 6

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: sidebar.macOSStyle ? 26 : 32

            Label {
                anchors.fill: parent
                text: qsTr("Сценарии")
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            SidebarCommandButton {
                text: qsTr("Телесуфлёр")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.teleprompterRequested()
            }
            SidebarCommandButton {
                text: qsTr("Монтажный лист")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.montagePreviewRequested()
            }
            SidebarCommandButton {
                text: qsTr("Reaper")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.reaperExportRequested()
            }
            SidebarCommandButton {
                text: qsTr("Аудиокнига")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                onClicked: sidebar.audiobookRequested()
            }
            SidebarCommandButton {
                text: qsTr("Отчёт серии")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.episodeSummaryRequested()
            }
            SidebarCommandButton {
                text: qsTr("Назначить роли")
                Layout.fillWidth: true
                Layout.preferredHeight: sidebar.macOSStyle ? 28 : 32
                enabled: sidebar.castingBackend !== null
                onClicked: sidebar.rolesRequested()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 230
            Layout.preferredHeight: 320

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: sidebar.macOSStyle
                    ? "transparent" : sidebar.softBorder
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    color: sidebar.macOSStyle
                        ? "transparent" : sidebar.softHeader
                    border.color: sidebar.macOSStyle
                        ? "transparent" : sidebar.softBorder

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        visible: sidebar.macOSStyle
                        color: sidebar.softBorder
                    }

                    Label {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        text: qsTr("Статистика персонажа")
                        font.bold: true
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: 6
                    spacing: 6

                    Label {
                        Layout.fillWidth: true
                        text: sidebar.castingBackend
                            ? sidebar.castingBackend.selectedCharacterStats
                            : qsTr("Выберите персонажа в таблице")
                        color: sidebar.softMuted
                        wrapMode: Text.WordWrap
                    }

                    PersistentListView {
                        id: characterStatsList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: sidebar.castingBackend
                            ? sidebar.castingBackend.characterEpisodeStatsModel
                            : null

                        delegate: ItemDelegate {
                            required property string episode
                            required property int rings
                            required property int words
                            required property string actor
                            width: characterStatsList.viewportWidth
                            height: 38
                            contentItem: Column {
                                Label {
                                    width: parent.width
                                    text: episode + " · " + actor
                                    elide: Text.ElideRight
                                }
                                Label {
                                    width: parent.width
                                    text: rings + " колец · " + words + " слов"
                                    color: sidebar.softMuted
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }
                }
            }
        }

        QuickConverterPanel {
            appBridge: sidebar.appBridge
            softBorder: sidebar.softBorder
            softHeader: sidebar.softHeader
            softMuted: sidebar.softMuted
            Layout.fillWidth: true
            onResultsRequested: sidebar.converterResultsRequested()
        }
    }
}
