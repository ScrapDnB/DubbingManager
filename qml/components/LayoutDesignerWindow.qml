pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

NativeDialogWindow {
    id: window

    required property var appBridge
    required property color softBorder
    required property color softHeader
    required property color softRow
    required property color softAltRow
    required property color softMuted
    readonly property var backend: appBridge.layoutTemplates
    property string pendingKind: ""
    property string pendingTemplateId: ""
    property bool pendingCreate: false
    property bool pendingClose: false
    property bool allowClose: false
    property string selectedLibraryId: backend.draftId
    property string noticeText: ""
    property bool noticeIsError: false
    property bool structureVisible: false
    property int canvasZoom: 100

    modal: false
    macOSDocumentWindow: true
    title: qsTr("Конструктор макетов")
    width: Math.min(1320, Screen.desktopAvailableWidth - 40)
    height: Math.min(820, Screen.desktopAvailableHeight - 60)
    minimumWidth: 940
    minimumHeight: 620

    function openFor(kind, sourceWindow) {
        if (sourceWindow)
            ownerWindow = sourceWindow
        backend.begin(kind === "teleprompter" ? "teleprompter" : "montage")
        selectedLibraryId = backend.draftId
        open()
        Qt.callLater(reloadPreview)
    }

    function reloadPreview() {
        if (designerCanvas)
            designerCanvas.reloadPreview()
    }

    function showNotice(message, isError) {
        noticeText = String(message || "")
        noticeIsError = Boolean(isError)
        noticeTimer.restart()
    }

    function requestKind(kind) {
        if (kind === backend.kind)
            return
        if (backend.draftDirty) {
            pendingKind = kind
            discardDialog.open()
            return
        }
        backend.begin(kind)
        selectedLibraryId = backend.draftId
    }

    function requestTemplate(templateId) {
        if (templateId === backend.draftId)
            return
        if (backend.draftDirty) {
            pendingTemplateId = templateId
            discardDialog.open()
            return
        }
        backend.loadTemplate(templateId)
    }

    function requestCreate() {
        if (backend.draftDirty) {
            pendingCreate = true
            discardDialog.open()
            return
        }
        backend.createTemplate(qsTr("Новый макет"))
    }

    function fieldLabel(field) {
        return field === "timecode" ? qsTr("Таймкод")
            : field === "character" ? qsTr("Персонаж")
            : field === "actor" ? qsTr("Актёр") : qsTr("Реплика")
    }

    onClosing: function(close) {
        if (backend.draftDirty && !allowClose) {
            close.accepted = false
            pendingClose = true
            discardDialog.open()
        }
        allowClose = false
    }

    Connections {
        target: window.backend
        function onDraftChanged() {
            window.selectedLibraryId = window.backend.draftId
        }
        function onErrorRequested(message) {
            window.showNotice(message, true)
        }
        function onStatusRequested(message) {
            window.showNotice(message, false)
        }
    }

    Timer {
        id: noticeTimer
        interval: 5000
        onTriggered: window.noticeText = ""
    }

    Shortcut {
        sequences: [StandardKey.Undo]
        enabled: window.visible && window.backend.canUndo
        onActivated: window.backend.undo()
    }
    Shortcut {
        sequences: [StandardKey.Redo]
        enabled: window.visible && window.backend.canRedo
        onActivated: window.backend.redo()
    }
    Shortcut {
        sequence: "Delete"
        enabled: window.visible && window.backend.selectedCanRemove
        onActivated: window.backend.removeSelectedNode()
    }

    Dialog {
        id: discardDialog
        width: Math.min(420, parent.width - 40)
        height: 170
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        modal: true
        title: qsTr("Отменить несохранённые изменения?")
        standardButtons: Dialog.Discard | Dialog.Cancel
        Label {
            width: discardDialog.availableWidth
            wrapMode: Text.WordWrap
            text: window.pendingClose
                ? qsTr("Несохранённый черновик будет потерян при закрытии конструктора.")
                : qsTr("При переходе в другую библиотеку текущий черновик будет потерян.")
        }
        onDiscarded: {
            if (window.pendingClose) {
                window.pendingClose = false
                window.allowClose = true
                window.close()
            } else if (window.pendingKind) {
                window.backend.begin(window.pendingKind)
            } else if (window.pendingTemplateId) {
                window.backend.loadTemplate(window.pendingTemplateId)
            } else if (window.pendingCreate) {
                window.backend.createTemplate(qsTr("Новый макет"))
            }
            window.selectedLibraryId = window.backend.draftId
            window.pendingKind = ""
            window.pendingTemplateId = ""
            window.pendingCreate = false
        }
        onRejected: {
            window.pendingKind = ""
            window.pendingTemplateId = ""
            window.pendingCreate = false
            window.pendingClose = false
        }
    }

    content: ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label {
                text: qsTr("Назначение:")
                color: window.softMuted
            }
            Button {
                text: qsTr("Монтажный лист")
                checkable: true
                autoExclusive: true
                checked: window.backend.kind === "montage"
                onClicked: window.requestKind("montage")
            }
            Button {
                text: qsTr("Телесуфлёр")
                checkable: true
                autoExclusive: true
                checked: window.backend.kind === "teleprompter"
                onClicked: window.requestKind("teleprompter")
            }
            Item { Layout.fillWidth: true }
            Label {
                text: window.noticeText || (!window.backend.draftPersisted
                    ? qsTr("Макет ещё не сохранён")
                    : window.backend.draftDirty
                        ? qsTr("Есть несохранённые изменения") : qsTr("Сохранено"))
                color: window.noticeText
                    ? window.noticeIsError ? "#C74737" : palette.highlight
                    : window.backend.draftDirty ? palette.highlight : window.softMuted
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Rectangle {
                SplitView.preferredWidth: window.structureVisible ? 320 : 300
                SplitView.minimumWidth: 270
                color: palette.base
                border.width: 1
                border.color: window.softBorder
                radius: 5

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    Label {
                        text: window.backend.kind === "montage"
                            ? qsTr("Макеты монтажных листов")
                            : qsTr("Макеты телесуфлёра")
                        font.bold: true
                    }

                    ListView {
                        id: libraryList
                        Layout.fillWidth: true
                        Layout.preferredHeight: 210
                        clip: true
                        model: window.backend.libraryModel
                        currentIndex: -1

                        delegate: Rectangle {
                            id: libraryRow
                            required property int index
                            required property string templateId
                            required property string name
                            required property bool builtIn
                            required property bool active
                            width: libraryList.width
                            height: 38
                            radius: 4
                            color: window.selectedLibraryId === templateId
                                ? palette.highlight : index % 2
                                    ? window.softAltRow : window.softRow

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                Label {
                                    text: libraryRow.name
                                    color: window.selectedLibraryId === libraryRow.templateId
                                        ? palette.highlightedText : palette.text
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                }
                                Label {
                                    text: libraryRow.active ? "✓"
                                        : libraryRow.builtIn ? qsTr("встроенный") : ""
                                    color: window.selectedLibraryId === libraryRow.templateId
                                        ? palette.highlightedText : window.softMuted
                                    font.pixelSize: libraryRow.active
                                        ? 16 : Math.max(9, Application.font.pixelSize - 2)
                                    Layout.maximumWidth: libraryRow.active ? 24 : 76
                                    elide: Text.ElideRight
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: window.requestTemplate(
                                    libraryRow.templateId
                                )
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 6
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("Создать")
                            onClicked: window.requestCreate()
                        }
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("Копия")
                            enabled: Boolean(window.backend.draftId)
                                && !window.backend.draftDirty
                            onClicked: window.backend.duplicateTemplate(
                                window.backend.draftId
                            )
                        }
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("Удалить")
                            enabled: !window.backend.draftBuiltIn
                                && !window.backend.draftDirty
                            onClicked: window.backend.deleteTemplate(
                                window.backend.draftId
                            )
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 1
                        color: window.softBorder
                    }

                    Label { text: qsTr("Элементы макета"); font.bold: true }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 6
                        Repeater {
                            model: window.backend.fieldKeys
                            AdaptiveButton {
                                id: fieldPaletteButton
                                required property string modelData
                                readonly property bool alreadyUsed:
                                    window.backend.usedFields.indexOf(modelData) >= 0
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                text: alreadyUsed
                                    ? "✓ " + window.fieldLabel(modelData)
                                    : "+ " + window.fieldLabel(modelData)
                                enabled: !window.backend.draftBuiltIn && !alreadyUsed
                                onClicked: window.backend.addNode("field", modelData)
                                HoverHandler { id: fieldPaletteHover }
                                PlatformToolTip {
                                    target: fieldPaletteButton
                                    active: fieldPaletteHover.hovered
                                    text: fieldPaletteButton.alreadyUsed
                                        ? qsTr("Поле уже находится в макете")
                                        : qsTr("Добавить в выбранную группу")
                                }
                            }
                        }
                    }

                    Label {
                        text: qsTr("Группировка")
                        color: window.softMuted
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 6
                        enabled: !window.backend.draftBuiltIn
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("+ Горизонтальная")
                            onClicked: window.backend.addNode("row", "")
                        }
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("+ Вертикальная")
                            onClicked: window.backend.addNode("column", "")
                        }
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("+ Линия")
                            onClicked: window.backend.addNode("separator", "")
                        }
                        AdaptiveButton {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 1
                            text: qsTr("+ Отступ")
                            onClicked: window.backend.addNode("spacer", "")
                        }
                    }

                    AdaptiveButton {
                        Layout.fillWidth: true
                        text: window.structureVisible
                            ? qsTr("Скрыть структуру") : qsTr("Показать структуру")
                        onClicked: window.structureVisible = !window.structureVisible
                    }

                    Label {
                        visible: window.structureVisible
                        text: qsTr("Расширенная структура")
                        font.bold: true
                    }
                    ListView {
                        id: treeList
                        visible: window.structureVisible
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: window.backend.treeModel

                        delegate: Rectangle {
                            id: treeRow
                            required property int index
                            required property string nodeId
                            required property int depth
                            required property string nodeType
                            required property string label
                            width: treeList.width
                            height: 34
                            radius: 3
                            Drag.active: nodeDrag.active
                            Drag.source: treeRow
                            Drag.hotSpot.x: width / 2
                            Drag.hotSpot.y: height / 2
                            Drag.keys: ["layout-tree-node"]
                            Drag.mimeData: ({ "text/plain": treeRow.nodeId })
                            color: window.backend.selectedNodeId === nodeId
                                ? palette.highlight : index % 2
                                    ? window.softAltRow : "transparent"
                            Label {
                                anchors.left: parent.left
                                anchors.leftMargin: 28 + treeRow.depth * 16
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: (treeRow.nodeType === "row" ? "▤ "
                                    : treeRow.nodeType === "column" ? "▥ "
                                    : "• ") + treeRow.label
                                color: window.backend.selectedNodeId === treeRow.nodeId
                                    ? palette.highlightedText : palette.text
                                elide: Text.ElideRight
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: window.backend.selectNode(treeRow.nodeId)
                            }
                            Label {
                                anchors.left: parent.left
                                anchors.leftMargin: 6 + treeRow.depth * 16
                                anchors.verticalCenter: parent.verticalCenter
                                text: "⠿"
                                color: window.backend.draftBuiltIn
                                    ? window.softMuted : palette.text
                                DragHandler {
                                    id: nodeDrag
                                    target: null
                                    enabled: !window.backend.draftBuiltIn
                                }
                            }
                            DropArea {
                                anchors.fill: parent
                                keys: ["layout-tree-node"]
                                onDropped: function(drop) {
                                    var sourceNodeId = drop.getDataAsString(
                                        "text/plain"
                                    )
                                    if (sourceNodeId) {
                                        window.backend.moveNodeBefore(
                                            sourceNodeId, treeRow.nodeId
                                        )
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        visible: window.structureVisible
                        enabled: !window.backend.draftBuiltIn
                        AdaptiveButton { text: "↑"; onClicked: window.backend.moveSelectedNode(-1) }
                        AdaptiveButton { text: "↓"; onClicked: window.backend.moveSelectedNode(1) }
                        AdaptiveButton { text: "−"; onClicked: window.backend.removeSelectedNode() }
                    }

                    Item {
                        visible: !window.structureVisible
                        Layout.fillHeight: true
                    }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 400
                color: palette.base
                border.width: 1
                border.color: window.softBorder
                radius: 5

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        AdaptiveButton {
                            text: qsTr("↶ Отменить")
                            enabled: window.backend.canUndo
                            onClicked: window.backend.undo()
                        }
                        AdaptiveButton {
                            text: qsTr("↷ Повторить")
                            enabled: window.backend.canRedo
                            onClicked: window.backend.redo()
                        }
                        Rectangle {
                            Layout.preferredWidth: 1
                            Layout.preferredHeight: 22
                            Layout.alignment: Qt.AlignVCenter
                            color: window.softBorder
                        }
                        Button {
                            text: qsTr("Пример")
                            checkable: true
                            autoExclusive: true
                            checked: !window.backend.previewUsesProjectData
                            onClicked: window.backend.setPreviewUsesProjectData(false)
                        }
                        Button {
                            text: qsTr("Из проекта")
                            checkable: true
                            autoExclusive: true
                            checked: window.backend.previewUsesProjectData
                            enabled: window.backend.previewProjectDataAvailable
                            onClicked: window.backend.setPreviewUsesProjectData(true)
                        }
                        Item { Layout.fillWidth: true }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label { text: qsTr("Масштаб") }
                        Slider {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 80
                            Layout.maximumWidth: 180
                            from: 60
                            to: 140
                            stepSize: 10
                            value: window.canvasZoom
                            onMoved: window.canvasZoom = Math.round(value)
                        }
                        Label { text: window.canvasZoom + "%" }
                    }

                    LayoutDesignerCanvas {
                        id: designerCanvas
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 260
                        backend: window.backend
                        softBorder: window.softBorder
                        softAltRow: window.softAltRow
                        zoomPercent: window.canvasZoom
                    }

                    Label {
                        Layout.fillWidth: true
                        text: window.backend.draftBuiltIn
                            ? qsTr("Выберите блок, чтобы посмотреть его свойства. Для редактирования создайте копию.")
                            : qsTr("Выбирайте блоки прямо на макете. Перетаскивайте их для перестановки, тяните разделители колонок для изменения ширины.")
                        color: window.softMuted
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                SplitView.preferredWidth: 280
                SplitView.minimumWidth: 230
                color: palette.base
                border.width: 1
                border.color: window.softBorder
                radius: 5

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    Label { text: qsTr("Свойства"); font.bold: true }

                    TextField {
                        Layout.fillWidth: true
                        placeholderText: qsTr("Название макета")
                        text: window.backend.draftName
                        readOnly: window.backend.draftBuiltIn
                        onEditingFinished: window.backend.setDraftName(text)
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: window.backend.draftBuiltIn
                        wrapMode: Text.WordWrap
                        color: window.softMuted
                        text: qsTr("Встроенный макет доступен только для просмотра. Нажмите «Копия», чтобы изменить его.")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 1
                        color: window.softBorder
                    }

                    Label {
                        text: {
                            var node = window.backend.selectedNode
                            if (!node || !node.type)
                                return qsTr("Элемент не выбран")
                            if (node.type === "field")
                                return window.fieldLabel(String(node.field))
                            return node.type === "row" ? qsTr("Горизонтальная группа")
                                : node.type === "column" ? qsTr("Вертикальная группа")
                                : node.type === "separator" ? qsTr("Линия-разделитель")
                                : qsTr("Отступ")
                        }
                        font.bold: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        enabled: !window.backend.draftBuiltIn

                        Label {
                            text: window.backend.selectedNode.type === "spacer"
                                ? qsTr("Размер отступа") : qsTr("Доля ширины")
                        }
                        SpinBox {
                            Layout.fillWidth: true
                            from: window.backend.selectedNode.type === "spacer" ? 2 : 1
                            to: window.backend.selectedNode.type === "spacer" ? 100 : 10
                            value: window.backend.selectedNode.type === "spacer"
                                ? Number(window.backend.selectedNode.size || 12)
                                : Number(window.backend.selectedNode.weight || 1)
                            onValueModified: window.backend.setSelectedNodeValue(
                                window.backend.selectedNode.type === "spacer"
                                    ? "size" : "weight", value
                            )
                        }

                        Label {
                            visible: ["row", "column"].indexOf(
                                String(window.backend.selectedNode.type)
                            ) >= 0
                            text: qsTr("Интервал")
                        }
                        SpinBox {
                            visible: ["row", "column"].indexOf(
                                String(window.backend.selectedNode.type)
                            ) >= 0
                            Layout.fillWidth: true
                            from: 0; to: 48
                            value: Number(window.backend.selectedNode.gap || 0)
                            onValueModified: window.backend.setSelectedNodeValue("gap", value)
                        }

                        Label {
                            visible: window.backend.selectedNode.type === "field"
                            text: qsTr("Размер текста")
                        }
                        SpinBox {
                            visible: window.backend.selectedNode.type === "field"
                            Layout.fillWidth: true
                            from: 8; to: 300
                            value: Number((window.backend.selectedNode.style || {}).font_size || 24)
                            onValueModified: window.backend.setSelectedNodeValue("font_size", value)
                        }

                        CheckBox {
                            visible: window.backend.selectedNode.type === "field"
                            text: qsTr("Жирный")
                            checked: Boolean((window.backend.selectedNode.style || {}).bold)
                            onClicked: window.backend.setSelectedNodeValue("bold", checked)
                        }
                        CheckBox {
                            visible: window.backend.selectedNode.type === "field"
                            text: qsTr("Курсив")
                            checked: Boolean((window.backend.selectedNode.style || {}).italic)
                            onClicked: window.backend.setSelectedNodeValue("italic", checked)
                        }
                    }

                    Label {
                        text: qsTr("Выравнивание")
                        visible: window.backend.selectedNode.type === "field"
                    }
                    PlatformComboBox {
                        Layout.fillWidth: true
                        visible: window.backend.selectedNode.type === "field"
                        enabled: !window.backend.draftBuiltIn
                        model: [qsTr("Слева"), qsTr("По центру"), qsTr("Справа")]
                        currentIndex: {
                            var alignment = String(
                                (window.backend.selectedNode.style || {}).alignment || "left"
                            )
                            return alignment === "center" ? 1 : alignment === "right" ? 2 : 0
                        }
                        onActivated: window.backend.setSelectedNodeValue(
                            "alignment", currentIndex === 1 ? "center"
                                : currentIndex === 2 ? "right" : "left"
                        )
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        enabled: !window.backend.draftBuiltIn
                        AdaptiveButton {
                            text: qsTr("Раньше")
                            enabled: window.backend.selectedCanMoveEarlier
                            onClicked: window.backend.moveSelectedNode(-1)
                        }
                        AdaptiveButton {
                            text: qsTr("Позже")
                            enabled: window.backend.selectedCanMoveLater
                            onClicked: window.backend.moveSelectedNode(1)
                        }
                        AdaptiveButton {
                            text: qsTr("Удалить")
                            enabled: window.backend.selectedCanRemove
                            onClicked: window.backend.removeSelectedNode()
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    footer: RowLayout {
        anchors.fill: parent
        spacing: 8
        AdaptiveButton {
            text: qsTr("Вернуть изменения")
            enabled: window.backend.draftModified
            onClicked: window.backend.revertDraft()
        }
        Item { Layout.fillWidth: true }
        AdaptiveButton {
            text: qsTr("Закрыть")
            onClicked: window.close()
        }
        AdaptiveButton {
            text: qsTr("Сохранить")
            enabled: !window.backend.draftBuiltIn && window.backend.draftDirty
            onClicked: window.backend.saveDraft()
        }
        AdaptiveButton {
            text: qsTr("Использовать макет")
            enabled: Boolean(window.backend.draftId)
            highlighted: true
            onClicked: window.backend.activateTemplate(window.backend.draftId)
        }
    }
}
