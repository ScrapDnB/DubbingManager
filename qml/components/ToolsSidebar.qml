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
        color: sidebar.panelSurface
        border.color: sidebar.softBorder
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 6

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 32

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

            FluentButton {
                text: qsTr("Телесуфлёр")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.teleprompterRequested()
            }
            FluentButton {
                text: qsTr("Монтажный лист")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.montagePreviewRequested()
            }
            FluentButton {
                text: qsTr("Reaper")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.reaperExportRequested()
            }
            FluentButton {
                text: qsTr("Аудиокнига")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                onClicked: sidebar.audiobookRequested()
            }
            FluentButton {
                text: qsTr("Отчёт серии")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.episodeSummaryRequested()
            }
            FluentButton {
                text: qsTr("Назначить роли")
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                enabled: sidebar.castingBackend !== null
                onClicked: sidebar.rolesRequested()
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

        Item { Layout.fillHeight: true }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 230

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: sidebar.softBorder
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    color: sidebar.softHeader
                    border.color: sidebar.softBorder

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
    }
}
