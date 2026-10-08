pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: section

    default property alias sectionContent: body.data
    property string title: qsTr("")
    property bool expanded: false
    // Used by the inspector-style sidebars in the macOS tools windows.
    // Other uses keep their existing, platform-neutral presentation.
    property bool sidebarStyle: false
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    spacing: macOSStyle && sidebarStyle ? 4 : macOSStyle ? 2 : 4

    AbstractButton {
        id: headerButton
        Layout.fillWidth: true
        Layout.preferredHeight: section.macOSStyle && section.sidebarStyle
            ? 30 : section.macOSStyle ? 26 : 32
        leftPadding: section.macOSStyle && section.sidebarStyle ? 6 : 0
        rightPadding: section.macOSStyle && section.sidebarStyle ? 6 : 0
        text: section.title
        font.weight: Font.DemiBold
        onClicked: section.expanded = !section.expanded

        background: Rectangle {
            radius: 6
            color: headerButton.hovered && (
                !section.macOSStyle || section.sidebarStyle
            ) ? Qt.rgba(
                headerButton.palette.text.r,
                headerButton.palette.text.g,
                headerButton.palette.text.b,
                section.macOSStyle ? 0.065 : 0.05
            ) : "transparent"
        }

        contentItem: RowLayout {
            spacing: section.macOSStyle && section.sidebarStyle
                ? 6 : section.macOSStyle ? 5 : 7

            Item {
                Layout.preferredWidth: section.macOSStyle && section.sidebarStyle
                    ? 12 : arrow.implicitWidth
                Layout.preferredHeight: parent.height

                Label {
                    id: arrow
                    anchors.centerIn: parent
                    text: section.macOSStyle && section.sidebarStyle ? "›" : "▶"
                    font.pixelSize: section.macOSStyle && section.sidebarStyle
                        ? 14 : section.macOSStyle ? 9 : 11
                    color: headerButton.palette.buttonText
                    rotation: section.expanded ? 90 : 0
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Behavior on rotation {
                        NumberAnimation { duration: 120 }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: headerButton.text
                font: headerButton.font
                color: headerButton.palette.buttonText
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignLeft
                elide: Text.ElideRight
            }
        }
    }

    ColumnLayout {
        id: body
        visible: section.expanded
        Layout.fillWidth: true
        Layout.leftMargin: section.macOSStyle && section.sidebarStyle
            ? 16 : section.macOSStyle ? 18 : 8
        Layout.rightMargin: section.macOSStyle && section.sidebarStyle
            ? 8 : section.macOSStyle ? 6 : 4
        spacing: section.macOSStyle && section.sidebarStyle
            ? 9 : section.macOSStyle ? 8 : 6
    }
}
