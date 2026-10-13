pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: inspector
    required property var appBridge
    required property color softBorder
    required property color softMuted
    required property color panelSurface
    readonly property var backend: appBridge.workspace
    readonly property var casting: appBridge.casting
    readonly property var info: backend.characterInfo
    signal openTextRequested(string character)
    signal renameRequested
    color: panelSurface
    SplitView.minimumWidth: 235
    SplitView.preferredWidth: 280
    Rectangle {
        width: 1
        height: parent.height
        color: inspector.softBorder
    }
    ScrollView {
        anchors.fill: parent
        anchors.margins: 14
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 12
            Label {
                text: qsTr("Персонаж")
                color: inspector.softMuted
                font.weight: Font.DemiBold
            }
            Label {
                text: inspector.info.name || qsTr("Выберите персонажа")
                font.pixelSize: 22
                font.weight: Font.DemiBold
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
            Label {
                visible: !inspector.info.name
                text: qsTr("Назначения, статистика и реплики появятся здесь")
                color: inspector.softMuted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            ColumnLayout {
                visible: !!inspector.info.name
                Layout.fillWidth: true
                spacing: 10
                Label {
                    text: (inspector.info.lines || 0) + qsTr(" строк · ") + (inspector.info.words || 0) + qsTr(" слов в серии")
                    color: inspector.softMuted
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                Label {
                    text: qsTr("Область назначения")
                    font.weight: Font.DemiBold
                }
                PlatformComboBox {
                    id: scope
                    Layout.fillWidth: true
                    model: [qsTr("Весь проект"), qsTr("Только эта серия")]
                    currentIndex: inspector.info.scope === "episode" ? 1 : 0
                    Accessible.name: qsTr("Область назначения")
                    onActivated: inspector.casting.setAssignmentScope(inspector.info.name, currentIndex === 1 ? "episode" : "global")
                }
                Label {
                    text: qsTr("Актёры")
                    font.weight: Font.DemiBold
                }
                Repeater {
                    model: inspector.info.actors || []
                    delegate: RowLayout {
                        id: actor
                        required property var modelData
                        Layout.fillWidth: true
                        Rectangle {
                            width: 9
                            height: 9
                            radius: 5
                            color: actor.modelData.color
                        }
                        Label {
                            text: actor.modelData.name
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        CompactToolButton {
                            iconSource: Qt.resolvedUrl("../icons/x.svg")
                            toolTipText: qsTr("Снять назначение: ") + actor.modelData.name
                            onClicked: inspector.casting.removeActorFromCharacter(inspector.info.name, actor.modelData.id)
                        }
                    }
                }
                Label {
                    visible: (inspector.info.actors || []).length === 0
                    text: qsTr("Актёр не назначен")
                    color: inspector.softMuted
                }
                RowLayout {
                    Layout.fillWidth: true
                    PlatformComboBox {
                        id: assignActor
                        objectName: "inspectorActorCombo"
                        Layout.fillWidth: true
                        model: inspector.casting.actorsModel
                        textRole: "name"
                        valueRole: "id"
                        Accessible.name: qsTr("Актёр для назначения")
                    }
                    AdaptiveButton {
                        text: qsTr("Добавить")
                        enabled: assignActor.currentIndex >= 0 && !!assignActor.currentValue
                        onClicked: inspector.casting.addActorToCharacter(inspector.info.name, assignActor.currentValue)
                    }
                }
                AdaptiveButton {
                    Layout.fillWidth: true
                    text: qsTr("Реплики персонажа")
                    onClicked: inspector.openTextRequested(inspector.info.name)
                }
                SidebarCommandButton {
                    Layout.fillWidth: true
                    text: qsTr("Переименовать…")
                    onClicked: inspector.renameRequested()
                }
                ToolSeparator {
                    orientation: Qt.Horizontal
                    Layout.fillWidth: true
                }
                Label {
                    text: qsTr("По сериям")
                    font.weight: Font.DemiBold
                }
                Repeater {
                    model: inspector.casting.characterEpisodeStatsModel
                    delegate: ItemDelegate {
                        id: assignmentRow
                        required property string episode
                        required property int rings
                        required property int words
                        required property string actor
                        Layout.fillWidth: true
                        implicitHeight: 60
                        onClicked: inspector.appBridge.project.selectEpisode(assignmentRow.episode)
                        contentItem: Column {
                            spacing: 4
                            Label {
                                text: assignmentRow.episode
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            Label {
                                text: assignmentRow.rings + qsTr(" реплик · ") + assignmentRow.words + qsTr(" слов")
                                color: inspector.softMuted
                                font.pixelSize: 11
                            }
                            Label {
                                text: assignmentRow.actor
                                width: parent.width
                                elide: Text.ElideRight
                                color: inspector.softMuted
                                font.pixelSize: 11
                            }
                        }
                    }
                }
                ToolSeparator {
                    orientation: Qt.Horizontal
                    Layout.fillWidth: true
                }
                Label {
                    text: qsTr("Первая реплика в серии")
                    font.weight: Font.DemiBold
                }
                Label {
                    text: inspector.info.firstTime || ""
                    color: inspector.softMuted
                }
                Label {
                    text: inspector.info.firstText || ""
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    maximumLineCount: 4
                    elide: Text.ElideRight
                }
                SidebarCommandButton {
                    text: qsTr("Открыть в тексте")
                    Layout.fillWidth: true
                    onClicked: inspector.openTextRequested(inspector.info.name)
                }
            }
        }
    }
}
