pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property string text: ""
    property url iconSource
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    signal clicked()

    implicitWidth: buttonLoader.implicitWidth
    implicitHeight: macOSStyle ? 28 : 32

    Loader {
        id: buttonLoader
        anchors.fill: parent
        sourceComponent: control.macOSStyle ? macButton : defaultButton
    }

    Component {
        id: defaultButton

        AdaptiveButton {
            text: control.text
            enabled: control.enabled
            onClicked: control.clicked()
        }
    }

    Component {
        id: macButton

        ItemDelegate {
            id: button
            text: control.text
            enabled: control.enabled
            leftPadding: 8
            rightPadding: 8
            topPadding: 2
            bottomPadding: 2
            onClicked: control.clicked()

            contentItem: Label {
                text: button.text
                color: button.enabled
                    ? button.palette.text : button.palette.placeholderText
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                radius: 6
                color: button.down
                    ? Qt.rgba(
                        button.palette.highlight.r,
                        button.palette.highlight.g,
                        button.palette.highlight.b,
                        0.22
                    )
                    : button.hovered
                        ? Qt.rgba(
                            button.palette.text.r,
                            button.palette.text.g,
                            button.palette.text.b,
                            0.07
                        )
                        : "transparent"
            }
        }
    }
}
