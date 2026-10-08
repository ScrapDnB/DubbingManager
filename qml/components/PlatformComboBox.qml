import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    readonly property bool macOSStyle: Qt.platform.os === "osx"
    property string nativeMenuToken: ""

    Component.onCompleted: if (macOSStyle)
        nativeMenuToken = platformIntegration.newComboMenuToken()

    function openNativeMenu() {
        if (!macOSStyle || editable || count <= 0)
            return
        var labels = []
        for (var index = 0; index < count; ++index)
            labels.push(textAt(index))
        var point = mapToGlobal(0, height)
        platformIntegration.showComboMenu(
            nativeMenuToken,
            labels,
            currentIndex,
            point.x,
            point.y
        )
    }

    MouseArea {
        anchors.fill: parent
        visible: control.macOSStyle && !control.editable
        cursorShape: Qt.PointingHandCursor
        onClicked: control.openNativeMenu()
    }

    Connections {
        target: platformIntegration
        function onComboMenuSelected(token, index) {
            if (token !== control.nativeMenuToken)
                return
            control.currentIndex = index
            control.activated(index)
        }
    }
}
