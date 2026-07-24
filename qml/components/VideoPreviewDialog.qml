pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

NativeDialogWindow {
    id: dialog
    objectName: "videoPreviewDialog"

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    readonly property var videoBackend: appBridge ? appBridge.video : null
    property int characterColumnWidth: Math.max(110, Math.min(170, width * 0.17))
    property int actorColumnWidth: Math.max(110, Math.min(170, width * 0.17))
    readonly property int rowPadding: 8
    readonly property int columnSpacing: 10
    readonly property int timeColumnWidth: 76
    readonly property int characterColumnX: rowPadding + timeColumnWidth + columnSpacing
    readonly property int actorColumnX: characterColumnX + characterColumnWidth + columnSpacing
    readonly property int replicaColumnX: actorColumnX + actorColumnWidth + columnSpacing

    modal: true
    title: qsTr("Просмотр · серия ") + (videoBackend ? videoBackend.episode : "")
    standardButtons: Dialog.NoButton
    width: boundedWidth(1020, 32)
    height: boundedHeight(720, 32)

    function formatPosition(milliseconds) {
        var totalSeconds = Math.max(0, Math.floor(Number(milliseconds || 0) / 1000))
        var hours = Math.floor(totalSeconds / 3600)
        var minutes = Math.floor((totalSeconds % 3600) / 60)
        var seconds = totalSeconds % 60
        var prefix = hours > 0 ? String(hours).padStart(2, "0") + ":" : ""
        return prefix + String(minutes).padStart(2, "0") + ":"
            + String(seconds).padStart(2, "0")
    }

    function togglePlayback() {
        if (!videoBackend || !videoBackend.hasVideo) {
            return
        }
        if (video.playbackState === MediaPlayer.PlayingState) {
            video.pause()
        } else {
            video.play()
        }
    }

    function openFor(character) {
        video.stop()
        video.source = ""
        seekSlider.value = 0
        if (!videoBackend || !videoBackend.prepare(character || "")) {
            return
        }
        characterCombo.syncValue()
        video.source = videoBackend.videoUrl
        open()
    }

    onClosed: {
        video.stop()
        video.source = ""
        seekSlider.value = 0
    }

    Shortcut {
        sequence: "Space"
        enabled: dialog.visible && dialog.videoBackend && dialog.videoBackend.hasVideo
        onActivated: dialog.togglePlayback()
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label { text: qsTr("Персонаж:") }

            ComboBox {
                id: characterCombo
                Layout.preferredWidth: 230
                model: dialog.videoBackend ? dialog.videoBackend.characterModel : null
                textRole: "label"
                valueRole: "value"
                onActivated: dialog.videoBackend.setCharacter(currentValue)

                function syncValue() {
                    if (!dialog.videoBackend) {
                        return
                    }
                    var characterIndex = indexOfValue(dialog.videoBackend.character)
                    currentIndex = characterIndex >= 0 ? characterIndex : 0
                }
            }

            Label {
                text: (dialog.videoBackend ? dialog.videoBackend.count : 0) + " реплик"
                color: dialog.softMuted
            }

            Item { Layout.fillWidth: true }

            Label {
                visible: dialog.videoBackend && dialog.videoBackend.hasVideo
                text: dialog.videoBackend ? dialog.videoBackend.videoName : ""
                color: dialog.softMuted
                elide: Text.ElideMiddle
                Layout.maximumWidth: 280
            }
        }

        Rectangle {
            visible: dialog.videoBackend && !dialog.videoBackend.hasVideo
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 42 : 0
            color: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.08)
            border.color: dialog.softBorder

            Label {
                anchors.fill: parent
                anchors.margins: 10
                text: qsTr("Видео для этой серии не привязано. Доступен список реплик.")
                color: dialog.softMuted
                verticalAlignment: Text.AlignVCenter
                wrapMode: Text.WordWrap
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            Rectangle {
                visible: dialog.videoBackend && dialog.videoBackend.hasVideo
                SplitView.preferredHeight: visible ? 320 : 0
                SplitView.minimumHeight: visible ? 180 : 0
                color: "#000000"
                clip: true

                Video {
                    id: video
                    objectName: "videoPreviewPlayer"
                    anchors.fill: parent
                    autoPlay: false
                    fillMode: VideoOutput.PreserveAspectFit

                    onPositionChanged: {
                        if (!seekSlider.pressed) {
                            seekSlider.value = position
                        }
                    }
                    onDurationChanged: seekSlider.to = Math.max(1, duration)
                }

                Label {
                    anchors.centerIn: parent
                    visible: video.error !== MediaPlayer.NoError
                    text: video.errorString.length > 0
                        ? video.errorString
                        : "Не удалось воспроизвести видео"
                    color: "#FFFFFF"
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    width: Math.min(parent.width - 40, 520)
                }
            }

            Item {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 180

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 4

                    RowLayout {
                        visible: dialog.videoBackend && dialog.videoBackend.hasVideo
                        Layout.fillWidth: true
                        Layout.preferredHeight: visible ? 36 : 0
                        spacing: 8

                        AdaptiveButton {
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 30
                            text: video.playbackState === MediaPlayer.PlayingState ? "Ⅱ" : "▶"
                            onClicked: dialog.togglePlayback()
                            ToolTip.visible: hovered
                            ToolTip.text: video.playbackState === MediaPlayer.PlayingState
                                ? "Пауза"
                                : "Воспроизвести"
                        }

                        Slider {
                            id: seekSlider
                            Layout.fillWidth: true
                            from: 0
                            to: 1
                            live: true
                            onMoved: video.position = value
                        }

                        Label {
                            text: dialog.formatPosition(video.position) + " / "
                                + dialog.formatPosition(video.duration)
                            color: dialog.softMuted
                            Layout.preferredWidth: video.duration >= 3600000 ? 112 : 92
                            horizontalAlignment: Text.AlignRight
                        }

                        AdaptiveButton {
                            Layout.preferredWidth: 38
                            Layout.preferredHeight: 30
                            text: video.muted ? "×" : "♪"
                            onClicked: video.muted = !video.muted
                            ToolTip.visible: hovered
                            ToolTip.text: video.muted ? "Включить звук" : "Выключить звук"
                        }

                        CheckBox {
                            id: syncCheck
                            text: qsTr("Переходить по клику")
                            checked: true
                            ToolTip.visible: hovered
                            ToolTip.text: qsTr("Клик по реплике перематывает видео к её началу.")
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 30
                        color: dialog.softHeader
                        border.color: dialog.softBorder
                        clip: true

                        Item {
                            anchors.fill: parent

                            Label { x: dialog.rowPadding; width: dialog.timeColumnWidth; height: parent.height; text: qsTr("Время"); font.bold: true; verticalAlignment: Text.AlignVCenter }
                            Label { x: dialog.characterColumnX; width: dialog.characterColumnWidth; height: parent.height; text: qsTr("Персонаж"); font.bold: true; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                            Label { x: dialog.actorColumnX; width: dialog.actorColumnWidth; height: parent.height; text: qsTr("Актёр"); font.bold: true; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter }
                            Label { x: dialog.replicaColumnX; width: Math.max(0, parent.width - x - dialog.rowPadding); height: parent.height; text: qsTr("Реплика"); font.bold: true; horizontalAlignment: Text.AlignLeft; verticalAlignment: Text.AlignVCenter }
                        }
                    }

                    PersistentListView {
                        id: replicaList
                        objectName: "videoPreviewReplicaList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        currentIndex: -1
                        model: dialog.videoBackend ? dialog.videoBackend.model : null

                        delegate: Rectangle {
                            id: replicaRow
                            required property int index
                            required property int startMs
                            required property int endMs
                            required property string time
                            required property string character
                            required property string actor
                            required property string text
                            required property color actorColor
                            readonly property bool activeLine: dialog.videoBackend
                                && dialog.videoBackend.hasVideo
                                && video.position >= startMs
                                && video.position < endMs

                            width: replicaList.viewportWidth
                            height: Math.max(38, replicaText.implicitHeight + 12)
                            color: activeLine
                                ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.24)
                                : replicaList.currentIndex === index
                                    ? Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.14)
                                    : replicaHover.hovered
                                        ? dialog.softHover
                                        : index % 2 === 0
                                            ? dialog.softRow
                                            : dialog.softAltRow

                            HoverHandler { id: replicaHover }

                            TapHandler {
                                onTapped: {
                                    replicaList.currentIndex = replicaRow.index
                                    if (
                                        syncCheck.checked
                                        && dialog.videoBackend
                                        && dialog.videoBackend.hasVideo
                                    ) {
                                        video.position = replicaRow.startMs
                                        video.play()
                                    }
                                }
                            }

                            Item {
                                anchors.fill: parent

                                Label {
                                    x: dialog.rowPadding
                                    width: dialog.timeColumnWidth
                                    height: parent.height
                                    text: replicaRow.time
                                    color: dialog.softMuted
                                    verticalAlignment: Text.AlignVCenter
                                }
                                Label {
                                    x: dialog.characterColumnX
                                    width: dialog.characterColumnWidth
                                    height: parent.height
                                    text: replicaRow.character
                                    font.bold: replicaRow.activeLine
                                    elide: Text.ElideRight
                                    verticalAlignment: Text.AlignVCenter
                                }
                                RowLayout {
                                    x: dialog.actorColumnX
                                    width: dialog.actorColumnWidth
                                    height: parent.height
                                    spacing: 6
                                    Rectangle {
                                        Layout.preferredWidth: 12
                                        Layout.preferredHeight: 12
                                        radius: 2
                                        color: replicaRow.actorColor
                                    }
                                    Label {
                                        text: replicaRow.actor
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                                Text {
                                    id: replicaText
                                    x: dialog.replicaColumnX
                                    width: Math.max(0, parent.width - x - dialog.rowPadding)
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: replicaRow.text
                                    color: palette.text
                                    horizontalAlignment: Text.AlignLeft
                                    verticalAlignment: Text.AlignVCenter
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        Label {
                            anchors.centerIn: parent
                            visible: replicaList.count === 0
                            text: qsTr("Для выбранного персонажа нет реплик")
                            color: dialog.softMuted
                        }
                    }
                }
            }
        }

        DialogButtonBox {
            Layout.fillWidth: true
            AdaptiveButton {
                text: qsTr("Закрыть")
                onClicked: dialog.close()
            }
        }
    }

    Connections {
        target: dialog.videoBackend
        function onChanged() { characterCombo.syncValue() }
    }
}
