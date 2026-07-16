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
    signal montagePreviewRequested()
    signal reaperExportRequested()
    signal episodeSummaryRequested()
    signal teleprompterRequested()
    signal audiobookRequested()
    signal rolesRequested()
    signal converterResultsRequested()

    SplitView.preferredWidth: 235
    SplitView.minimumWidth: 150

    Rectangle {
        anchors.fill: parent
        color: "transparent"
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

            Button {
                text: qsTr("Телесуфлёр")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.teleprompterRequested()
            }
            Button {
                text: qsTr("Монтажный лист")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.montagePreviewRequested()
            }
            Button {
                text: qsTr("Reaper")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.reaperExportRequested()
            }
            Button {
                text: qsTr("Аудиокнига")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                onClicked: sidebar.audiobookRequested()
            }
            Button {
                text: qsTr("Отчёт серии")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                enabled: sidebar.appBridge && sidebar.appBridge.project.currentEpisode.length > 0
                onClicked: sidebar.episodeSummaryRequested()
            }
            Button {
                text: qsTr("Назначить роли")
                Layout.fillWidth: true
                Layout.preferredHeight: 28
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

                    ListView {
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
                            width: ListView.view.width
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
