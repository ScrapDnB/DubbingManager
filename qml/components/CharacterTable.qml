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
    property int actorColorMuteLevel: 2
    property bool actorCellFillFullHeight: false
    property int actorMarkerShape: 0
    property int actorMarkerSize: 0
    property var columnOrder: [
        "character", "lines", "rings", "words", "scope", "actor", "preview"
    ]
    property var hiddenColumns: []
    property var columnWidthModes: ({})
    property bool compactRows: false
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    readonly property bool actorCellColorFill:
        actorColorDisplayMode === "cell"
    readonly property bool darkTheme: (
        palette.base.r * 0.2126
        + palette.base.g * 0.7152
        + palette.base.b * 0.0722
    ) < 0.5
    property color selectedRow: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)

    function actorCellFillColor(actorColor) {
        if (actorColorMuteLevel <= 0)
            return actorColor
        var blend = actorColorMuteLevel === 1
            ? (darkTheme ? 0.60 : 0.55)
            : (darkTheme ? 0.30 : 0.20)
        return Qt.rgba(
            palette.base.r * (1 - blend) + actorColor.r * blend,
            palette.base.g * (1 - blend) + actorColor.g * blend,
            palette.base.b * (1 - blend) + actorColor.b * blend,
            1
        )
    }

    function actorCellNeedsLightText(fillColor) {
        function linearChannel(channel) {
            return channel <= 0.03928
                ? channel / 12.92
                : Math.pow((channel + 0.055) / 1.055, 2.4)
        }

        var luminance = 0.2126 * linearChannel(fillColor.r)
            + 0.7152 * linearChannel(fillColor.g)
            + 0.0722 * linearChannel(fillColor.b)
        return luminance < 0.22
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    // The table is custom because Qt Quick Controls does not provide a native
    // data grid. Keep its geometry tied to the active font instead of a
    // snapshot of one monitor's logical pixels.
    FontMetrics {
        id: tableFontMetrics
        font: Application.font
    }

    TextMetrics {
        id: linesHeaderMetrics
        text: qsTr("Строк") + " ↓"
        font.pixelSize: table.macOSStyle ? 11 : 13
        font.weight: table.macOSStyle ? Font.Medium : Font.DemiBold
    }
    TextMetrics {
        id: ringsHeaderMetrics
        text: qsTr("Реплик") + " ↓"
        font.pixelSize: table.macOSStyle ? 11 : 13
        font.weight: table.macOSStyle ? Font.Medium : Font.DemiBold
    }
    TextMetrics {
        id: wordsHeaderMetrics
        text: qsTr("Слов") + " ↓"
        font.pixelSize: table.macOSStyle ? 11 : 13
        font.weight: table.macOSStyle ? Font.Medium : Font.DemiBold
    }
    TextMetrics {
        id: scopeHeaderMetrics
        text: qsTr("Область")
        font.pixelSize: table.macOSStyle ? 11 : 13
        font.weight: table.macOSStyle ? Font.Medium : Font.DemiBold
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

    readonly property int columnGap: Math.max(
        6, Math.ceil(tableFontMetrics.height * 0.45)
    )
    readonly property int cellPadding: Math.max(
        12, Math.ceil(tableFontMetrics.height * 0.9)
    )
    function isColumnVisible(key) {
        return key === "character" || hiddenColumns.indexOf(key) < 0
    }

    function widthFactor(key) {
        var mode = Number(columnWidthModes[key] || 0)
        return mode < 0 ? 0.78 : mode > 0 ? 1.28 : 1
    }

    function orderedVisibleColumns() {
        var known = ["character", "lines", "rings", "words", "scope", "actor", "preview"]
        var ordered = []
        for (var i = 0; i < columnOrder.length; ++i) {
            var key = columnOrder[i]
            if (known.indexOf(key) >= 0 && ordered.indexOf(key) < 0 && isColumnVisible(key))
                ordered.push(key)
        }
        for (var j = 0; j < known.length; ++j)
            if (ordered.indexOf(known[j]) < 0 && isColumnVisible(known[j]))
                ordered.push(known[j])
        return ordered
    }

    readonly property var visibleColumns: orderedVisibleColumns()
    readonly property int visibleColumnCount: visibleColumns.length
    readonly property int baseLineColumnWidth: Math.max(48, Math.ceil(linesHeaderMetrics.width + cellPadding))
    readonly property int baseRingsColumnWidth: Math.max(50, Math.ceil(ringsHeaderMetrics.width + cellPadding))
    readonly property int baseWordsColumnWidth: Math.max(58, Math.ceil(wordsHeaderMetrics.width + cellPadding))
    readonly property int baseScopeColumnWidth: Math.max(66, Math.ceil(scopeHeaderMetrics.width + cellPadding + tableFontMetrics.height))
    readonly property int basePreviewColumnWidth: Math.max(26, tableFontMetrics.height + 12)
    readonly property int lineColumnWidth: isColumnVisible("lines")
        ? Math.round(baseLineColumnWidth * widthFactor("lines")) : 0
    readonly property int ringsColumnWidth: isColumnVisible("rings")
        ? Math.round(baseRingsColumnWidth * widthFactor("rings")) : 0
    readonly property int wordsColumnWidth: isColumnVisible("words")
        ? Math.round(baseWordsColumnWidth * widthFactor("words")) : 0
    readonly property int scopeColumnWidth: isColumnVisible("scope")
        ? Math.round(baseScopeColumnWidth * widthFactor("scope")) : 0
    readonly property int previewColumnWidth: isColumnVisible("preview")
        ? Math.round(basePreviewColumnWidth * widthFactor("preview")) : 0
    readonly property int rowVerticalPadding: compactRows
        ? 1 : Math.max(4, Math.ceil(tableFontMetrics.height * 0.3))
    readonly property int actorEntrySpacing: compactRows
        ? 0 : Math.max(2, Math.ceil(tableFontMetrics.height * 0.15))
    readonly property int actorEntryHeight: Math.max(
        compactRows ? (macOSStyle ? 18 : 20) : (macOSStyle ? 20 : 22),
        tableFontMetrics.height + (compactRows ? 3 : (macOSStyle ? 6 : 8))
    )
    readonly property int actorMarkerArea: actorMarkerSize === 2 ? 24 : 18
    readonly property int baseRowHeight: Math.max(
        compactRows ? (macOSStyle ? 20 : 23) : (macOSStyle ? 30 : 34),
        tableFontMetrics.height + (compactRows ? 4 : (macOSStyle ? 14 : 18))
    )
    readonly property int fixedColumnsWidth: lineColumnWidth + ringsColumnWidth
        + wordsColumnWidth + scopeColumnWidth + previewColumnWidth
    readonly property int flexibleWidth: Math.max(
        0, characterView.viewportWidth - columnGap * (visibleColumnCount + 1) - fixedColumnsWidth
    )
    // Actor cells contain names, colours and actions. They deliberately get
    // the larger share on narrow windows, rather than truncating first.
    readonly property real characterColumnShare: Math.min(
        0.48, Math.max(0.38, 0.38 + flexibleWidth / 7500)
    )
    readonly property real characterWeight: isColumnVisible("character")
        ? characterColumnShare * widthFactor("character") : 0
    readonly property real actorWeight: isColumnVisible("actor")
        ? (1 - characterColumnShare) * widthFactor("actor") : 0
    readonly property int characterColumnWidth: characterWeight + actorWeight > 0
        ? Math.floor(flexibleWidth * characterWeight / (characterWeight + actorWeight)) : 0
    readonly property int actorColumnWidth: characterWeight + actorWeight > 0
        ? Math.max(0, flexibleWidth - characterColumnWidth) : 0
    function columnWidth(key) {
        if (!isColumnVisible(key)) return 0
        if (key === "character") return characterColumnWidth
        if (key === "actor") return actorColumnWidth
        if (key === "lines") return lineColumnWidth
        if (key === "rings") return ringsColumnWidth
        if (key === "words") return wordsColumnWidth
        if (key === "scope") return scopeColumnWidth
        return previewColumnWidth
    }
    function columnX(key) {
        var x = columnGap
        for (var i = 0; i < visibleColumns.length; ++i) {
            var current = visibleColumns[i]
            if (current === key) return x
            x += columnWidth(current) + columnGap
        }
        return -10000
    }
    readonly property int characterColumnX: columnX("character")
    readonly property int lineColumnX: columnX("lines")
    readonly property int ringsColumnX: columnX("rings")
    readonly property int wordsColumnX: columnX("words")
    readonly property int scopeColumnX: columnX("scope")
    readonly property int actorColumnX: columnX("actor")
    readonly property int previewColumnX: columnX("preview")
    property string pendingCharacter: ""
    property var pendingActorIds: []
    property var pendingActorEntries: []
    property string pendingRemovalActorId: ""
    property string pendingRemovalActorName: ""
    property bool actorRemoveActionHovered: false
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

    function renameSelectedCharacter() {
        if (!castingBackend || !castingBackend.selectedCharacter)
            return
        renameCharacterSource = castingBackend.selectedCharacter
        renameCharacterDialog.open()
    }

    function previewSelectedCharacter() {
        if (castingBackend && castingBackend.selectedCharacter)
            videoPreviewRequested(castingBackend.selectedCharacter)
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
            text: table.pendingActorEntries.length > 1
                ? qsTr("Снять всех актёров") : qsTr("Снять актёра")
            enabled: table.pendingActorEntries.length > 0
            onTriggered: {
                if (table.castingBackend)
                    table.castingBackend.assignActor(table.pendingCharacter, "")
                actorMenu.close()
            }
        }

        MenuSeparator {}

        Repeater {
            model: table.castingBackend ? table.castingBackend.actorFilterModel : null

            MenuItem {
                required property string id
                required property string name

                visible: id.length > 0 && id !== "__unassigned__"
                height: visible ? implicitHeight : 0
                text: name
                onTriggered: {
                    const character = table.pendingCharacter
                    const actorId = id
                    actorMenu.close()
                    Qt.callLater(function() {
                        if (table.castingBackend)
                            table.castingBackend.assignActor(character, actorId)
                    })
                }
            }
        }
    }

    Menu {
        id: removeActorMenu

        MenuItem {
            enabled: false
            text: qsTr("Убрать актёра «%1»?").arg(
                table.pendingRemovalActorName
            )
        }

        MenuSeparator {}

        MenuItem {
            text: qsTr("Убрать")
            onTriggered: {
                if (table.castingBackend)
                    table.castingBackend.removeActorFromCharacter(
                        table.pendingCharacter, table.pendingRemovalActorId
                    )
            }
        }

        MenuItem {
            text: qsTr("Отмена")
        }
    }

    Menu {
        id: addActorMenu

        Repeater {
            model: table.castingBackend ? table.castingBackend.actorFilterModel : null

            MenuItem {
                required property string id
                required property string name

                visible: id.length > 0 && id !== "__unassigned__"
                    && table.pendingActorIds.indexOf(id) < 0
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
        title: qsTr("Карточка персонажа")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 430
        height: 270

        onOpened: {
            renameCharacterField.text = table.renameCharacterSource
            var aliases = table.castingBackend
                ? table.castingBackend.characterAliases(table.renameCharacterSource)
                : []
            characterAliasesField.text = aliases.join("\n")
            renameCharacterField.selectAll()
            renameCharacterField.forceActiveFocus()
        }
        onAccepted: if (table.castingBackend) {
            var aliases = characterAliasesField.text.split(/[\n,;]/).map(
                function(value) { return value.trim() }
            ).filter(function(value) { return value.length > 0 })
            table.castingBackend.updateCharacterProfile(
                table.renameCharacterSource,
                renameCharacterField.text,
                aliases
            )
        }

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
            Label {
                text: qsTr("Алиасы, прозвища и варианты имени")
                font.bold: true
            }
            TextArea {
                id: characterAliasesField
                Layout.fillWidth: true
                Layout.fillHeight: true
                placeholderText: qsTr("По одному на строке, например:\nСаша\nкапитан")
                selectByMouse: true
                wrapMode: TextEdit.Wrap
            }
            Label {
                text: qsTr("Алиасы используются в поиске, экспорте и будущей авторазметке.")
                color: table.softMuted
                wrapMode: Text.Wrap
                Layout.fillWidth: true
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

                TableHeaderButton { visible: table.isColumnVisible("character"); x: table.characterColumnX; width: table.characterColumnWidth; height: parent.height; text: table.sortTitle("Персонаж", "character"); onClicked: table.castingBackend.setCharacterSort("character"); Accessible.name: qsTr("Сортировать по персонажу") }
                TableHeaderButton { visible: table.isColumnVisible("lines"); x: table.lineColumnX; width: table.lineColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Строк", "lines"); onClicked: table.castingBackend.setCharacterSort("lines"); Accessible.name: qsTr("Сортировать по строкам") }
                TableHeaderButton { visible: table.isColumnVisible("rings"); x: table.ringsColumnX; width: table.ringsColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Реплик", "rings"); onClicked: table.castingBackend.setCharacterSort("rings"); Accessible.name: qsTr("Сортировать по репликам") }
                TableHeaderButton { visible: table.isColumnVisible("words"); x: table.wordsColumnX; width: table.wordsColumnWidth; height: parent.height; textAlignment: Text.AlignRight; text: table.sortTitle("Слов", "words"); onClicked: table.castingBackend.setCharacterSort("words"); Accessible.name: qsTr("Сортировать по словам") }
                TableHeaderButton { visible: table.isColumnVisible("scope"); x: table.scopeColumnX; width: table.scopeColumnWidth; height: parent.height; textAlignment: Text.AlignHCenter; text: table.sortTitle("Область", "scope"); onClicked: table.castingBackend.setCharacterSort("scope"); Accessible.name: qsTr("Сортировать по области назначения") }
                TableHeaderButton { visible: table.isColumnVisible("actor"); x: table.actorColumnX; width: table.actorColumnWidth; height: parent.height; text: table.sortTitle("Актёр", "actor"); onClicked: table.castingBackend.setCharacterSort("actor"); Accessible.name: qsTr("Сортировать по актёру") }
                TableHeaderButton {
                    id: allReplicasButton
                    x: table.previewColumnX
                    width: table.previewColumnWidth
                    height: parent.height
                    visible: table.isColumnVisible("preview")
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
                readonly property int profileRowHeight: model.aliasesText.length > 0
                    ? table.baseRowHeight + Math.max(10, tableFontMetrics.height - 3)
                    : table.baseRowHeight
                height: actorCellIsCollapsed
                    ? profileRowHeight
                    : Math.max(
                        profileRowHeight,
                        (model.actorEntries.length || 1) * table.actorEntryHeight
                            + (table.actorCellColorFill
                                && table.actorCellFillFullHeight
                                ? 0 : table.rowVerticalPadding * 2)
                            + Math.max(0, model.actorEntries.length - 1)
                                * (table.actorCellColorFill
                                    && table.actorCellFillFullHeight
                                    ? 0 : table.actorEntrySpacing)
                    )
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

                    Item {
                        visible: table.isColumnVisible("character")
                        x: table.characterColumnX
                        width: table.characterColumnWidth
                        height: parent.height
                        clip: true

                        Column {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1

                            Label {
                                width: parent.width
                                text: model.character
                                elide: Text.ElideRight
                            }
                            Label {
                                width: parent.width
                                visible: model.aliasesText.length > 0
                                text: model.aliasesText
                                color: table.softMuted
                                font.pixelSize: Math.max(10, Application.font.pixelSize - 2)
                                elide: Text.ElideRight
                            }
                        }

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
                    Label { visible: table.isColumnVisible("lines"); x: table.lineColumnX; width: table.lineColumnWidth; height: parent.height; text: model.lines; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { visible: table.isColumnVisible("rings"); x: table.ringsColumnX; width: table.ringsColumnWidth; height: parent.height; text: model.rings; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Label { visible: table.isColumnVisible("words"); x: table.wordsColumnX; width: table.wordsColumnWidth; height: parent.height; text: model.words; horizontalAlignment: Text.AlignRight; verticalAlignment: Text.AlignVCenter }
                    Rectangle {
                        visible: table.isColumnVisible("scope")
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
                        visible: table.isColumnVisible("actor")
                        x: table.actorColumnX
                        width: table.actorColumnWidth
                        height: parent.height
                        color: "transparent"
                        clip: true

                        Column {
                            anchors.fill: parent
                            anchors.leftMargin: 0
                            anchors.rightMargin: (
                                collapseActorsButton.visible
                                    ? addActorButton.width
                                        + collapseActorsButton.width + 8
                                    : addActorButton.visible
                                        ? addActorButton.width + table.columnGap
                                        : table.columnGap
                            )
                            anchors.topMargin: table.actorCellColorFill
                                && table.actorCellFillFullHeight ? 0 : table.rowVerticalPadding
                            anchors.bottomMargin: table.actorCellColorFill
                                && table.actorCellFillFullHeight ? 0 : table.rowVerticalPadding
                            spacing: table.actorCellColorFill
                                && table.actorCellFillFullHeight ? 0 : table.actorEntrySpacing
                            visible: !characterRow.actorCellIsCollapsed

                            Repeater {
                                model: characterRow.model.actorEntries

                                delegate: Item {
                                    id: actorEntry

                                    readonly property color actorBaseColor: modelData.color
                                    readonly property color actorDisplayFillColor:
                                        table.actorCellFillColor(actorBaseColor)

                                    width: parent.width
                                    height: table.actorCellColorFill
                                        && table.actorCellFillFullHeight
                                        && !characterRow.hasMultipleActors
                                        ? parent.height : table.actorEntryHeight

                                    Rectangle {
                                        anchors.fill: parent
                                        visible: table.actorCellColorFill
                                        color: actorEntry.actorDisplayFillColor
                                        radius: table.macOSStyle ? 5 : 2
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        anchors.rightMargin: 2
                                        spacing: 4

                                        ActorColorSwatch {
                                            Layout.preferredWidth: table.actorMarkerArea
                                            Layout.preferredHeight: table.actorMarkerArea
                                            swatchColor: actorEntry.actorBaseColor
                                            markerShape: table.actorMarkerShape
                                            markerSize: table.actorMarkerSize
                                            visible: !table.actorCellColorFill
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: modelData.name
                                            elide: Text.ElideRight
                                            verticalAlignment: Text.AlignVCenter
                                            color: table.actorCellColorFill
                                                && table.actorCellNeedsLightText(
                                                    actorEntry.actorDisplayFillColor
                                                )
                                                ? "white" : "#151515"
                                        }

                                        RowAccessoryButton {
                                            id: removeActorButton

                                            visible: characterRow.hasMultipleActors
                                            buttonSize: Math.min(
                                                table.actorEntryHeight,
                                                table.macOSStyle ? 18 : 20
                                            )
                                            Layout.preferredWidth: Math.min(
                                                table.actorEntryHeight,
                                                table.macOSStyle ? 18 : 20
                                            )
                                            Layout.preferredHeight: Layout.preferredWidth
                                            overlayGlyph: "−"
                                            overlayGlyphSize: table.macOSStyle ? 14 : 18
                                            toolTipText: ""
                                            Accessible.name: qsTr("Убрать %1 из роли").arg(
                                                modelData.name
                                            )
                                            onHoveredChanged: table.actorRemoveActionHovered = hovered
                                            onClicked: {
                                                table.pendingCharacter = characterRow.model.character
                                                table.pendingRemovalActorId = modelData.id
                                                table.pendingRemovalActorName = modelData.name
                                                removeActorMenu.popup(
                                                    removeActorButton,
                                                    removeActorButton.width, 0
                                                )
                                            }
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
                                table.pendingActorEntries = model.actorEntries
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
                                && !table.actorRemoveActionHovered
                            onTapped: {
                                characterView.currentIndex = characterRow.index
                                characterView.forceActiveFocus()
                                if (table.castingBackend)
                                    table.castingBackend.selectCharacter(model.character)
                                table.pendingCharacter = model.character
                                table.pendingActorIds = model.actorIds
                                table.pendingActorEntries = model.actorEntries
                                actorMenu.popup()
                            }
                        }
                    }

                    Rectangle {
                        visible: table.isColumnVisible("preview")
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
