pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

Item {
    id: renderer

    required property var rows
    required property var replicaDelegate
    required property var windowConfig
    required property var colors
    property var primaryTextItem: null
    property string displayReplicaText: replicaDelegate.replicaText
    property bool replicaTextStyled: false
    signal editRequested()

    implicitHeight: contentColumn.implicitHeight
    Layout.fillWidth: true

    ColumnLayout {
        id: contentColumn
        width: renderer.width
        spacing: 6

        Repeater {
            model: renderer.rows || []

            RowLayout {
                id: layoutRow
                required property var modelData
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: Math.max(0, Number(modelData.gap || 0))

                Repeater {
                    model: layoutRow.modelData.cells || []

                    ColumnLayout {
                        id: layoutCell
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: Math.max(
                            1, Number(modelData.weight || 1)
                        ) * 100
                        Layout.minimumWidth: 1
                        Layout.alignment: Qt.AlignTop
                        spacing: Math.max(0, Number(modelData.gap || 0))

                        Repeater {
                            model: layoutCell.modelData.items || []

                            Loader {
                                id: itemLoader
                                required property var modelData
                                readonly property string itemType: String(
                                    modelData.type || "field"
                                )
                                readonly property string fieldName: String(
                                    modelData.field || "replica"
                                )
                                readonly property var itemStyle: modelData.style || ({})
                                readonly property bool fieldAllowed: itemType !== "field" || (
                                    fieldName === "timecode"
                                        ? Boolean(renderer.windowConfig.show_timecode)
                                    : fieldName === "character"
                                        ? Boolean(renderer.windowConfig.show_character)
                                    : fieldName === "actor"
                                        ? Boolean(renderer.windowConfig.show_actor)
                                    : Boolean(renderer.windowConfig.show_replica)
                                )
                                visible: fieldAllowed
                                Layout.fillWidth: true
                                Layout.preferredHeight: visible && item
                                    ? (item as Item).implicitHeight : 0
                                sourceComponent: itemType === "separator"
                                    ? separatorComponent
                                    : itemType === "spacer"
                                        ? spacerComponent : fieldComponent

                                Component {
                                    id: separatorComponent
                                    Rectangle {
                                        implicitHeight: 1
                                        color: renderer.colors.block_border || "#4D4D4D"
                                    }
                                }

                                Component {
                                    id: spacerComponent
                                    Item {
                                        implicitHeight: Math.max(
                                            2, Number(itemLoader.modelData.size || 12)
                                        )
                                    }
                                }

                                Component {
                                    id: fieldComponent
                                    Text {
                                        id: fieldText
                                        text: itemLoader.fieldName === "timecode"
                                            ? renderer.replicaDelegate.timeRangeText(false, false)
                                            : itemLoader.fieldName === "character"
                                                ? renderer.replicaDelegate.character
                                                : itemLoader.fieldName === "actor"
                                                    ? renderer.replicaDelegate.actor
                                                    : renderer.displayReplicaText
                                        textFormat: itemLoader.fieldName === "replica"
                                            && renderer.replicaTextStyled
                                            ? Text.StyledText : Text.PlainText
                                        color: !renderer.replicaDelegate.active
                                            ? (renderer.colors.inactive_text || "#3b3b3b")
                                            : itemLoader.fieldName === "timecode"
                                                ? (renderer.colors.tc || "#ffffff")
                                                : itemLoader.fieldName === "actor"
                                                    ? (renderer.colors.actor || "#AAAAAA")
                                                    : itemLoader.fieldName === "character"
                                                        && renderer.replicaDelegate.colorActive
                                                        ? renderer.replicaDelegate.actorColor
                                                        : (renderer.colors.active_text || "#ffffff")
                                        font.pixelSize: Math.max(
                                            8, Number(itemLoader.itemStyle.font_size || 24)
                                        )
                                        font.bold: Boolean(itemLoader.itemStyle.bold)
                                        font.italic: Boolean(itemLoader.itemStyle.italic)
                                        wrapMode: Text.WordWrap
                                        horizontalAlignment: itemLoader.itemStyle.alignment === "center"
                                            ? Text.AlignHCenter
                                            : itemLoader.itemStyle.alignment === "right"
                                                ? Text.AlignRight : Text.AlignLeft
                                        verticalAlignment: Text.AlignTop
                                        elide: itemLoader.fieldName === "replica"
                                            ? Text.ElideNone : Text.ElideRight
                                        font.underline: itemLoader.fieldName === "character"
                                            && fieldMouse.containsMouse

                                        Component.onCompleted: {
                                            if (itemLoader.fieldName === "replica")
                                                renderer.primaryTextItem = fieldText
                                        }

                                        MouseArea {
                                            id: fieldMouse
                                            anchors.fill: parent
                                            enabled: itemLoader.fieldName === "character"
                                                || itemLoader.fieldName === "replica"
                                            hoverEnabled: enabled
                                            cursorShape: enabled
                                                ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: renderer.editRequested()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
