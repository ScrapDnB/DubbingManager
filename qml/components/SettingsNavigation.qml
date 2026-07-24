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

    implicitWidth: 174

    SystemPalette {
        id: navPalette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.fill: parent
        color: navigation.darkPalette
            ? Qt.lighter(navPalette.window, 1.13)
            : Qt.darker(navPalette.window, 1.035)
        radius: 6
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 2

        Label {
            text: qsTr("Разделы")
            color: navigation.softMuted
            font.pixelSize: 12
            leftPadding: 8
            topPadding: 6
            bottomPadding: 5
        }

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
                height: 34

                Accessible.name: modelData
                Accessible.role: Accessible.PageTab
                Accessible.selected: selected

                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: sectionDelegate.selected
                        ? Qt.rgba(
                            navPalette.highlight.r,
                            navPalette.highlight.g,
                            navPalette.highlight.b,
                            navigation.darkPalette ? 0.42 : 0.20
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

                Label {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    text: sectionDelegate.modelData
                    elide: Text.ElideRight
                    font.weight: sectionDelegate.selected
                        ? Font.DemiBold
                        : Font.Normal
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
