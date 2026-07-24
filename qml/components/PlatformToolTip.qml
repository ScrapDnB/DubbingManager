import QtQuick
import QtQuick.Controls

Item {
    id: tip

    required property var target
    property string text: ""
    property bool active: target !== null
        && target.visible
        && target.enabled
        && Boolean(target["hovered"])
        && text.length > 0
    property int delay: 500
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    visible: false
    width: 0
    height: 0

    onActiveChanged: {
        if (active && macOSStyle) {
            showTimer.restart()
        } else {
            showTimer.stop()
            if (macOSStyle)
                platformIntegration.hideToolTip()
        }
    }

    onTextChanged: if (!text.length && macOSStyle)
        platformIntegration.hideToolTip()

    Component.onDestruction: if (macOSStyle)
        platformIntegration.hideToolTip()

    Timer {
        id: showTimer
        interval: tip.delay
        onTriggered: {
            if (!tip.active)
                return
            var point = tip.target.mapToGlobal(
                tip.target.width / 2,
                tip.target.height
            )
            platformIntegration.showToolTip(tip.text, point.x, point.y)
        }
    }

    ToolTip {
        parent: tip.target
        visible: !tip.macOSStyle && tip.active
        text: tip.text
        delay: tip.delay
    }
}
