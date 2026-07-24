pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: section

    default property alias sectionContent: body.data
    property string title: qsTr("")
    property bool expanded: false
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    spacing: macOSStyle ? 2 : 4

    AbstractButton {
        id: headerButton
        Layout.fillWidth: true
        Layout.preferredHeight: section.macOSStyle ? 26 : 32
        text: section.title
        font.weight: Font.DemiBold
        onClicked: section.expanded = !section.expanded

        background: Rectangle {
            radius: 6
            color: !section.macOSStyle && headerButton.hovered
                ? Qt.rgba(
                    headerButton.palette.text.r,
                    headerButton.palette.text.g,
                    headerButton.palette.text.b,
                    section.macOSStyle ? 0.065 : 0.05
                )
                : "transparent"
        }

        contentItem: RowLayout {
            spacing: section.macOSStyle ? 5 : 7

            Label {
                text: "▶"
                font.pixelSize: section.macOSStyle ? 9 : 11
                color: headerButton.palette.buttonText
                rotation: section.expanded ? 90 : 0
                Behavior on rotation {
                    NumberAnimation { duration: 120 }
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
        Layout.leftMargin: section.macOSStyle ? 18 : 8
        Layout.rightMargin: section.macOSStyle ? 6 : 4
        spacing: section.macOSStyle ? 8 : 6
    }
}
