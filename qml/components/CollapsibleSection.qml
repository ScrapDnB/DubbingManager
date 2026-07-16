pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: section

    default property alias sectionContent: body.data
    property string title: qsTr("")
    property bool expanded: false

    spacing: 4

    ToolButton {
        id: headerButton
        Layout.fillWidth: true
        text: (section.expanded ? "▾  " : "▸  ") + section.title
        font.bold: true
        flat: true
        onClicked: section.expanded = !section.expanded

        contentItem: Label {
            text: headerButton.text
            font: headerButton.font
            color: headerButton.palette.buttonText
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
        }
    }

    ColumnLayout {
        id: body
        visible: section.expanded
        Layout.fillWidth: true
        Layout.leftMargin: 8
        Layout.rightMargin: 4
        spacing: 6
    }
}
