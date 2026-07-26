import QtQuick

Item {
    id: swatch

    property color swatchColor: "transparent"
    property bool interactive: false
    property bool selected: false
    property bool well: false
    property bool compact: false
    // 0 follows the platform: circles on macOS, rounded squares on Windows.
    property int markerShape: 0
    // 0 is the regular size, 1 is small and 2 is large.
    property int markerSize: 0
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int resolvedMarkerShape: markerShape === 0
        ? (macOSStyle ? 1 : 2) : markerShape
    readonly property int markSize: well
        ? (compact ? (macOSStyle ? 16 : 18) : 28)
        : markerSize === 1
            ? (macOSStyle ? 8 : 10)
            : markerSize === 2
                ? (macOSStyle ? 14 : 18)
                : (macOSStyle ? 10 : 14)

    signal clicked()

    implicitWidth: well ? markSize + (compact ? 6 : 8) : 20
    implicitHeight: well ? markSize + (compact ? 6 : 8) : 20
    Accessible.role: interactive ? Accessible.Button : Accessible.StaticText
    Accessible.name: qsTr("Цвет актёра")

    Rectangle {
        anchors.centerIn: parent
        width: swatch.markSize + 4
        height: width
        radius: swatch.well
            ? (swatch.macOSStyle ? 8 : 5)
            : swatch.resolvedMarkerShape === 1 ? width / 2
                : swatch.resolvedMarkerShape === 2 ? Math.min(4, width / 3) : 0
        color: "transparent"
        border.width: swatch.selected ? 2 : 0
        border.color: palette.highlight
        visible: swatch.selected
    }

    Rectangle {
        id: mark
        anchors.centerIn: parent
        width: swatch.markSize
        height: width
        radius: swatch.well
            ? (swatch.macOSStyle ? 6 : 3)
            : swatch.resolvedMarkerShape === 1 ? width / 2
                : swatch.resolvedMarkerShape === 2 ? Math.min(3, width / 3) : 0
        color: swatch.swatchColor
        border.width: 1
        border.color: Qt.rgba(
            palette.text.r, palette.text.g, palette.text.b,
            hover.hovered ? 0.52 : 0.28
        )
        scale: hover.hovered && !swatch.well ? 1.12 : 1

        Behavior on scale {
            NumberAnimation { duration: 90; easing.type: Easing.OutCubic }
        }
    }

    HoverHandler {
        id: hover
        enabled: swatch.interactive
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        enabled: swatch.interactive
        onTapped: swatch.clicked()
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }
}
