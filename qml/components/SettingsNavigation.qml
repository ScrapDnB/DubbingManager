pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: navigation

    property var sections: []
    property alias currentIndex: sectionList.currentIndex
    property color softMuted: navPalette.placeholderText
    readonly property bool darkPalette: (
        navPalette.window.r + navPalette.window.g + navPalette.window.b
    ) < 1.5
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    implicitWidth: macOSStyle ? 190 : 184

    SystemPalette {
        id: navPalette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.fill: parent
        color: navigation.macOSStyle
            ? "transparent"
            : Qt.rgba(
                navPalette.window.r,
                navPalette.window.g,
                navPalette.window.b,
                navigation.darkPalette ? 0.10 : 0.32
            )
    }

    Rectangle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: 1
        color: Qt.rgba(
            navPalette.text.r,
            navPalette.text.g,
            navPalette.text.b,
            navigation.macOSStyle ? 0.12 : 0.16
        )
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: navigation.macOSStyle ? 4 : 6
        anchors.rightMargin: navigation.macOSStyle ? 10 : 10
        anchors.topMargin: navigation.macOSStyle ? 4 : 6
        anchors.bottomMargin: navigation.macOSStyle ? 4 : 6
        spacing: navigation.macOSStyle ? 3 : 2

        PersistentListView {
            id: sectionList

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: navigation.sections
            currentIndex: 0

            delegate: Item {
                id: sectionDelegate

                required property int index
                required property string modelData
                readonly property bool selected: index === sectionList.currentIndex

                width: sectionList.viewportWidth
                height: navigation.macOSStyle ? 30 : 36

                Accessible.name: modelData
                Accessible.role: Accessible.PageTab
                Accessible.selected: selected

                Rectangle {
                    anchors.fill: parent
                    radius: navigation.macOSStyle ? 7 : 4
                    color: sectionDelegate.selected
                        ? Qt.rgba(
                            navPalette.highlight.r,
                            navPalette.highlight.g,
                            navPalette.highlight.b,
                            navigation.macOSStyle
                                ? (navigation.darkPalette ? 0.72 : 0.82)
                                : (navigation.darkPalette ? 0.42 : 0.20)
                        )
                        : sectionMouse.containsMouse
                            ? Qt.rgba(
                                navPalette.text.r,
                                navPalette.text.g,
                                navPalette.text.b,
                                0.07
                            )
                            : "transparent"
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: 20
                    radius: 2
                    visible: sectionDelegate.selected && !navigation.macOSStyle
                    color: navPalette.highlight
                }

                Label {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: navigation.macOSStyle ? 10 : 12
                    anchors.rightMargin: 8
                    text: sectionDelegate.modelData
                    elide: Text.ElideRight
                    font.weight: sectionDelegate.selected
                        ? Font.DemiBold
                        : Font.Normal
                    color: sectionDelegate.selected && navigation.macOSStyle
                        ? navPalette.highlightedText
                        : navPalette.text
                }

                MouseArea {
                    id: sectionMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        sectionList.currentIndex = sectionDelegate.index
                        sectionList.forceActiveFocus()
                    }
                }

            }
        }
    }
}
