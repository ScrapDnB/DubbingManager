import QtQuick

Item {
    id: swatch

    property color swatchColor: "transparent"
    property bool interactive: false
    property bool selected: false
    property bool well: false
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property int markSize: well ? 28 : (macOSStyle ? 10 : 14)

    signal clicked()

    implicitWidth: well ? 36 : 20
    implicitHeight: well ? 36 : 20
    Accessible.role: interactive ? Accessible.Button : Accessible.StaticText
    Accessible.name: qsTr("Цвет актёра")

    Rectangle {
        anchors.centerIn: parent
        width: swatch.markSize + 4
        height: width
        radius: swatch.well
            ? (swatch.macOSStyle ? 8 : 5)
            : (swatch.macOSStyle ? width / 2 : 4)
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
            : (swatch.macOSStyle ? width / 2 : 3)
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
