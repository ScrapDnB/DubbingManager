import QtQuick
import QtWebEngine

WebEngineView {
    id: browser

    property string previewHtml: ""
    property string episode: ""
    property string loadedHtml: ""
    property string loadedEpisode: ""
    property bool updating: false
    property point restorePosition: Qt.point(0, 0)

    function updatePreview(preservePosition) {
        // Serialize loads, including scroll restoration. Changes received during
        // a load are picked up afterwards using the latest backend state.
        if (updating || (loadedHtml === previewHtml && loadedEpisode === episode))
            return
        if (loadedEpisode !== episode)
            restorePosition = Qt.point(0, 0)
        else if (!preservePosition)
            restorePosition = scrollPosition
        loadedHtml = previewHtml
        loadedEpisode = episode
        updating = true
        loadHtml(loadedHtml)
    }

    onPreviewHtmlChanged: Qt.callLater(updatePreview)
    onEpisodeChanged: Qt.callLater(updatePreview)
    Component.onCompleted: Qt.callLater(updatePreview)

    onLoadingChanged: function(request) {
        if (request.status === WebEngineView.LoadSucceededStatus) {
            runJavaScript(
                "window.scrollTo(" + restorePosition.x + "," + restorePosition.y + ")",
                function() {
                    browser.updating = false
                    // Chromium reports scrollPosition asynchronously; queued
                    // updates must keep the saved position until it catches up.
                    browser.updatePreview(true)
                }
            )
        } else if (request.status === WebEngineView.LoadFailedStatus
                   || request.status === WebEngineView.LoadStoppedStatus) {
            updating = false
            updatePreview(true)
        }
    }
}
