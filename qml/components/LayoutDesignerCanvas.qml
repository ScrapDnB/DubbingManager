pragma ComponentBehavior: Bound

import QtQuick
import QtWebEngine

Item {
    id: canvas

    implicitWidth: 560
    implicitHeight: 520

    required property var backend
    required property color softBorder
    required property color softAltRow
    property int zoomPercent: 100

    readonly property bool montage: backend.kind === "montage"

    function reloadPreview() {
        previewBrowser.loadHtml(backend.previewHtml)
    }

    Connections {
        target: canvas.backend
        function onDraftChanged() {
            Qt.callLater(canvas.reloadPreview)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: canvas.softAltRow
        radius: 6
        clip: true

        Rectangle {
            anchors.fill: parent
            anchors.margins: 12
            color: canvas.montage ? "#ffffff" : "#050505"
            border.width: 1
            border.color: canvas.softBorder
            radius: 5
            clip: true

            WebEngineView {
                id: previewBrowser
                anchors.fill: parent
                anchors.margins: 1
                backgroundColor: canvas.montage ? "#ffffff" : "#050505"
                zoomFactor: canvas.zoomPercent / 100

                onJavaScriptConsoleMessage: function(
                    level, message, lineNumber, sourceId
                ) {
                    var prefix = "__DM_LAYOUT__"
                    if (String(message).indexOf(prefix) !== 0)
                        return
                    var event
                    try {
                        event = JSON.parse(String(message).slice(prefix.length))
                    } catch (error) {
                        return
                    }
                    if (event.action === "select") {
                        canvas.backend.selectNode(String(event.nodeId || ""))
                    } else if (event.action === "remove") {
                        canvas.backend.removeNode(String(event.nodeId || ""))
                    } else if (event.action === "move") {
                        canvas.backend.moveNode(
                            String(event.nodeId || ""), Number(event.direction || 0)
                        )
                    } else if (event.action === "moveBefore") {
                        canvas.backend.moveNodeBefore(
                            String(event.sourceId || ""),
                            String(event.targetId || "")
                        )
                    } else if (event.action === "setWeight") {
                        canvas.backend.setNodeValue(
                            String(event.nodeId || ""),
                            "weight", Number(event.weight || 1)
                        )
                    }
                }
            }
        }
    }

    Component.onCompleted: Qt.callLater(reloadPreview)
}
