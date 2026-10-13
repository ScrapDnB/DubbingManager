pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

Item {
    id: workspace
    objectName: "scriptWorkspace"
    required property var appBridge
    required property color softBorder
    required property color softMuted
    required property color panelSurface
    property bool inspectorVisible: true
    property bool active: false
    readonly property var backend: appBridge.workspace
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property color alternateSurface: Qt.tint(panelSurface, Qt.rgba(workspacePalette.text.r, workspacePalette.text.g, workspacePalette.text.b, 0.035))
    readonly property color headerSurface: Qt.tint(panelSurface, Qt.rgba(workspacePalette.text.r, workspacePalette.text.g, workspacePalette.text.b, 0.055))
    readonly property real playbackPosition: backend.hasVideo && video.mediaStatus >= MediaPlayer.LoadedMedia && video.mediaStatus <= MediaPlayer.BufferedMedia ? video.position / 1000 : backend.selected.lineId ? (navigationPosition >= 0 ? navigationPosition : backend.selected.start) : -1
    property real navigationPosition: -1
    property int pendingSeek: -1
    signal videoLinkRequested
    signal audiobookRequested
    signal teleprompterRequested
    signal castingRequested(string character)

    function focusSearch() {
        search.forceActiveFocus();
        search.selectAll();
    }
    function togglePlayback() {
        if (!backend.hasVideo || !workspace.active)
            return;
        if (video.playbackState === MediaPlayer.PlayingState)
            video.pause();
        else
            video.play();
    }
    function selectedIndex() {
        for (var i = 0; i < lines.count; ++i)
            if (backend.model.get(i).lineId === backend.selected.lineId)
                return i;
        return -1;
    }
    onActiveChanged: if (!active)
        video.pause()
    Connections {
        target: workspace.backend
        function onChanged() {
            if (!workspace.backend.selected.lineId) {
                workspace.navigationPosition = -1;
                workspace.pendingSeek = -1;
            }
        }
        function onSeekRequested(position) {
            workspace.navigationPosition = position / 1000;
            video.pause();
            workspace.pendingSeek = position;
            video.position = position;
            var index = workspace.selectedIndex();
            if (index >= 0) {
                lines.currentIndex = index;
                lines.positionViewAtIndex(index, ListView.Contain);
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: workspace.panelSurface
    }
    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal
        ColumnLayout {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 320
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.topMargin: 12
                Label {
                    text: workspace.appBridge.project.currentEpisode || qsTr("Рабочий текст")
                    font.pixelSize: 19
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Label {
                    visible: lines.width >= 400
                    text: workspace.backend.count + " / " + workspace.backend.totalCount + qsTr(" строк")
                    color: workspace.softMuted
                }
            }
            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                columns: lines.width < 520 ? 2 : 3
                TextField {
                    id: search
                    Layout.columnSpan: lines.width < 520 ? 2 : 1
                    objectName: "scriptSearch"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 70
                    placeholderText: qsTr("Найти в тексте")
                    Accessible.name: placeholderText
                    text: workspace.backend.searchText
                    selectByMouse: true
                    onTextEdited: workspace.backend.setSearchText(text)
                }
                PlatformComboBox {
                    id: actorFilter
                    Layout.fillWidth: true
                    Layout.minimumWidth: 80
                    Layout.preferredWidth: workspace.width < 1050 ? 130 : 180
                    model: workspace.appBridge.casting.actorFilterModel
                    textRole: "name"
                    valueRole: "id"
                    Accessible.name: qsTr("Фильтр реплик по актёру")
                    onActivated: workspace.backend.setActorFilter(currentValue)
                    function sync() {
                        currentIndex = Math.max(0, indexOfValue(workspace.backend.actorFilter));
                    }
                    onCountChanged: sync()
                    Connections {
                        target: workspace.backend
                        function onChanged() {
                            actorFilter.sync();
                        }
                    }
                }
                PlatformComboBox {
                    id: characterFilter
                    Layout.fillWidth: true
                    Layout.minimumWidth: 80
                    Layout.preferredWidth: workspace.width < 1050 ? 130 : 180
                    model: workspace.backend.characterModel
                    textRole: "label"
                    valueRole: "value"
                    Accessible.name: qsTr("Фильтр реплик по персонажу")
                    onActivated: workspace.backend.setCharacterFilter(currentValue)
                    function sync() {
                        currentIndex = Math.max(0, indexOfValue(workspace.backend.characterFilter));
                    }
                    onCountChanged: sync()
                    Connections {
                        target: workspace.backend
                        function onChanged() {
                            characterFilter.sync();
                        }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 30
                color: workspace.headerSurface
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    Label {
                        width: 36
                        text: "№"
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        width: lines.timeWidth
                        text: qsTr("Вход")
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        width: lines.timeWidth
                        text: qsTr("Выход")
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        visible: lines.showEnd
                    }
                    Label {
                        width: lines.characterWidth
                        text: qsTr("Персонаж / актёр")
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                    }
                    Label {
                        text: qsTr("Реплика")
                        visible: !lines.stackedRows
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
            PersistentListView {
                id: lines
                objectName: "scriptLines"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: workspace.backend.model
                activeFocusOnTab: true
                readonly property bool stackedRows: width < 520
                readonly property bool showEnd: width > 640
                readonly property int timeWidth: workspace.macOSStyle ? 96 : 112
                readonly property int characterWidth: width > 800 ? 170 : 132
                Keys.onReturnPressed: {
                    var row = workspace.backend.model.get(currentIndex);
                    if (row.lineId)
                        workspace.backend.selectLine(row.lineId);
                }
                Keys.onEnterPressed: {
                    var row = workspace.backend.model.get(currentIndex);
                    if (row.lineId)
                        workspace.backend.selectLine(row.lineId);
                }
                delegate: ItemDelegate {
                    id: row
                    required property int index
                    required property string lineId
                    required property int number
                    required property string inTime
                    required property string outTime
                    required property string character
                    required property string actor
                    required property string actorColor
                    required property var model
                    text: model.text
                    width: lines.viewportWidth
                    height: Math.max(66, lines.stackedRows ? metadata.implicitHeight + stackedBody.implicitHeight + 28 : body.implicitHeight + 22)
                    highlighted: workspace.backend.selected.lineId === lineId
                    onClicked: if (workspace.backend.selectLine(lineId))
                        lines.currentIndex = index
                    Accessible.name: number + ", " + inTime + ", " + character + ", " + text
                    contentItem: Column {
                        spacing: 8
                        Row {
                            id: metadata
                            Label {
                                width: 36
                                text: row.number
                                color: workspace.softMuted
                            }
                            Label {
                                width: lines.timeWidth
                                text: row.inTime
                                font.family: workspace.macOSStyle ? "Menlo" : "Consolas"
                                font.pixelSize: 11
                            }
                            Label {
                                width: lines.timeWidth
                                visible: lines.showEnd
                                text: row.outTime
                                font.family: workspace.macOSStyle ? "Menlo" : "Consolas"
                                font.pixelSize: 11
                            }
                            Column {
                                width: lines.characterWidth
                                spacing: 5
                                Row {
                                    spacing: 5
                                    Rectangle {
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: row.actorColor
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Label {
                                        text: row.character
                                        font.weight: Font.DemiBold
                                        width: lines.characterWidth - 20
                                        elide: Text.ElideRight
                                    }
                                }
                                Label {
                                    text: row.actor
                                    color: workspace.softMuted
                                    width: parent.width - 10
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }
                            Label {
                                id: body
                                visible: !lines.stackedRows
                                width: Math.max(80, row.width - 36 - lines.timeWidth * (lines.showEnd ? 2 : 1) - lines.characterWidth - 24)
                                text: row.text
                                wrapMode: Text.WordWrap
                                textFormat: Text.PlainText
                            }
                        }
                        Label {
                            id: stackedBody
                            visible: lines.stackedRows
                            width: parent.width
                            text: row.text
                            wrapMode: Text.WordWrap
                            textFormat: Text.PlainText
                        }
                    }
                    background: Rectangle {
                        color: row.highlighted ? Qt.tint(workspace.panelSurface, Qt.rgba(workspacePalette.highlight.r, workspacePalette.highlight.g, workspacePalette.highlight.b, 0.17)) : row.hovered ? Qt.tint(workspace.panelSurface, Qt.rgba(workspacePalette.highlight.r, workspacePalette.highlight.g, workspacePalette.highlight.b, 0.07)) : row.index % 2 ? workspace.alternateSurface : workspace.panelSurface
                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: workspace.softBorder
                        }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    width: parent.width - 40
                    visible: lines.count === 0
                    text: workspace.backend.totalCount ? qsTr("Нет реплик по выбранным фильтрам") : qsTr("Импортируйте ASS, SRT или DOCX, чтобы начать работу с текстом")
                    color: workspace.softMuted
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.bottomMargin: 10
                Label {
                    text: workspace.backend.fps + qsTr(" fps · таймкоды без пропуска кадров")
                    color: workspace.softMuted
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                AdaptiveButton {
                    text: qsTr("Телесуфлёр")
                    enabled: workspace.backend.totalCount > 0
                    onClicked: workspace.teleprompterRequested()
                }
            }
        }
        Rectangle {
            id: inspector
            objectName: "scriptInspector"
            visible: workspace.inspectorVisible
            color: workspace.panelSurface
            SplitView.minimumWidth: 270
            SplitView.preferredWidth: workspace.appBridge.uiState.intValue("main.scriptInspectorWidth", 330)
            onWidthChanged: if (width > 0 && workspace.active)
                inspectorSave.restart()
            Rectangle {
                width: 1
                height: parent.height
                color: workspace.softBorder
            }
            Timer {
                id: inspectorSave
                interval: 350
                onTriggered: workspace.appBridge.uiState.setIntValue("main.scriptInspectorWidth", inspector.width)
            }
            ScrollView {
                anchors.fill: parent
                anchors.margins: 12
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: width * 9 / 16
                        color: "#17191d"
                        clip: true
                        VideoOutput {
                            id: videoOutput
                            anchors.fill: parent
                            fillMode: VideoOutput.PreserveAspectFit
                        }
                        MediaPlayer {
                            id: video
                            objectName: "workspaceVideo"
                            videoOutput: videoOutput
                            audioOutput: AudioOutput {}
                            source: workspace.active && workspace.inspectorVisible ? workspace.backend.videoUrl : ""
                            autoPlay: false
                            onSourceChanged: workspace.pendingSeek = workspace.backend.selected.lineId ? Math.round(workspace.backend.selected.start * 1000) : -1
                            onMediaStatusChanged: {
                                if ((mediaStatus === MediaPlayer.LoadedMedia || mediaStatus === MediaPlayer.BufferedMedia) && workspace.pendingSeek >= 0) {
                                    position = workspace.pendingSeek;
                                    workspace.pendingSeek = -1;
                                }
                            }
                        }
                        Label {
                            anchors.centerIn: parent
                            width: parent.width - 20
                            visible: !workspace.backend.hasVideo || video.error !== MediaPlayer.NoError
                            text: !workspace.backend.hasVideo ? qsTr("Видео не привязано") : video.errorString
                            color: "#dddddf"
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        AdaptiveButton {
                            text: video.playbackState === MediaPlayer.PlayingState ? qsTr("Пауза") : qsTr("Пуск")
                            enabled: workspace.backend.hasVideo
                            onClicked: workspace.togglePlayback()
                        }
                        Slider {
                            Layout.fillWidth: true
                            from: 0
                            to: Math.max(1, video.duration)
                            value: video.position
                            enabled: workspace.backend.hasVideo && video.seekable
                            Accessible.name: qsTr("Позиция видео")
                            onMoved: video.position = value
                        }
                    }
                    SidebarCommandButton {
                        Layout.fillWidth: true
                        text: qsTr("Добавить или заменить видео…")
                        onClicked: workspace.videoLinkRequested()
                    }
                    ToolSeparator {
                        orientation: Qt.Horizontal
                        Layout.fillWidth: true
                    }
                    Label {
                        text: workspace.backend.selected.lineId ? qsTr("Реплика ") + workspace.backend.selected.number : qsTr("Выберите реплику")
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                    Label {
                        visible: !workspace.backend.selected.lineId
                        text: qsTr("Выберите строку для просмотра и редактирования")
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: workspace.softMuted
                    }
                    ColumnLayout {
                        visible: !!workspace.backend.selected.lineId
                        Layout.fillWidth: true
                        spacing: 8
                        enabled: !workspace.backend.isAudiobook
                        Label {
                            text: qsTr("Персонаж")
                            font.weight: Font.DemiBold
                        }
                        TextField {
                            objectName: "scriptCharacter"
                            Layout.fillWidth: true
                            text: workspace.backend.draft.character || ""
                            Accessible.name: qsTr("Персонаж реплики")
                            selectByMouse: true
                            onTextEdited: workspace.backend.setDraftField("character", text)
                        }
                        Label {
                            text: qsTr("Вход / выход · ЧЧ:ММ:СС:КК")
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            TextField {
                                objectName: "scriptInTime"
                                Layout.fillWidth: true
                                text: workspace.backend.draft.inTime || ""
                                Accessible.name: qsTr("Таймкод входа")
                                selectByMouse: true
                                onTextEdited: workspace.backend.setDraftField("inTime", text)
                            }
                            TextField {
                                objectName: "scriptOutTime"
                                Layout.fillWidth: true
                                text: workspace.backend.draft.outTime || ""
                                Accessible.name: qsTr("Таймкод выхода")
                                selectByMouse: true
                                onTextEdited: workspace.backend.setDraftField("outTime", text)
                            }
                        }
                        Label {
                            text: qsTr("Текст реплики")
                            font.weight: Font.DemiBold
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 140
                            TextArea {
                                id: textEditor
                                objectName: "scriptTextEditor"
                                text: workspace.backend.draft.text || ""
                                textFormat: TextEdit.PlainText
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                Accessible.name: qsTr("Текст реплики")
                                onTextChanged: if (activeFocus && text !== workspace.backend.draft.text)
                                    workspace.backend.setDraftField("text", text)
                            }
                        }
                        Label {
                            visible: workspace.backend.validationError.length > 0
                            text: workspace.backend.validationError
                            color: workspacePalette.highlight
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            AdaptiveButton {
                                objectName: "applyScriptEdit"
                                text: qsTr("Применить")
                                highlighted: true
                                enabled: workspace.backend.draftDirty && !workspace.backend.validationError
                                onClicked: workspace.backend.flush()
                            }
                            AdaptiveButton {
                                text: qsTr("Отменить")
                                enabled: workspace.backend.draftDirty
                                onClicked: workspace.backend.discardDraft()
                            }
                        }
                        Label {
                            visible: workspace.backend.draftDirty
                            text: qsTr("Корректная правка применяется при переходе к другой реплике или сохранении проекта")
                            color: workspace.softMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            font.pixelSize: 11
                        }
                        ToolSeparator {
                            orientation: Qt.Horizontal
                            Layout.fillWidth: true
                        }
                        Label {
                            text: qsTr("Актёры персонажа")
                            font.weight: Font.DemiBold
                        }
                        Label {
                            text: workspace.backend.selected.actor || ""
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: workspace.softMuted
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            PlatformComboBox {
                                id: actor
                                Layout.fillWidth: true
                                model: workspace.appBridge.casting.actorsModel
                                textRole: "name"
                                valueRole: "id"
                                Accessible.name: qsTr("Добавить актёра персонажу")
                            }
                            AdaptiveButton {
                                text: qsTr("Добавить")
                                enabled: !!actor.currentValue
                                onClicked: if (workspace.backend.flush())
                                    workspace.appBridge.casting.addActorToCharacter(workspace.backend.selected.character, actor.currentValue)
                            }
                        }
                        SidebarCommandButton {
                            Layout.fillWidth: true
                            text: qsTr("Открыть в кастинге")
                            onClicked: if (workspace.backend.flush())
                                workspace.castingRequested(workspace.backend.selected.character)
                        }
                    }
                    AdaptiveButton {
                        visible: workspace.backend.isAudiobook
                        text: qsTr("Открыть редактор книги")
                        onClicked: workspace.audiobookRequested()
                    }
                }
            }
        }
    }
    SystemPalette {
        id: workspacePalette
    }
}
