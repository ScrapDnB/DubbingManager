import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: table

    required property var appBridge
    readonly property var castingBackend: appBridge ? appBridge.casting : null
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    signal relinkSourceRequested(string episode)
    signal videoPreviewRequested(string character)
    signal filesDropped(var urls)
    property bool framed: true
    property string actorColorDisplayMode: "marker"
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property bool actorCellColorFill:
        actorColorDisplayMode === "cell"
    readonly property bool darkTheme: (
        palette.base.r * 0.2126
        + palette.base.g * 0.7152
        + palette.base.b * 0.0722
    ) < 0.5
    property color selectedRow: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    SplitView.fillWidth: true
    Layout.minimumWidth: 0
    clip: true

    Rectangle {
        anchors.fill: parent
        visible: table.framed
        color: "transparent"
        border.color: table.macOSStyle ? "transparent" : table.softBorder
        border.width: fileDropArea.containsDrag ? 2 : 1
    }

    DropArea {
        id: fileDropArea
        anchors.fill: parent
        z: 20

        onDropped: function(drop) {
            if (drop.hasUrls) {
                table.filesDropped(drop.urls)
                drop.acceptProposedAction()
            }
        }
    }

    readonly property int tableHorizontalPadding: 16
    readonly property int tableSpacing: 48
    readonly property int lineColumnWidth: 58
    readonly property int ringsColumnWidth: 54
    readonly property int wordsColumnWidth: 52
    readonly property int scopeColumnWidth: 70
    readonly property int previewColumnWidth: 30
    readonly property int fixedColumnsWidth: lineColumnWidth + ringsColumnWidth + wordsColumnWidth + scopeColumnWidth + previewColumnWidth
    readonly property int flexibleWidth: Math.max(0, characterView.viewportWidth - tableHorizontalPadding - tableSpacing - fixedColumnsWidth)
    // Actor cells need room for names, colour markers, and row actions. Give
    // them a progressively larger share while the table is being narrowed.
    readonly property real characterColumnShare: Math.min(
        0.55, Math.max(0.42, 0.42 + flexibleWidth / 5000)
    )
    readonly property int characterColumnWidth: Math.floor(
        flexibleWidth * characterColumnShare
    )
    readonly property int actorColumnWidth: Math.max(0, flexibleWidth - characterColumnWidth)
    readonly property int characterColumnX: 8
    readonly property int lineColumnX: characterColumnX + characterColumnWidth + 8
    readonly property int ringsColumnX: lineColumnX + lineColumnWidth + 8
    readonly property int wordsColumnX: ringsColumnX + ringsColumnWidth + 8
    readonly property int scopeColumnX: wordsColumnX + wordsColumnWidth + 8
    readonly property int actorColumnX: scopeColumnX + scopeColumnWidth + 8
    readonly property int previewColumnX: actorColumnX + actorColumnWidth + 8
    property string pendingCharacter: ""
    property var pendingActorIds: []
    property var collapsedActorCells: ({})
    property var dismissedSourceWarnings: ({})
    property string renameCharacterSource: ""

    readonly property string sourceWarningKey: {
        if (!appBridge || !appBridge.projectFiles)
            return ""
        return appBridge.project.currentEpisode + "|"
            + appBridge.projectFiles.currentEpisodeSourcePath
    }

    function sourceWarningDismissed() {
        return dismissedSourceWarnings[sourceWarningKey] === true
    }

    function dismissSourceWarning() {
        var next = Object.assign({}, dismissedSourceWarnings)
        next[sourceWarningKey] = true
        dismissedSourceWarnings = next
    }

    function sortTitle(label, key) {
        if (!castingBackend || castingBackend.characterSortKey !== key)
            return label
        return label + (castingBackend.characterSortAscending ? " ↑" : " ↓")
    }

    function characterAt(index) {
        if (!castingBackend || index < 0)
            return ""
        return castingBackend.charactersModel.get(index).character || ""
    }

    function clearCharacterSelection() {
        characterView.currentIndex = -1
        if (castingBackend)
            castingBackend.selectCharacter("")
    }

    function toggleCharacterSelection(character, index) {
        if (castingBackend && castingBackend.selectedCharacter === character) {
            clearCharacterSelection()
            return
        }
        characterView.currentIndex = index
        characterView.forceActiveFocus()
        if (castingBackend)
            castingBackend.selectCharacter(character)
    }

    function actorCellCollapsed(character) {
        return collapsedActorCells[character] === true
    }

    function toggleActorCell(character) {
        var next = Object.assign({}, collapsedActorCells)
        next[character] = !actorCellCollapsed(character)
        collapsedActorCells = next
    }

    Menu {
        id: scopeMenu

        MenuItem {
            text: qsTr("Проект")
            onTriggered: if (table.castingBackend) table.castingBackend.setAssignmentScope(table.pendingCharacter, "global")
        }

        MenuItem {
            text: qsTr("Серия")
            onTriggered: if (table.castingBackend) table.castingBackend.setAssignmentScope(table.pendingCharacter, "episode")
        }
    }

    Menu {
        id: actorMenu

        MenuItem {
            text: qsTr("-")
            onTriggered: if (table.castingBackend) table.castingBackend.assignActor(table.pendingCharacter, "")
        }

        MenuSeparator {}

        Repeater {
            model: table.castingBackend ? table.castingBackend.actorFilterModel : null

            MenuItem {
                required property string id
                required property string name

                visible: id.length > 0
                height: visible ? implicitHeight : 0
                text: name
                onTriggered: if (table.castingBackend) table.castingBackend.assignActor(table.pendingCharacter, id)
            }
        }
    }

    Menu {
        id: addActorMenu

        Repeater {
            model: table.castingBackend ? table.castingBackend.actorFilterModel : null

            MenuItem {
                required property string id
                required property string name

                visible: id.length > 0 && table.pendingActorIds.indexOf(id) < 0
                height: visible ? implicitHeight : 0
                text: name
                onTriggered: if (table.castingBackend)
                    table.castingBackend.addActorToCharacter(
                        table.pendingCharacter, id
                    )
            }
        }
    }

    NativeDialogWindow {
        id: renameCharacterDialog
        ownerWindow: table.Window.window
        modal: true
        title: qsTr("Переименовать персонажа")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 380
        height: 150

        onOpened: {
            renameCharacterField.text = table.renameCharacterSource
            renameCharacterField.selectAll()
            renameCharacterField.forceActiveFocus()
        }
        onAccepted: if (table.castingBackend) table.castingBackend.renameCharacter(table.renameCharacterSource, renameCharacterField.text)

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            TextField {
                id: renameCharacterField
                Layout.fillWidth: true
                placeholderText: qsTr("Имя персонажа")
                selectByMouse: true
                onAccepted: renameCharacterDialog.accept()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: table.framed ? 6 : 0
        spacing: 6

        Rectangle {
            visible: table.appBridge && table.appBridge.projectFiles
                && table.appBridge.projectFiles.currentEpisodeSourceMissing
                && !table.sourceWarningDismissed()
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: visible
                ? Math.max(table.macOSStyle ? 34 : 44,
                    relinkButton.implicitHeight + 6) : 0
            Layout.maximumHeight: Layout.preferredHeight
            color: Qt.rgba(0.78, 0.42, 0.16, 0.12)
            border.color: Qt.rgba(0.78, 0.42, 0.16, 0.42)
            radius: table.macOSStyle ? 8 : 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    text: qsTr("Исходный файл серии не найден: ")
                        + (table.appBridge && table.appBridge.projectFiles
                            ? table.appBridge.projectFiles.currentEpisodeSourcePath
                            : "")
                    elide: Text.ElideMiddle
                }
                RowLayout {
                    spacing: 4

                    AdaptiveButton {
                        id: relinkButton
                        text: qsTr("Перепривязать")
                        Layout.preferredWidth: table.macOSStyle ? 106 : 132
                        onClicked: table.relinkSourceRequested(
                            table.appBridge.project.currentEpisode
                        )
                    }
                    CompactToolButton {
                        buttonSize: table.macOSStyle ? 24 : 34
                        glyphSize: table.macOSStyle ? 13 : 22
                        iconSource: Qt.resolvedUrl("../icons/x.svg")
                        toolTipText: qsTr("Скрыть предупреждение")
                        Accessible.name: qsTr("Скрыть предупреждение")
                        onClicked: table.dismissSourceWarning()
                    }
                }
            }
        }

        TableHeaderSurface {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: table.macOSStyle ? 24 : 28
            Layout.maximumHeight: Layout.preferredHeight
            softHeader: table.softHeader
            softBorder: table.softBorder
            clip: true

            Item {
                anchors.fill: parent

                TableHeaderButton { x: table.characterColumnX; width: table.characterColumnWidth; height: parent.height; text: table.sortTitle("Персонаж", "character"); onClicked: table.castingBackend.setCharacterSort("character"); Accessible.name: qsTr("Сортировать по персонажу") }
                TableHeaderButton { x: table.lineColumnX; width: table.lineColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Строк", "lines"); onClicked: table.castingBackend.setCharacterSort("lines"); Accessible.name: qsTr("Сортировать по строкам") }
                TableHeaderButton { x: table.ringsColumnX; width: table.ringsColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Колец", "rings"); onClicked: table.castingBackend.setCharacterSort("rings"); Accessible.name: qsTr("Сортировать по кольцам") }
                TableHeaderButton { x: table.wordsColumnX; width: table.wordsColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Слов", "words"); onClicked: table.castingBackend.setCharacterSort("words"); Accessible.name: qsTr("Сортировать по словам") }
                TableHeaderButton { x: table.scopeColumnX; width: table.scopeColumnWidth; height: parent.height; textAlignment: Text.AlignHCenter; text: table.sortTitle("Область", "scope"); onClicked: table.castingBackend.setCharacterSort("scope"); Accessible.name: qsTr("Сортировать по области назначения") }
                TableHeaderButton { x: table.actorColumnX; width: table.actorColumnWidth; height: parent.height; text: table.sortTitle("Актёр", "actor"); onClicked: table.castingBackend.setCharacterSort("actor"); Accessible.name: qsTr("Сортировать по актёру") }
                TableHeaderButton {
                    id: allReplicasButton
                    x: table.previewColumnX
                    width: table.previewColumnWidth
                    height: parent.height
                    text: qsTr("▶")
                    textAlignment: Text.AlignHCenter
                    Accessible.name: qsTr("Все реплики серии")
                    onClicked: table.videoPreviewRequested("")
                    PlatformToolTip {
                        target: allReplicasButton
                        text: qsTr("Все реплики серии")
                    }
                }
            }
        }

        PersistentListView {
            id: characterView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: table.castingBackend ? table.castingBackend.charactersModel : null
            activeFocusOnTab: true
            keyNavigationEnabled: true
            Accessible.name: qsTr("Персонажи серии")
            Keys.onUpPressed: {
                if (count > 0) currentIndex = Math.max(0, currentIndex - 1)
                table.castingBackend.selectCharacter(table.characterAt(currentIndex))
            }
            Keys.onDownPressed: {
                if (count > 0) currentIndex = Math.min(count - 1, currentIndex + 1)
                table.castingBackend.selectCharacter(table.characterAt(currentIndex))
            }
            Keys.onReturnPressed: table.videoPreviewRequested(table.characterAt(currentIndex))
            Keys.onEnterPressed: table.videoPreviewRequested(table.characterAt(currentIndex))
            Keys.onEscapePressed: table.clearCharacterSelection()
            // A tap below the final row is an explicit way to leave selection mode.
            TapHandler {
                onTapped: function(eventPoint) {
                    var rowIndex = characterView.indexAt(
                        eventPoint.position.x,
                        eventPoint.position.y + characterView.contentY
                    )
                    if (rowIndex < 0)
                        table.clearCharacterSelection()
                }
            }
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Home) {
                    if (count > 0) currentIndex = 0
                    table.castingBackend.selectCharacter(table.characterAt(currentIndex))
                    event.accepted = true
                } else if (event.key === Qt.Key_End) {
                    if (count > 0) currentIndex = count - 1
                    table.castingBackend.selectCharacter(table.characterAt(currentIndex))
                    event.accepted = true
                } else if (event.key === Qt.Key_F2 && currentIndex >= 0) {
                    table.renameCharacterSource = table.characterAt(currentIndex)
                    renameCharacterDialog.open()
                    event.accepted = true
                }
            }

            delegate: Rectangle {
                id: characterRow
                required property int index
                required property var model
                width: characterView.viewportWidth
                readonly property bool hasMultipleActors: model.actorEntries.length > 1
                readonly property bool actorCellIsCollapsed: hasMultipleActors
                    && table.actorCellCollapsed(model.character)
                height: actorCellIsCollapsed
                    ? 32
                    : Math.max(32, (model.actorEntries.length || 1) * 24 + 8)
                color: table.castingBackend && table.castingBackend.selectedCharacter === model.character ? table.selectedRow : (characterHover.hovered ? table.softHover : (index % 2 === 0 ? table.softRow : table.softAltRow))
                clip: true
                Accessible.role: Accessible.ListItem
                Accessible.name: model.character + ", " + model.actor

                HoverHandler {
                    id: characterHover
                }

                TapHandler {
                    onTapped: {
                        table.toggleCharacterSelection(
                            model.character, characterRow.index
                        )
                    }
                }

                Item {
                    anchors.fill: parent

                    Label {
                        x: table.characterColumnX
                        width: table.characterColumnWidth
                        height: parent.height
                        text: model.character
                        elide: Text.ElideRight
                        clip: true
                        verticalAlignment: Text.AlignVCenter

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            onClicked: {
                                table.toggleCharacterSelection(
                                    model.character, characterRow.index
                                )
                            }
                            onDoubleClicked: {
                                table.renameCharacterSource = model.character
                                renameCharacterDialog.open()
                            }
                        }
                    }
                    Label { x: table.lineColumnX; width: table.lineColumnWidth; height: parent.height; text: model.lines; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { x: table.ringsColumnX; width: table.ringsColumnWidth; height: parent.height; text: model.rings; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { x: table.wordsColumnX; width: table.wordsColumnWidth; height: parent.height; text: model.words; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Rectangle {
                        x: table.scopeColumnX
                        width: table.scopeColumnWidth
                        height: parent.height
                        color: "transparent"
                        clip: true

                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 2
                            radius: table.macOSStyle ? 5 : 2
                            color: scopeHover.hovered
                                ? Qt.rgba(
                                    palette.highlight.r,
                                    palette.highlight.g,
                                    palette.highlight.b,
                                    table.darkTheme ? 0.22 : 0.12
                                )
                                : "transparent"
                        }

                        Text {
                            id: scopeChevron
                            anchors.right: parent.right
                            anchors.rightMargin: 5
                            anchors.verticalCenter: parent.verticalCenter
                            text: "▾"
                            color: table.softMuted
                            font.pixelSize: 13
                            renderType: Text.NativeRendering
                        }

                        Label {
                            anchors.left: parent.left
                            anchors.right: scopeChevron.left
                            anchors.leftMargin: 3
                            anchors.rightMargin: 1
                            anchors.verticalCenter: parent.verticalCenter
                            text: model.scope
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        HoverHandler {
                            id: scopeHover
                            cursorShape: Qt.PointingHandCursor
                        }

                        TapHandler {
                            onTapped: {
                                characterView.currentIndex = characterRow.index
                                characterView.forceActiveFocus()
                                if (table.castingBackend)
                                    table.castingBackend.selectCharacter(model.character)
                                table.pendingCharacter = model.character
                                scopeMenu.popup()
                            }
                        }
                    }

                    Rectangle {
                        x: table.actorColumnX
                        width: table.actorColumnWidth
                        height: parent.height
                        color: "transparent"
                        clip: true

                        Rectangle {
                            anchors.fill: parent
                            visible: table.actorCellColorFill
                                && characterRow.model.actorEntries.length === 1
                            color: visible
                                ? characterRow.model.actorEntries[0].color
                                : "transparent"
                            opacity: table.darkTheme ? 0.30 : 0.20
                            radius: table.macOSStyle ? 5 : 2
                        }

                        Column {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: (
                                collapseActorsButton.visible
                                    ? addActorButton.width
                                        + collapseActorsButton.width + 8
                                    : addActorButton.visible
                                        ? addActorButton.width + 8 : 6
                            )
                            anchors.topMargin: 4
                            anchors.bottomMargin: 4
                            spacing: 2
                            visible: !characterRow.actorCellIsCollapsed

                            Repeater {
                                model: characterRow.model.actorEntries

                                delegate: Item {
                                    width: parent.width
                                    height: 22

                                    Rectangle {
                                        anchors.fill: parent
                                        visible: table.actorCellColorFill
                                            && characterRow.hasMultipleActors
                                        color: modelData.color
                                        opacity: table.darkTheme ? 0.30 : 0.20
                                        radius: table.macOSStyle ? 5 : 2
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 2
                                        anchors.rightMargin: 2
                                        spacing: 4

                                        ActorColorSwatch {
                                            Layout.preferredWidth: 18
                                            Layout.preferredHeight: 18
                                            swatchColor: modelData.color
                                            visible: !table.actorCellColorFill
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: modelData.name
                                            elide: Text.ElideRight
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }
                            }
                        }

                        Label {
                            anchors.left: parent.left
                            anchors.right: collapseActorsButton.left
                            anchors.leftMargin: 6
                            anchors.rightMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            visible: characterRow.actorCellIsCollapsed
                            text: qsTr("Несколько актёров")
                            color: table.softMuted
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }

                        RowAccessoryButton {
                            id: addActorButton
                            anchors.right: parent.right
                            anchors.rightMargin: collapseActorsButton.visible
                                ? collapseActorsButton.width + 4 : 4
                            anchors.verticalCenter: parent.verticalCenter
                            iconSource: table.macOSStyle
                                ? Qt.resolvedUrl("../icons/plus.svg") : ""
                            overlayGlyph: table.macOSStyle ? "" : "+"
                            toolTipText: qsTr("Добавить актёра")
                            onClicked: {
                                table.pendingCharacter = model.character
                                table.pendingActorIds = model.actorIds
                                addActorMenu.popup()
                            }
                        }

                        RowAccessoryButton {
                            id: collapseActorsButton
                            anchors.right: parent.right
                            anchors.rightMargin: 2
                            anchors.verticalCenter: parent.verticalCenter
                            visible: characterRow.hasMultipleActors
                            iconSource: characterRow.actorCellIsCollapsed
                                ? Qt.resolvedUrl("../icons/chevron-right.svg")
                                : Qt.resolvedUrl("../icons/chevron-down.svg")
                            toolTipText: characterRow.actorCellIsCollapsed
                                ? qsTr("Развернуть актёров")
                                : qsTr("Свернуть актёров")
                            onClicked: table.toggleActorCell(model.character)
                        }

                        TapHandler {
                            enabled: !addActorButton.hovered
                                && !collapseActorsButton.hovered
                            onTapped: {
                                characterView.currentIndex = characterRow.index
                                characterView.forceActiveFocus()
                                if (table.castingBackend)
                                    table.castingBackend.selectCharacter(model.character)
                                table.pendingCharacter = model.character
                                actorMenu.popup()
                            }
                        }
                    }

                    Rectangle {
                        x: table.previewColumnX
                        width: table.previewColumnWidth
                        height: parent.height
                        color: "transparent"
                        clip: true

                        ToolButton {
                            id: replicaPreviewButton
                            anchors.fill: parent
                            text: qsTr("▶")
                            flat: table.macOSStyle
                            Accessible.name: qsTr("Реплики персонажа ") + model.character
                            leftPadding: 0; rightPadding: 0; topPadding: 0; bottomPadding: 0
                            onClicked: table.videoPreviewRequested(model.character)
                            PlatformToolTip {
                                target: replicaPreviewButton
                                text: qsTr("Реплики персонажа")
                            }
                        }
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: characterView.count === 0
                text: table.appBridge
                    && table.appBridge.project.currentEpisode.length > 0
                    ? "Для серии нет рабочего текста"
                    : "Откройте проект или выберите серию"
                color: table.softMuted
            }
        }
    }
}
