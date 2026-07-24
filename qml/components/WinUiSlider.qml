pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: control

    property real from: 0
    property real to: 1
    property real value: 0
    property real stepSize: 0
    readonly property bool pressed: sliderLoader.item
        ? sliderLoader.item.pressed : false
    readonly property bool windowsStyle: Qt.platform.os === "windows"
    implicitWidth: sliderLoader.item ? sliderLoader.item.implicitWidth : 160
    implicitHeight: sliderLoader.item ? sliderLoader.item.implicitHeight : 28

    signal moved()

    onValueChanged: {
        if (sliderLoader.item && sliderLoader.item.value !== value)
            sliderLoader.item.value = value
    }

    Loader {
        id: sliderLoader
        anchors.fill: parent
        sourceComponent: control.windowsStyle ? windowsSlider : nativeSlider
    }

    Component {
        id: nativeSlider

        Slider {
            from: control.from
            to: control.to
            value: control.value
            stepSize: control.stepSize
            onMoved: {
                control.value = value
                control.moved()
            }
        }
    }

    Component {
        id: windowsSlider

        Slider {
            id: slider

            from: control.from
            to: control.to
            value: control.value
            stepSize: control.stepSize
            implicitHeight: 28
            onMoved: {
                control.value = value
                control.moved()
            }

            background: Rectangle {
                x: slider.leftPadding
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: slider.availableWidth
                height: 4
                radius: 2
                color: Qt.rgba(
                    slider.palette.text.r, slider.palette.text.g,
                    slider.palette.text.b, 0.18
                )

                Rectangle {
                    width: slider.visualPosition * parent.width
                    height: parent.height
                    radius: parent.radius
                    color: slider.palette.highlight
                }
            }

            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition
                    * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                implicitWidth: 16
                implicitHeight: 16
                radius: 8
                border.width: 1
                border.color: slider.pressed ? slider.palette.highlight
                    : Qt.rgba(
                        slider.palette.text.r, slider.palette.text.g,
                        slider.palette.text.b, 0.28
                    )
                color: slider.pressed ? slider.palette.highlight : "#ffffff"

                Rectangle {
                    anchors.centerIn: parent
                    width: 6
                    height: 6
                    radius: 3
                    color: slider.pressed ? "#ffffff"
                        : slider.palette.highlight
                }
            }
        }
    }
}
