pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: timeline

    required property var castingBackend
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    property bool expanded: true
    property int timelineHeight: macOSStyle ? 172 : 192
    property bool useActorColors: true
    property int timelineColorMuteLevel: 2
    signal characterRequested(string character)
    signal heightAdjustmentRequested(int height)

    readonly property bool macOSStyle: Qt.platform.os === "osx"
    property real widestActorName: 0
    readonly property int labelWidth: Math.ceil(Math.max(
        macOSStyle ? 118 : 132,
        Math.min(width * 0.40, widestActorName + 32)
    ))
    readonly property int laneHeight: macOSStyle ? 22 : 26
    readonly property int headerHeight: macOSStyle ? 28 : 32
    readonly property int rulerHeight: macOSStyle ? 20 : 24
    readonly property bool hasSegments: segments.count > 0
    readonly property int desiredHeight: expanded
        ? Math.max(headerHeight + 82, timelineHeight) : headerHeight

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }
    readonly property bool darkTheme: (
        palette.base.r * 0.2126
        + palette.base.g * 0.7152
        + palette.base.b * 0.0722
    ) < 0.5
    readonly property bool lightAppearance: !darkTheme
    readonly property color frameColor: lightAppearance
        ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.16)
        : softBorder
    readonly property color lanePrimary: lightAppearance
        ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.035)
        : softRow
    readonly property color laneAlternate: lightAppearance
        ? Qt.rgba(palette.text.r, palette.text.g, palette.text.b, 0.075)
        : softAltRow

    function mutedActorColor(source) {
        var sourceColor = Qt.color(source)
        if (!useActorColors)
            return Qt.rgba(
                palette.highlight.r, palette.highlight.g, palette.highlight.b,
                lightAppearance ? 0.52 : 0.68
            )
        if (timelineColorMuteLevel <= 0)
            return sourceColor
        var blend = timelineColorMuteLevel === 1
            ? (darkTheme ? 0.60 : 0.55)
            : (darkTheme ? 0.30 : 0.20)
        return Qt.rgba(
            palette.base.r * (1 - blend) + sourceColor.r * blend,
            palette.base.g * (1 - blend) + sourceColor.g * blend,
            palette.base.b * (1 - blend) + sourceColor.b * blend,
            1
        )
    }

    function refreshLabelWidth() {
        var widest = 0
        for (var index = 0; index < lanes.count; ++index) {
            var lane = lanes.itemAt(index)
            if (lane)
                widest = Math.max(widest, lane.labelTextWidth)
        }
        widestActorName = widest
    }

    function rulerStep(duration) {
        var target = Math.max(1, duration / 12)
        var steps = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]
        for (var index = 0; index < steps.length; ++index) {
            if (steps[index] >= target)
                return steps[index]
        }
        return Math.ceil(target / 3600) * 3600
    }

    function rulerTicks(duration) {
        var step = rulerStep(duration)
        var ticks = []
        for (var second = 0; second <= duration; second += step)
            ticks.push(second)
        if (ticks.length === 0 || ticks[ticks.length - 1] !== duration) {
            // Keep the precise duration visible. If the last regular tick is
            // too close, it is less useful than the exact ending time.
            if (ticks.length > 1
                    && duration - ticks[ticks.length - 1] < step * 0.55)
                ticks[ticks.length - 1] = duration
            else
                ticks.push(duration)
        }
        return ticks
    }

    function rulerLabel(seconds) {
        var total = Math.max(0, Math.round(seconds))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var remainder = total % 60
        function padded(value) { return value < 10 ? "0" + value : "" + value }
        return hours > 0
            ? hours + ":" + padded(minutes) + ":" + padded(remainder)
            : minutes + ":" + padded(remainder)
    }

    Timer {
        id: labelWidthTimer
        interval: 0
        repeat: false
        onTriggered: timeline.refreshLabelWidth()
    }

    implicitHeight: desiredHeight
    Layout.minimumHeight: desiredHeight
    Layout.preferredHeight: desiredHeight
    Layout.maximumHeight: desiredHeight

    Rectangle {
        anchors.fill: parent
        color: timeline.lightAppearance
            ? Qt.rgba(palette.base.r, palette.base.g, palette.base.b, 0.72)
            : "transparent"
        border.color: timeline.frameColor
        radius: timeline.macOSStyle ? 7 : 0
    }

    MouseArea {
        id: resizeHandle
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 8
        z: 2
        cursorShape: Qt.SizeVerCursor
        property real pressGlobalY: 0
        property int initialHeight: 0
        onPressed: function(mouse) {
            pressGlobalY = resizeHandle.mapToGlobal(mouse.x, mouse.y).y
            initialHeight = timeline.timelineHeight
        }
        onPositionChanged: function(mouse) {
            if (!pressed)
                return
            var currentGlobalY = resizeHandle.mapToGlobal(mouse.x, mouse.y).y
            var next = Math.round((initialHeight - (currentGlobalY - pressGlobalY)) / 10) * 10
            timeline.heightAdjustmentRequested(Math.max(110, Math.min(360, next)))
        }
        PlatformToolTip {
            target: resizeHandle
            text: qsTr("Перетащите границу, чтобы изменить высоту таймлайна")
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AbstractButton {
            id: headerButton
            Layout.fillWidth: true
            Layout.preferredHeight: timeline.headerHeight
            leftPadding: timeline.macOSStyle ? 8 : 10
            rightPadding: timeline.macOSStyle ? 8 : 10
            onClicked: timeline.expanded = !timeline.expanded

            contentItem: RowLayout {
                spacing: 7
                Label {
                    text: timeline.expanded ? "⌄" : "›"
                    font.pixelSize: timeline.macOSStyle ? 16 : 18
                    verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: qsTr("Таймлайн серии")
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    verticalAlignment: Text.AlignVCenter
                }
                Label {
                    text: segments.count > 0
                        ? qsTr("Реплики и занятость актёров")
                        : qsTr("Нет реплик для отображения")
                    color: timeline.softMuted
                    font.pixelSize: timeline.macOSStyle ? 11 : 12
                    visible: !timeline.macOSStyle || width > 500
                    elide: Text.ElideRight
                }
            }
            background: Rectangle {
                color: timeline.macOSStyle
                    ? (headerButton.hovered ? Qt.rgba(
                        headerButton.palette.text.r, headerButton.palette.text.g,
                        headerButton.palette.text.b, 0.055
                    ) : "transparent")
                    : timeline.softHeader
                radius: timeline.macOSStyle ? 6 : 0
            }
        }

        Item {
            id: timelineContent
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: timeline.macOSStyle ? 4 : 6
            visible: timeline.expanded
            clip: true

            readonly property real duration: Math.max(
                1,
                timeline.castingBackend ? timeline.castingBackend.timelineDuration : 1
            )
            readonly property real availableWidth: Math.max(
                1, timelineEndX - timelineStartX
            )
            // The ruler and the segments now share the Flickable's actual
            // content coordinates, including platform-specific insets.
            readonly property real timelineStartX: Math.round(
                timelineFlick.contentItem.mapToItem(
                    timelineContent, timeline.labelWidth, 0
                ).x
            )
            readonly property real timelineEndX: Math.round(
                timelineFlick.contentItem.mapToItem(
                    timelineContent, timelineFlick.width - 8, 0
                ).x
            )

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: timeline.rulerHeight
                visible: timeline.hasSegments
                color: "transparent"
                border.color: timeline.frameColor
                border.width: 0

                Rectangle {
                    x: timelineContent.timelineStartX
                    anchors.bottom: parent.bottom
                    width: timelineContent.availableWidth
                    height: 1
                    color: timeline.frameColor
                }

                Repeater {
                    model: timeline.rulerTicks(timelineContent.duration)

                    delegate: Item {
                        required property real modelData
                        readonly property real ratio: modelData / timelineContent.duration
                        readonly property bool firstTick: Math.abs(modelData) < 0.001
                        readonly property bool lastTick: Math.abs(
                            modelData - timelineContent.duration
                        ) < 0.001
                        readonly property real tickX: timelineContent.timelineStartX
                            + timelineContent.availableWidth * ratio
                        x: tickX - width / 2
                        width: 56
                        height: parent.height

                        Label {
                            x: parent.firstTick
                                ? parent.width / 2
                                : parent.lastTick
                                    ? parent.width / 2 - implicitWidth
                                    : (parent.width - implicitWidth) / 2
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 5
                            text: timeline.rulerLabel(modelData)
                            color: timeline.softMuted
                            font.pixelSize: timeline.macOSStyle ? 9 : 10
                        }
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            width: 1
                            height: 4
                            color: timeline.frameColor
                        }
                    }
                }
            }

            Flickable {
                id: timelineFlick
                anchors.fill: parent
                anchors.leftMargin: timeline.macOSStyle ? 4 : 6
                anchors.rightMargin: timeline.macOSStyle ? 4 : 6
                anchors.topMargin: timeline.hasSegments ? timeline.rulerHeight : 0
                contentWidth: width
                contentHeight: Math.max(height, lanes.count * timeline.laneHeight)
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.vertical: VisibleScrollBar {
                    contentOverflow: timelineFlick.contentHeight > timelineFlick.height + 1
                }

                Repeater {
                    id: lanes
                    model: timeline.castingBackend ? timeline.castingBackend.timelineActorsModel : null
                    onItemAdded: function(index, item) { labelWidthTimer.restart() }
                    onItemRemoved: function(index, item) { labelWidthTimer.restart() }
                    onCountChanged: labelWidthTimer.restart()

                    delegate: Item {
                        required property string id
                        required property string name
                        required property string actorColor
                        required property int lane
                        readonly property real labelTextWidth: actorNameMetrics.width
                        width: timelineFlick.width
                        height: timeline.laneHeight
                        y: lane * timeline.laneHeight

                        Rectangle {
                            anchors.fill: parent
                            color: lane % 2 === 0
                                ? timeline.lanePrimary : timeline.laneAlternate
                        }
                        ActorColorSwatch {
                            x: 6
                            anchors.verticalCenter: parent.verticalCenter
                            width: timeline.macOSStyle ? 10 : 12
                            height: width
                            swatchColor: actorColor
                        }
                        Label {
                            id: actorNameLabel
                            x: 22
                            width: timeline.labelWidth - 26
                            anchors.verticalCenter: parent.verticalCenter
                            text: name
                            elide: Text.ElideRight
                            font.pixelSize: timeline.macOSStyle ? 11 : 12
                        }
                        TextMetrics {
                            id: actorNameMetrics
                            text: name
                            font: actorNameLabel.font
                            onWidthChanged: labelWidthTimer.restart()
                        }
                        Rectangle {
                            x: timeline.labelWidth
                            width: 1
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            color: timeline.frameColor
                        }
                    }
                }

                Repeater {
                    id: segments
                    model: timeline.castingBackend ? timeline.castingBackend.timelineModel : null

                    delegate: Rectangle {
                        id: segment
                        required property real start
                        required property real end
                        required property string character
                        required property string actor
                        required property string actorColor
                        required property int lane
                        required property bool selected
                        readonly property real duration: Math.max(1, timeline.castingBackend.timelineDuration)
                        readonly property real availableWidth: Math.max(1, timelineFlick.width - timeline.labelWidth - 8)
                        x: timeline.labelWidth + availableWidth * start / duration
                        y: lane * timeline.laneHeight + 3
                        width: Math.max(3, availableWidth * Math.max(0.15, end - start) / duration)
                        height: timeline.laneHeight - 6
                        radius: timeline.macOSStyle ? 4 : 2
                        color: timeline.mutedActorColor(actorColor)
                        opacity: 1
                        border.width: selected ? 2 : 0
                        border.color: segment.palette.highlight
                        clip: true

                        TapHandler {
                            onTapped: timeline.characterRequested(segment.character)
                        }
                        PlatformToolTip {
                            target: segment
                            text: segment.character + " · " + segment.actor
                        }
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: lanes.count === 0
                    text: qsTr("Откройте серию с репликами")
                    color: timeline.softMuted
                }
            }
        }
    }
}
