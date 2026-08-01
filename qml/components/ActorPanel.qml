import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: panel

    required property var appBridge
    readonly property var castingBackend: appBridge ? appBridge.casting : null
    readonly property var actorLibraryBackend: appBridge
        ? appBridge.actorLibrary : null
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softHover
    required property color softMuted
    required property color panelSurface
    property int actorMarkerShape: 0
    property int actorMarkerSize: 0
    property bool compactRows: false
    signal projectSummaryRequested()
    signal actorRolesRequested(string actorId)
    signal bulkTransferRequested()
    signal globalBulkTransferRequested()

    SplitView.preferredWidth: 330
    SplitView.minimumWidth: 180
    property string selectedActorId: ""
    property var selectedActorIds: []
    property string selectedActorName: ""
    property color selectedActorColor: "#4F81BD"
    property string selectedActorGender: ""
    property color addActorColor: "#4F81BD"
    readonly property bool macOSStyle: Qt.platform.os === "osx"
    property bool globalMode: actorBaseMode.currentIndex === 1
    property color selectedRow: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)
    readonly property int tablePadding: Math.max(
        6, Math.ceil(panelFontMetrics.height * 0.45)
    )
    readonly property int tableColumnSpacing: tablePadding
    readonly property int colorColumnWidth: panel.globalMode ? 0 : Math.max(
        panel.actorMarkerSize === 2 ? 24 : 16,
        panelFontMetrics.height + 2
    )
    readonly property int genderColumnWidth: Math.max(
        42, Math.ceil(genderHeaderMetrics.width + tablePadding)
    )
    readonly property int trailingColumnWidth: Math.max(
        panel.globalMode ? 64 : 42,
        Math.ceil(
            (panel.globalMode ? statusHeaderMetrics.width : rolesHeaderMetrics.width)
                + tablePadding
        )
    )
    readonly property int tableContentWidth: Math.max(
        0, actorsView.viewportWidth
    )
    readonly property int nameColumnX: tablePadding + colorColumnWidth
        + (colorColumnWidth > 0 ? tableColumnSpacing : 0)
    readonly property int trailingColumnX: tableContentWidth - tablePadding
        - trailingColumnWidth
    readonly property int genderColumnX: trailingColumnX
        - tableColumnSpacing - genderColumnWidth
    readonly property int nameColumnWidth: Math.max(
        0, genderColumnX - tableColumnSpacing - nameColumnX
    )
    readonly property int controlHeight: Math.max(
        macOSStyle ? 28 : 40,
        Math.ceil(panelFontMetrics.height + (macOSStyle ? 8 : 18))
    )
    readonly property int tableHeaderHeight: Math.max(
        macOSStyle ? 24 : 28,
        Math.ceil(panelFontMetrics.height + (macOSStyle ? 4 : 8))
    )
    readonly property int actorRowHeight: Math.max(
        compactRows ? (macOSStyle ? 22 : 24) : (macOSStyle ? 28 : 32),
        panelFontMetrics.height + (compactRows
            ? (macOSStyle ? 6 : 8)
            : (macOSStyle ? 12 : 16))
    )

    function sortTitle(label, key) {
        var backend = panel.globalMode
            ? panel.actorLibraryBackend : panel.castingBackend
        if (!backend || backend.actorSortKey !== key)
            return label
        return label + (backend.actorSortAscending ? " ↑" : " ↓")
    }

    function setActorSort(key) {
        if (panel.globalMode)
            panel.actorLibraryBackend.setActorSort(key === "roleCount" ? "status" : key)
        else
            panel.castingBackend.setActorSort(key)
    }

    function selectActor(actorId, actorName, actorColor, actorGender) {
        panel.selectedActorId = actorId
        panel.selectedActorIds = actorId.length > 0 ? [actorId] : []
        panel.selectedActorName = actorName
        panel.selectedActorColor = actorColor
        panel.selectedActorGender = actorGender
    }

    function clearActorSelection() {
        panel.selectedActorId = ""
        panel.selectedActorIds = []
        panel.selectedActorName = ""
        panel.selectedActorGender = ""
    }

    function isActorSelected(actorId) {
        return panel.selectedActorIds.indexOf(actorId) >= 0
    }

    function toggleActorSelection(actorId, actorName, actorColor, actorGender, modifiers) {
        var isMultiSelect = (modifiers & Qt.ControlModifier)
            || (modifiers & Qt.MetaModifier)
        if (!isMultiSelect) {
            if (panel.selectedActorIds.length === 1
                    && panel.selectedActorId === actorId) {
                panel.clearActorSelection()
                return
            }
            panel.selectActor(actorId, actorName, actorColor, actorGender)
            return
        }

        var ids = panel.selectedActorIds.slice()
        var selectedIndex = ids.indexOf(actorId)
        if (selectedIndex >= 0) {
            ids.splice(selectedIndex, 1)
            panel.selectedActorIds = ids
            if (panel.selectedActorId === actorId) {
                if (ids.length === 0) {
                    panel.clearActorSelection()
                } else {
                    panel.selectedActorId = ids[ids.length - 1]
                }
            }
            return
        }
        ids.push(actorId)
        panel.selectedActorIds = ids
        panel.selectedActorId = actorId
        panel.selectedActorName = actorName
        panel.selectedActorColor = actorColor
        panel.selectedActorGender = actorGender
    }

    function requestProjectActorDeletion() {
        var assignments = panel.castingBackend.actorRoleAssignments(
            panel.selectedActorIds
        )
        if (assignments.length === 0) {
            panel.castingBackend.deleteActors(panel.selectedActorIds)
            panel.clearActorSelection()
            return
        }
        deleteProjectActorsDialog.actorIds = panel.selectedActorIds.slice()
        deleteProjectActorsDialog.roleAssignments = assignments
        deleteProjectActorsDialog.open()
    }

    function transferSelectedActor() {
        if (panel.selectedActorId.length === 0)
            return
        if (panel.globalMode) {
            panel.chooseGlobalActorColor(panel.selectedActorId)
        } else {
            panel.actorLibraryBackend.addProjectActorToGlobal(
                panel.selectedActorId
            )
        }
    }

    function chooseGlobalActorColor(actorId) {
        globalActorColorDialog.actorId = actorId
        globalActorColorDialog.currentColor = panel.addActorColor
        globalActorColorDialog.open()
    }

    function updateSelectedActorGender(gender) {
        if (panel.selectedActorId.length === 0)
            return
        panel.selectedActorGender = gender
        if (panel.globalMode) {
            panel.actorLibraryBackend.updateGlobalActor(
                panel.selectedActorId,
                panel.selectedActorName,
                gender
            )
        } else {
            panel.castingBackend.updateActorGender(
                panel.selectedActorId,
                gender
            )
        }
    }

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    FontMetrics {
        id: panelFontMetrics
        font: Application.font
    }

    TextMetrics {
        id: genderHeaderMetrics
        // Account for the sort arrow as well as the header text.
        text: qsTr("Пол ↑")
        font: panelFontMetrics.font
    }
    TextMetrics {
        id: rolesHeaderMetrics
        text: qsTr("Роли")
        font: panelFontMetrics.font
    }
    TextMetrics {
        id: statusHeaderMetrics
        text: qsTr("Статус")
        font: panelFontMetrics.font
    }

    Rectangle {
        anchors.fill: parent
        color: panel.macOSStyle
            ? Qt.rgba(
                palette.window.r,
                palette.window.g,
                palette.window.b,
                0.72
            )
            : panel.panelSurface
        border.color: panel.macOSStyle ? "transparent" : panel.softBorder

        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: 1
            visible: panel.macOSStyle
            color: panel.softBorder
        }
    }

    NativeDialogWindow {
        id: addActorDialog
        ownerWindow: panel.Window.window
        modal: true
        title: panel.globalMode
            ? qsTr("Добавить в глобальную базу")
            : qsTr("Добавить актёра в проект")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: boundedWidth(500, 36)
        height: panel.globalMode ? 280 : 330

        onOpened: {
            actorNameField.text = ""
            actorSourceCombo.currentIndex = 0
            addActorColor = "#4F81BD"
            addActorGenderCombo.currentIndex = 0
            actorNameField.forceActiveFocus()
        }
        onAccepted: {
            if (panel.globalMode) {
                panel.actorLibraryBackend.addGlobalActor(
                    actorNameField.text,
                    addActorGenderCombo.currentText
                )
            } else if (String(actorSourceCombo.currentValue || "").length > 0) {
                panel.chooseGlobalActorColor(actorSourceCombo.currentValue)
            } else {
                panel.castingBackend.addActorWithDetails(
                    actorNameField.text,
                    addActorColor.toString(),
                    addActorGenderCombo.currentText
                )
            }
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                visible: panel.globalMode

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: qsTr("Из проекта")
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Label {
                        text: qsTr("Можно выбрать сразу нескольких актёров")
                        color: panel.softMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                AdaptiveButton {
                    text: qsTr("Из проекта...")
                    Layout.minimumWidth: implicitWidth
                    onClicked: {
                        addActorDialog.close()
                        panel.bulkTransferRequested()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: panel.softBorder
                visible: panel.globalMode
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                visible: !panel.globalMode

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: qsTr("Из глобальной базы")
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Label {
                        text: qsTr("Можно выбрать сразу нескольких актёров")
                        color: panel.softMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                AdaptiveButton {
                    text: qsTr("Выбрать...")
                    Layout.minimumWidth: implicitWidth
                    onClicked: {
                        addActorDialog.close()
                        panel.globalBulkTransferRequested()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: panel.softBorder
                visible: !panel.globalMode
            }

            Label {
                text: qsTr("Создать нового актёра")
                color: panel.softMuted
                visible: panel.globalMode
            }

            Label {
                text: qsTr("Источник")
                color: panel.softMuted
                visible: !panel.globalMode
            }

            PlatformComboBox {
                id: actorSourceCombo
                visible: !panel.globalMode
                Layout.fillWidth: true
                model: panel.actorLibraryBackend
                    ? panel.actorLibraryBackend.globalActorChoicesModel : null
                textRole: "name"
                valueRole: "id"
            }

            TextField {
                id: actorNameField
                Layout.fillWidth: true
                placeholderText: qsTr("Имя актёра")
                selectByMouse: true
                visible: panel.globalMode
                    || String(actorSourceCombo.currentValue || "").length === 0
                onAccepted: addActorDialog.accept()
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: panel.globalMode
                    || String(actorSourceCombo.currentValue || "").length === 0

                AdaptiveButton {
                    text: qsTr("Цвет")
                    visible: !panel.globalMode
                    onClicked: addActorColorDialog.open()
                }

                Rectangle {
                    Layout.preferredWidth: 24
                    Layout.preferredHeight: 24
                    radius: 3
                    color: panel.addActorColor
                    border.color: panel.softBorder
                    visible: !panel.globalMode
                }

                Label { text: qsTr("Пол:") }

                PlatformComboBox {
                    id: addActorGenderCombo
                    Layout.preferredWidth: 80
                    model: ["", "М", "Ж"]
                }
            }
        }
    }

    NativeDialogWindow {
        id: mergeActorDialog
        ownerWindow: panel.Window.window
        modal: true
        title: qsTr("Объединить актёров")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 430
        height: 230

        onOpened: {
            panel.actorLibraryBackend.prepareMergeTargets(
                panel.selectedActorId
            )
            mergeTargetCombo.currentIndex = 0
        }
        onAccepted: {
            var target = panel.actorLibraryBackend.mergeTargetModel.get(
                mergeTargetCombo.currentIndex
            )
            if (panel.actorLibraryBackend.mergeProjectActor(
                panel.selectedActorId,
                target.targetKind || "",
                target.targetId || ""
            )) {
                panel.clearActorSelection()
            }
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 10

            Label {
                text: qsTr("Все роли и назначения «") + panel.selectedActorName
                    + "» перейдут к выбранному актёру."
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label { text: qsTr("Оставить актёра"); color: panel.softMuted }
            PlatformComboBox {
                id: mergeTargetCombo
                Layout.fillWidth: true
                model: panel.actorLibraryBackend
                    ? panel.actorLibraryBackend.mergeTargetModel : null
                textRole: "label"
            }
            Label {
                text: qsTr("Операцию можно отменить через Undo.")
                color: panel.softMuted
            }
        }
    }

    ActorColorDialog {
        id: addActorColorDialog
        ownerWindow: panel.Window.window
        appBridge: panel.appBridge
        currentColor: panel.addActorColor
        onColorAccepted: function(colorValue) {
            panel.addActorColor = colorValue
        }
    }

    ActorColorDialog {
        id: globalActorColorDialog
        ownerWindow: panel.Window.window
        appBridge: panel.appBridge
        property string actorId: ""
        currentColor: panel.addActorColor
        onColorAccepted: function(colorValue) {
            if (actorId.length > 0) {
                panel.actorLibraryBackend.addGlobalActorToProject(
                    actorId, colorValue.toString()
                )
            }
        }
    }

    NativeDialogWindow {
        id: renameActorDialog
        ownerWindow: panel.Window.window
        modal: true
        title: qsTr("Переименовать актёра")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 360
        height: 150

        onOpened: {
            renameActorField.text = panel.selectedActorName
            renameActorField.selectAll()
            renameActorField.forceActiveFocus()
        }
        onAccepted: {
            if (panel.globalMode) {
                panel.actorLibraryBackend.updateGlobalActor(
                    panel.selectedActorId,
                    renameActorField.text,
                    panel.selectedActorGender
                )
                panel.selectedActorName = renameActorField.text.trim()
            } else {
                panel.castingBackend.renameActor(
                    panel.selectedActorId,
                    renameActorField.text
                )
            }
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            TextField {
                id: renameActorField
                Layout.fillWidth: true
                placeholderText: qsTr("Имя актёра")
                selectByMouse: true
                onAccepted: renameActorDialog.accept()
            }
        }
    }

    NativeDialogWindow {
        id: deleteGlobalActorDialog
        ownerWindow: panel.Window.window
        modal: true
        title: qsTr("Удалить из глобальной базы?")
        standardButtons: Dialog.Yes | Dialog.Cancel
        width: 430
        height: 180
        property var actorIds: []
        property var actorNames: []

        onAccepted: {
            if (actorIds.length === 0)
                return
            panel.actorLibraryBackend.deleteGlobalActors(actorIds)
            panel.clearActorSelection()
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            Label {
                text: deleteGlobalActorDialog.actorNames.length === 1
                    ? qsTr("Удалить «") + deleteGlobalActorDialog.actorNames[0]
                        + qsTr("» из глобальной базы?")
                    : qsTr("Удалить выбранных актёров из глобальной базы: ")
                        + deleteGlobalActorDialog.actorNames.length + "?"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                text: qsTr("Актёры, уже добавленные в проекты, останутся без изменений.")
                wrapMode: Text.WordWrap
                color: panel.softMuted
                Layout.fillWidth: true
            }
        }
    }

    NativeDialogWindow {
        id: deleteProjectActorsDialog
        ownerWindow: panel.Window.window
        modal: true
        title: qsTr("Удалить актёров из проекта?")
        standardButtons: Dialog.Yes | Dialog.Cancel
        width: 500
        height: boundedHeight(430, 36)
        property var actorIds: []
        property var roleAssignments: []

        onAccepted: {
            if (actorIds.length === 0)
                return
            panel.castingBackend.deleteActors(actorIds)
            panel.clearActorSelection()
        }

        content: ColumnLayout {
            anchors.fill: parent
            spacing: 8

            Label {
                text: qsTr("Назначения этих актёров будут сняты:")
                Layout.fillWidth: true
            }

            PersistentListView {
                id: projectActorRolesView
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 96
                clip: true
                model: deleteProjectActorsDialog.roleAssignments
                delegate: Label {
                    width: projectActorRolesView.viewportWidth
                    text: modelData.actorName + ": " + modelData.rolesText
                    wrapMode: Text.WordWrap
                    padding: 4
                }
            }

            Label {
                text: qsTr("Операцию можно отменить через Undo.")
                color: panel.softMuted
                Layout.fillWidth: true
            }
        }
    }

    ActorColorDialog {
        id: actorColorDialog
        ownerWindow: panel.Window.window
        appBridge: panel.appBridge
        currentColor: panel.selectedActorColor
        onColorAccepted: function(colorValue) {
            panel.selectedActorColor = colorValue
            if (panel.appBridge && panel.selectedActorId.length > 0) {
                panel.castingBackend.updateActorColor(panel.selectedActorId, colorValue.toString())
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: panel.macOSStyle ? 8 : 6
        spacing: panel.macOSStyle ? 5 : 6

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: panel.controlHeight

            Label {
                text: qsTr("Актёры")
                font.bold: true
                Layout.fillWidth: true
            }

            PlatformComboBox {
                id: actorBaseMode
                Layout.preferredWidth: 130
                Layout.minimumHeight: panel.controlHeight
                Layout.preferredHeight: panel.controlHeight
                Layout.maximumHeight: panel.controlHeight
                Layout.alignment: Qt.AlignVCenter
                model: ["Проект", "Глобальная"]
                onActivated: panel.clearActorSelection()
            }
        }

        TableHeaderSurface {
            Layout.fillWidth: true
            Layout.preferredHeight: panel.tableHeaderHeight
            softHeader: panel.softHeader
            softBorder: panel.softBorder

            Item {
                anchors.fill: parent

                TableHeaderButton {
                    x: panel.nameColumnX
                    width: panel.nameColumnWidth
                    height: parent.height
                    text: panel.sortTitle(qsTr("Имя"), "name")
                    onClicked: panel.setActorSort("name")
                    Accessible.name: qsTr("Сортировать актёров по имени")
                }
                TableHeaderButton {
                    x: panel.genderColumnX
                    width: panel.genderColumnWidth
                    height: parent.height
                    text: panel.sortTitle(qsTr("Пол"), "gender")
                    textAlignment: Text.AlignHCenter
                    onClicked: panel.setActorSort("gender")
                    Accessible.name: qsTr("Сортировать актёров по полу")
                }
                TableHeaderButton {
                    x: panel.trailingColumnX
                    width: panel.trailingColumnWidth
                    height: parent.height
                    text: panel.sortTitle(
                        panel.globalMode ? qsTr("Статус") : qsTr("Роли"),
                        panel.globalMode ? "status" : "roleCount"
                    )
                    textAlignment: Text.AlignRight
                    onClicked: panel.setActorSort("roleCount")
                    Accessible.name: panel.globalMode
                        ? qsTr("Сортировать актёров по статусу")
                        : qsTr("Сортировать актёров по числу ролей")
                }
            }
        }

        PersistentListView {
            id: actorsView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: panel.castingBackend
                ? (panel.globalMode
                    ? panel.actorLibraryBackend.globalActorsModel
                    : panel.castingBackend.actorsModel)
                : null
            activeFocusOnTab: true
            Keys.onEscapePressed: panel.clearActorSelection()

            // A tap below the final row is an explicit way to leave selection mode.
            TapHandler {
                onTapped: function(eventPoint) {
                    var rowIndex = actorsView.indexAt(
                        eventPoint.position.x,
                        eventPoint.position.y + actorsView.contentY
                    )
                    if (rowIndex < 0)
                        panel.clearActorSelection()
                }
            }

            delegate: Rectangle {
                id: actorRow
                width: actorsView.viewportWidth
                height: panel.actorRowHeight
                color: panel.isActorSelected(model.id) ? panel.selectedRow : (actorHover.hovered ? panel.softHover : (index % 2 === 0 ? panel.softRow : panel.softAltRow))

                HoverHandler {
                    id: actorHover
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onClicked: function(mouse) {
                        panel.toggleActorSelection(
                            model.id, model.name, model.color, model.gender,
                            mouse.modifiers
                        )
                    }
                    onDoubleClicked: if (!panel.globalMode) {
                        panel.actorRolesRequested(model.id)
                    }
                }

                Item {
                    anchors.fill: parent

                    ActorColorSwatch {
                        x: panel.tablePadding
                        anchors.verticalCenter: parent.verticalCenter
                        width: panel.colorColumnWidth
                        height: 20
                        swatchColor: model.color
                        markerShape: panel.actorMarkerShape
                        markerSize: panel.actorMarkerSize
                        interactive: true
                        visible: !panel.globalMode

                        onClicked: {
                            panel.selectActor(
                                model.id, model.name,
                                model.color, model.gender
                            )
                            actorColorDialog.open()
                        }
                    }

                    Label {
                        x: panel.nameColumnX
                        width: Math.max(
                            0,
                            panel.nameColumnWidth
                                - (rowActions.visible ? rowActions.width + 4 : 0)
                        )
                        height: parent.height
                        text: model.name
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    Label {
                        x: panel.genderColumnX
                        width: panel.genderColumnWidth
                        height: parent.height
                        text: model.gender
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    Label {
                        x: panel.trailingColumnX
                        width: panel.trailingColumnWidth
                        height: parent.height
                        text: panel.globalMode ? model.status : model.roleCount
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    Row {
                        id: rowActions
                        x: panel.nameColumnX + panel.nameColumnWidth - width - 2
                        anchors.verticalCenter: parent.verticalCenter
                        height: moreActorButton.implicitHeight
                        spacing: 2
                        visible: true

                        RowAccessoryButton {
                            id: moreActorButton
                            iconSource: panel.macOSStyle
                                ? Qt.resolvedUrl("../icons/ellipsis.svg") : ""
                            overlayIconSource: panel.macOSStyle
                                ? "" : Qt.resolvedUrl("../icons/ellipsis.svg")
                            toolTipText: qsTr("Действия с актёром")
                            onClicked: {
                                panel.selectActor(
                                    model.id, model.name,
                                    model.color, model.gender
                                )
                                actorActionsMenu.popup()
                            }
                        }
                    }

                    Menu {
                        id: actorActionsMenu
                        // Fluent's automatic menu width is based on the
                        // compact trigger, not its longest action label.
                        width: 280

                        MenuItem {
                            text: panel.globalMode
                                ? qsTr("Добавить в проект")
                                : qsTr("Добавить в глобальную базу")
                            onTriggered: panel.transferSelectedActor()
                        }
                        MenuSeparator { }
                        MenuItem {
                            text: qsTr("Переименовать...")
                            visible: panel.globalMode
                            height: visible ? implicitHeight : 0
                            onTriggered: renameActorDialog.open()
                        }
                        MenuItem {
                            text: qsTr("Объединить с...")
                            visible: !panel.globalMode
                            height: visible ? implicitHeight : 0
                            onTriggered: mergeActorDialog.open()
                        }
                        MenuSeparator { }
                        MenuItem {
                            text: qsTr("Пол: не указан")
                            checkable: true
                            checked: panel.selectedActorGender.length === 0
                            autoExclusive: true
                            onTriggered: panel.updateSelectedActorGender("")
                        }
                        MenuItem {
                            text: qsTr("Пол: М")
                            checkable: true
                            checked: panel.selectedActorGender === "М"
                            autoExclusive: true
                            onTriggered: panel.updateSelectedActorGender("М")
                        }
                        MenuItem {
                            text: qsTr("Пол: Ж")
                            checkable: true
                            checked: panel.selectedActorGender === "Ж"
                            autoExclusive: true
                            onTriggered: panel.updateSelectedActorGender("Ж")
                        }
                    }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: actorsView.count === 0
                text: panel.globalMode
                    ? "Глобальная база пуста" : "Актёры не добавлены"
                color: panel.softMuted
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AdaptiveButton {
                text: qsTr("Добавить")
                highlighted: !panel.macOSStyle
                onClicked: addActorDialog.open()
                Layout.fillWidth: !panel.macOSStyle
            }
            AdaptiveButton {
                text: qsTr("Удалить")
                palette.buttonText: panel.macOSStyle
                    ? palette.text : "#b42318"
                enabled: panel.selectedActorIds.length > 0
                onClicked: {
                    if (panel.globalMode) {
                        var names = []
                        for (var i = 0; i < panel.selectedActorIds.length; i++) {
                            var actorId = panel.selectedActorIds[i]
                            for (var row = 0; row < actorsView.count; row++) {
                                var actor = actorsView.model.get(row)
                                if (actor.id === actorId) {
                                    names.push(actor.name)
                                    break
                                }
                            }
                        }
                        deleteGlobalActorDialog.actorIds = panel.selectedActorIds.slice()
                        deleteGlobalActorDialog.actorNames = names
                        deleteGlobalActorDialog.open()
                    } else {
                        panel.requestProjectActorDeletion()
                    }
                }
                Layout.fillWidth: !panel.macOSStyle
            }
            Item { Layout.fillWidth: true }
            AdaptiveButton {
                id: reportButton
                text: qsTr("Отчёт")
                enabled: panel.appBridge !== null
                onClicked: panel.projectSummaryRequested()
                PlatformToolTip {
                    target: reportButton
                    text: qsTr("Отчёт по проекту")
                }
            }
        }
    }
}
