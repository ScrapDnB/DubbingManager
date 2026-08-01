pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: floatWindow
    objectName: "teleprompterFloatWindow"

    required property var teleprompter
    required property var uiState
    required property color softBorder
    required property color softMuted
    property var ownerWindow

    width: 300
    height: 440
    minimumWidth: 280
    minimumHeight: 340
    maximumWidth: 520
    maximumHeight: 700
    visible: false
    title: qsTr("Телесуфлёр")
    transientParent: null
    flags: Qt.Tool
        | Qt.WindowStaysOnTopHint
        | Qt.CustomizeWindowHint
        | Qt.WindowDoesNotAcceptFocus
        | Qt.FramelessWindowHint
    color: palette.window
    property bool uiStateReady: false

    function displayedTimecode(value) {
        var text = String(value || "")
        if (Boolean(floatWindow.teleprompter.config.hide_leading_timecode_zeros)
                && text.indexOf("0:") === 0) {
            return text.slice(2)
        }
        return text
    }

    function restoreSize() {
        width = Math.max(
            minimumWidth,
            Math.min(maximumWidth, uiState.intValue("teleprompterFloat.width", 300))
        )
        height = Math.max(
            minimumHeight,
            Math.min(maximumHeight, uiState.intValue("teleprompterFloat.height", 440))
        )
        uiStateReady = true
    }

    function persistSize() {
        uiState.setIntValue("teleprompterFloat.width", Math.round(width))
        uiState.setIntValue("teleprompterFloat.height", Math.round(height))
    }

    function openNearOwner() {
        if (Qt.platform.os === "osx"
                && typeof platformIntegration !== "undefined") {
            platformIntegration.configureFloatingToolWindow(floatWindow)
        }
        if (ownerWindow) {
            x = ownerWindow.x + ownerWindow.width - width - 24
            y = ownerWindow.y + 72
        }
        visible = true
        raise()
    }

    onVisibleChanged: if (visible && Qt.platform.os === "osx"
            && typeof platformIntegration !== "undefined") {
        platformIntegration.configureFloatingToolWindow(floatWindow)
    }
    onWidthChanged: if (uiStateReady) sizePersistenceTimer.restart()
    onHeightChanged: if (uiStateReady) sizePersistenceTimer.restart()

    Component.onCompleted: restoreSize()

    Timer {
        id: sizePersistenceTimer
        interval: 250
        repeat: false
        onTriggered: floatWindow.persistSize()
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    Connections {
        target: floatWindow.teleprompter
        function onChanged() {
            episodeBox.currentIndex = episodeBox.indexOfValue(
                floatWindow.teleprompter.episode
            )
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            radius: 4
            color: Qt.rgba(
                palette.text.r,
                palette.text.g,
                palette.text.b,
                0.12
            )

            Label {
                anchors.centerIn: parent
                text: qsTr("Управление")
                font.bold: true
            }

            HoverHandler {
                cursorShape: Qt.OpenHandCursor
            }
            DragHandler {
                target: null
                onActiveChanged: if (active) floatWindow.startSystemMove()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            AdaptiveButton {
                text: qsTr("Назад")
                Layout.fillWidth: true
                Layout.preferredWidth: 0
                Layout.minimumWidth: 0
                Layout.maximumWidth: Number.POSITIVE_INFINITY
                Layout.preferredHeight: 50
                onClicked: floatWindow.teleprompter.navigate(-1)
            }
            AdaptiveButton {
                text: qsTr("Вперёд")
                Layout.fillWidth: true
                Layout.preferredWidth: 0
                Layout.minimumWidth: 0
                Layout.maximumWidth: Number.POSITIVE_INFINITY
                Layout.preferredHeight: 50
                onClicked: floatWindow.teleprompter.navigate(1)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: qsTr("Серия:") }
            PlatformComboBox {
                id: episodeBox
                Layout.fillWidth: true
                textRole: "name"
                valueRole: "name"
                model: floatWindow.teleprompter.episodesModel
                Component.onCompleted: currentIndex = indexOfValue(
                    floatWindow.teleprompter.episode
                )
                onActivated: floatWindow.teleprompter.setEpisode(currentValue)
            }
        }

        Label {
            text: qsTr("Список реплик:")
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 4
            color: palette.base
            border.width: 1
            border.color: floatWindow.softBorder
            clip: true

            PersistentListView {
                id: activeList
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: floatWindow.teleprompter.model
                currentIndex: floatWindow.teleprompter.currentIndex

                delegate: Rectangle {
                    id: navigationRow

                    required property int index
                    required property real start
                    required property string time
                    required property string character
                    required property bool active

                    width: activeList.viewportWidth
                    height: active ? 30 : 0
                    visible: active
                    color: index === activeList.currentIndex
                        ? Qt.rgba(
                            palette.highlight.r,
                            palette.highlight.g,
                            palette.highlight.b,
                            0.14
                        ) : navigationHover.hovered ? Qt.rgba(
                            palette.highlight.r,
                            palette.highlight.g,
                            palette.highlight.b,
                            0.07
                        ) : index % 2 === 0 ? "transparent"
                            : Qt.rgba(
                                palette.text.r,
                                palette.text.g,
                                palette.text.b,
                                0.025
                            )

                    HoverHandler { id: navigationHover }
                    TapHandler {
                        onTapped: floatWindow.teleprompter.jumpTo(
                            navigationRow.start
                        )
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 6
                        spacing: 7

                        Label {
                            text: floatWindow.displayedTimecode(navigationRow.time)
                            color: palette.text
                            Layout.preferredWidth: 60
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
                        }
                        Label {
                            text: navigationRow.character
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        AdaptiveButton {
            text: qsTr("Скрыть")
            Layout.fillWidth: true
            Layout.preferredWidth: 0
            Layout.minimumWidth: 0
            Layout.maximumWidth: Number.POSITIVE_INFINITY
            onClicked: floatWindow.close()
        }
    }

    // The controller intentionally has no native title bar, so provide a
    // small resize affordance that behaves consistently on both platforms.
    Item {
        id: resizeHandle
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 18
        height: 18
        z: 10

        property real initialWidth: 0
        property real initialHeight: 0

        HoverHandler {
            id: resizeHover
            cursorShape: Qt.SizeFDiagCursor
        }
        DragHandler {
            target: null
            onActiveChanged: if (active) {
                resizeHandle.initialWidth = floatWindow.width
                resizeHandle.initialHeight = floatWindow.height
            }
            onTranslationChanged: if (active) {
                floatWindow.width = Math.max(
                    floatWindow.minimumWidth,
                    Math.min(
                        floatWindow.maximumWidth,
                        Math.round(resizeHandle.initialWidth + translation.x)
                    )
                )
                floatWindow.height = Math.max(
                    floatWindow.minimumHeight,
                    Math.min(
                        floatWindow.maximumHeight,
                        Math.round(resizeHandle.initialHeight + translation.y)
                    )
                )
            }
        }

        Canvas {
            anchors.centerIn: parent
            width: 10
            height: 10
            visible: resizeHover.hovered
            onPaint: {
                var context = getContext("2d")
                context.clearRect(0, 0, width, height)
                context.strokeStyle = floatWindow.softMuted
                context.lineWidth = 1
                for (var offset = 2; offset <= 6; offset += 2) {
                    context.beginPath()
                    context.moveTo(offset, height)
                    context.lineTo(width, offset)
                    context.stroke()
                }
            }
        }
    }
}
