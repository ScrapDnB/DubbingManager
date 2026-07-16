pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebChannel
import QtWebEngine

NativeDialogWindow {
    id: window
    objectName: "chapterMarkupWindow"

    required property var backend
    required property color softBorder
    required property color softHeader
    required property color softMuted

    title: qsTr("Структура глав")
    modal: true
    width: boundedWidth(1220, 24)
    height: boundedHeight(820, 24)
    minimumWidth: 820
    minimumHeight: 600
    standardButtons: Dialog.NoButton

    function openEditor() {
        backend.prepareChapterMarkup()
        titleField.text = backend.selectedBoundary
        sourceView.url = backend.chapterMarkupUrl
        open()
    }

    function callEditor(name, argument) {
        var expression = "window.dmChapters." + name + "("
        if (argument !== undefined)
            expression += JSON.stringify(argument)
        expression += ")"
        sourceView.runJavaScript(expression)
    }

    QtObject {
        id: chapterPage
        WebChannel.id: "chapterPage"

        function updateBoundaries(payload) {
            window.backend.updateBoundaries(String(payload))
        }
        function boundarySelected(title) {
            window.backend.selectBoundary(String(title))
            titleField.text = String(title)
        }
        function boundaryRenamed(oldTitle, newTitle) {
            window.backend.boundaryRenamed(String(oldTitle), String(newTitle))
            titleField.text = String(newTitle)
        }
        function boundaryDeleted(title) {
            window.backend.boundaryDeleted(String(title))
        }
    }

    WebChannel {
        id: chapterChannel
        registeredObjects: [chapterPage]
    }

    content: SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Pane {
            SplitView.preferredWidth: 285
            SplitView.minimumWidth: 245
            SplitView.maximumWidth: 390
            padding: 8

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                Label {
                    text: qsTr("Главы")
                    font.bold: true
                }

                ListView {
                    id: chapterList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: window.backend.markupChaptersModel
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: ItemDelegate {
                        required property string title
                        required property bool selected
                        width: ListView.view.width
                        text: title
                        highlighted: selected
                        onClicked: {
                            titleField.text = title
                            window.backend.selectBoundary(title)
                            window.callEditor("selectTitle", title)
                        }
                    }
                }

                Label {
                    text: qsTr("Название")
                    color: window.softMuted
                }
                TextField {
                    id: titleField
                    Layout.fillWidth: true
                    placeholderText: qsTr("Название главы")
                    selectByMouse: true
                    onAccepted: renameButton.clicked()
                }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 6
                    rowSpacing: 6

                    Button {
                        text: qsTr("Добавить здесь")
                        enabled: titleField.text.trim().length > 0
                        Layout.fillWidth: true
                        onClicked: {
                            var title = titleField.text.trim()
                            if (title === window.backend.selectedBoundary)
                                title = window.backend.suggestedChapterTitle()
                            titleField.text = title
                            window.callEditor("add", title)
                        }
                    }
                    Button {
                        text: qsTr("Переместить сюда")
                        enabled: window.backend.selectedBoundary.length > 0
                        Layout.fillWidth: true
                        onClicked: window.callEditor("moveSelected")
                    }
                    Button {
                        id: renameButton
                        text: qsTr("Переименовать")
                        enabled: window.backend.selectedBoundary.length > 0
                            && titleField.text.trim().length > 0
                        Layout.fillWidth: true
                        onClicked: window.callEditor("renameSelected", titleField.text.trim())
                    }
                    Button {
                        text: qsTr("Удалить границу")
                        enabled: window.backend.selectedBoundary.length > 0
                        Layout.fillWidth: true
                        onClicked: deleteConfirm.open()
                    }
                }

                Label {
                    text: qsTr("Поставьте курсор перед нужным абзацем. Границы можно также перетаскивать мышью.")
                    color: window.softMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }

        Rectangle {
            SplitView.fillWidth: true
            color: palette.base
            border.color: window.softBorder
            clip: true

            WebEngineView {
                id: sourceView
                anchors.fill: parent
                anchors.margins: 1
                webChannel: chapterChannel
                backgroundColor: "#ecebea"
                onLoadingChanged: function(request) {
                    if (request.status === WebEngineView.LoadSucceededStatus)
                        window.callEditor("selectTitle", window.backend.selectedBoundary)
                }
            }
        }
    }

    footer: DialogButtonBox {
        anchors.fill: parent
        Button {
            text: qsTr("Отмена")
            onClicked: window.close()
        }
        Button {
            text: qsTr("Применить")
            highlighted: true
            onClicked: {
                sourceView.runJavaScript("window.dmChapters.send()", function() {
                    if (window.backend.applyChapterMarkup())
                        window.close()
                })
            }
        }
    }

    NativeDialogWindow {
        id: deleteConfirm
        ownerWindow: window
        title: qsTr("Удалить границу главы?")
        width: 420
        height: 180
        standardButtons: Dialog.Yes | Dialog.Cancel
        content: Label {
            anchors.fill: parent
            text: qsTr("Текст книги останется на месте и войдёт в соседнюю главу.")
            wrapMode: Text.WordWrap
        }
        onAccepted: window.callEditor("deleteSelected")
    }
}
