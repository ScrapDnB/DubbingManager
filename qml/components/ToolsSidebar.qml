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
    property bool quickConverterVisible: true
    signal converterResultsRequested()
    signal characterPreviewRequested()
    signal characterRenameRequested()
    signal characterSelectionCleared()

    SplitView.preferredWidth: 235
    SplitView.minimumWidth: 150
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int topControlHeight: macOSStyle ? 28 : 40

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

        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: sidebar.topControlHeight
            Layout.preferredHeight: sidebar.topControlHeight
            Layout.maximumHeight: sidebar.topControlHeight
            spacing: sidebar.macOSStyle ? 5 : 4

            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("Поиск персонажа")
                enabled: sidebar.appBridge !== null
                text: sidebar.castingBackend ? sidebar.castingBackend.searchText : ""
                selectByMouse: true
                Accessible.name: qsTr("Поиск по персонажам")
                onTextEdited: if (sidebar.castingBackend) sidebar.castingBackend.setSearchText(text)
            }

            CompactToolButton {
                iconSource: Qt.resolvedUrl("../icons/x.svg")
                toolTipText: qsTr("Сбросить фильтры")
                enabled: sidebar.castingBackend && (
                    sidebar.castingBackend.actorFilter.length > 0
                    || sidebar.castingBackend.showUnassignedOnly
                    || sidebar.castingBackend.searchText.length > 0
                )
                onClicked: {
                    if (!sidebar.castingBackend)
                        return
                    sidebar.castingBackend.setActorFilter("")
                    sidebar.castingBackend.setShowUnassignedOnly(false)
                    sidebar.castingBackend.setSearchText("")
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 230
            Layout.preferredHeight: 320
            clip: true

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: sidebar.macOSStyle
                    ? "transparent" : sidebar.softBorder
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 0
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

                    RowLayout {
                        Layout.fillWidth: true
                        visible: sidebar.castingBackend
                            && sidebar.castingBackend.selectedCharacter.length > 0
                        spacing: sidebar.macOSStyle ? 5 : 4

                        AdaptiveButton {
                            text: qsTr("Реплики")
                            Layout.fillWidth: true
                            onClicked: sidebar.characterPreviewRequested()
                        }
                        AdaptiveButton {
                            text: qsTr("Переименовать")
                            Layout.fillWidth: true
                            onClicked: sidebar.characterRenameRequested()
                        }
                        CompactToolButton {
                            toolTipText: qsTr("Сбросить выбор")
                            iconSource: Qt.resolvedUrl("../icons/x.svg")
                            onClicked: sidebar.characterSelectionCleared()
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sidebar.castingBackend
                            && sidebar.castingBackend.selectedCharacter.length > 0
                        text: qsTr("Назначения по сериям")
                        font.weight: Font.DemiBold
                        font.pixelSize: sidebar.macOSStyle ? 11 : 12
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 0
                        clip: true
                        readonly property bool statsOverflow: characterStatsList.count
                            * (sidebar.macOSStyle ? 34 : 38)
                            > characterStatsList.height + 1

                        PersistentListView {
                            id: characterStatsList
                            anchors.fill: parent
                            clip: true
                            verticalScrollBarEnabled: !sidebar.macOSStyle
                            model: sidebar.castingBackend
                                ? sidebar.castingBackend.characterEpisodeStatsModel
                                : null

                            delegate: ItemDelegate {
                                required property string episode
                                required property int rings
                                required property int words
                                required property string actor
                                required property string scope
                                width: characterStatsList.viewportWidth
                                height: sidebar.macOSStyle ? 34 : 38
                                leftPadding: sidebar.macOSStyle ? 10 : 12
                                rightPadding: sidebar.macOSStyle ? 10 : 12
                                topPadding: sidebar.macOSStyle ? 3 : 4
                                bottomPadding: sidebar.macOSStyle ? 3 : 4
                                contentItem: Column {
                                    width: Math.max(0, characterStatsList.viewportWidth
                                        - (sidebar.macOSStyle ? 20 : 24))
                                    spacing: 1
                                    Label {
                                        width: parent.width
                                        text: qsTr("Серия ") + episode + " · " + actor
                                        elide: Text.ElideRight
                                        maximumLineCount: 1
                                    }
                                    Label {
                                        width: parent.width
                                        text: scope + " · " + rings + " реплик · " + words + " слов"
                                        elide: Text.ElideRight
                                        maximumLineCount: 1
                                        color: sidebar.softMuted
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: macStatsScrollBar
                            // This panel may keep its content position while
                            // the surrounding SplitView is relaid out. Keep
                            // the macOS indicator available whenever the
                            // selected character has assignments instead of
                            // relying on ListView's delayed height report.
                            visible: sidebar.macOSStyle && characterStatsList.count > 0
                            z: 10
                            width: 6
                            height: Math.max(
                                28,
                                parent.height * parent.height / Math.max(
                                    1, characterStatsList.count
                                        * (sidebar.macOSStyle ? 34 : 38)
                                )
                            )
                            anchors.right: parent.right
                            anchors.rightMargin: 1
                            y: Math.round((parent.height - height) * Math.max(0, Math.min(
                                1,
                                characterStatsList.contentY / Math.max(
                                    1,
                                    characterStatsList.count
                                        * (sidebar.macOSStyle ? 34 : 38) - parent.height
                                )
                            )))
                            radius: width / 2
                            color: palette.text
                            opacity: statsScrollDrag.pressed ? 0.62 : 0.40

                            MouseArea {
                                id: statsScrollDrag
                                anchors.fill: parent
                                cursorShape: Qt.OpenHandCursor
                                property real pressY: 0
                                property real initialContentY: 0
                                onPressed: function(mouse) {
                                    pressY = mouse.y
                                    initialContentY = characterStatsList.contentY
                                    cursorShape = Qt.ClosedHandCursor
                                }
                                onPositionChanged: function(mouse) {
                                    if (!pressed)
                                        return
                                    var rowHeight = sidebar.macOSStyle ? 34 : 38
                                    var trackHeight = Math.max(
                                        1, parent.parent.height - macStatsScrollBar.height
                                    )
                                    var contentRange = Math.max(
                                        0, characterStatsList.count * rowHeight
                                            - parent.parent.height
                                    )
                                    characterStatsList.contentY = Math.max(0, Math.min(
                                        contentRange,
                                        initialContentY + (mouse.y - pressY)
                                            * contentRange / trackHeight
                                    ))
                                }
                                onReleased: cursorShape = Qt.OpenHandCursor
                            }
                        }
                    }
                }
            }
        }

        QuickConverterPanel {
            appBridge: sidebar.appBridge
            visible: sidebar.quickConverterVisible
            softBorder: sidebar.softBorder
            softHeader: sidebar.softHeader
            softMuted: sidebar.softMuted
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            onResultsRequested: sidebar.converterResultsRequested()
        }
    }
}
