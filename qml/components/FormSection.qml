pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: section

    default property alias contentData: contentHost.data
    property string title: ""
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    implicitWidth: Math.max(titleLabel.implicitWidth, contentHost.implicitWidth)
        + (macOSStyle ? 0 : 24)
    implicitHeight: titleRow.implicitHeight + (title.length > 0 ? 8 : 0)
        + contentHost.implicitHeight + (macOSStyle ? 6 : 20)

    SystemPalette {
        id: sectionPalette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.fill: parent
        visible: !section.macOSStyle
        radius: 6
        color: "transparent"
        border.color: Qt.rgba(
            sectionPalette.text.r,
            sectionPalette.text.g,
            sectionPalette.text.b,
            0.16
        )
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: section.macOSStyle ? 0 : 10
        spacing: section.title.length > 0 ? 6 : 0

        Item {
            id: titleRow
            Layout.fillWidth: true
            implicitHeight: section.title.length > 0 ? 20 : 0
            visible: section.title.length > 0

            Label {
                id: titleLabel
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: section.title
                font.pixelSize: section.macOSStyle ? 12 : 13
                font.weight: Font.Medium
                color: section.macOSStyle
                    ? sectionPalette.placeholderText : sectionPalette.text
            }

            Rectangle {
                anchors.left: titleLabel.right
                anchors.right: parent.right
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                height: 1
                visible: false
                color: Qt.rgba(
                    sectionPalette.text.r,
                    sectionPalette.text.g,
                    sectionPalette.text.b,
                    0.10
                )
            }
        }

        Item {
            id: contentHost
            Layout.fillWidth: true
            implicitHeight: children.length > 0
                ? children[0].implicitHeight : 0
            Layout.leftMargin: section.macOSStyle ? 0 : 0
            Layout.rightMargin: section.macOSStyle ? 4 : 0
        }
    }
}
