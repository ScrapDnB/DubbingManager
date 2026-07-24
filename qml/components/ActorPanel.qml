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
    signal projectSummaryRequested()
    signal actorRolesRequested(string actorId)
    signal bulkTransferRequested()

    SplitView.preferredWidth: 330
    SplitView.minimumWidth: 180
    property string selectedActorId: ""
    property string selectedActorName: ""
    property color selectedActorColor: "#4F81BD"
    property string selectedActorGender: ""
    property color addActorColor: "#4F81BD"
    property bool globalMode: actorBaseMode.currentIndex === 1
    property color selectedRow: Qt.rgba(palette.highlight.r, palette.highlight.g, palette.highlight.b, 0.22)
    readonly property int tablePadding: 6
    readonly property int tableColumnSpacing: 6
    readonly property int colorColumnWidth: panel.globalMode ? 0 : 16
    readonly property int genderColumnWidth: 34
    readonly property int trailingColumnWidth: panel.globalMode ? 76 : 46
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
        40, Math.ceil(panelFontMetrics.height + 18)
    )
    readonly property int tableHeaderHeight: Math.max(
        28, Math.ceil(panelFontMetrics.height + 8)
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

    SystemPalette {
        id: palette
        colorGroup: SystemPalette.Active
    }

    FontMetrics {
        id: panelFontMetrics
        font: Application.font
    }

    Rectangle {
        anchors.fill: parent
        color: panel.panelSurface
        border.color: panel.softBorder
    }

    NativeDialogWindow {
        id: addActorDialog
        ownerWindow: panel.Window.window
        modal: true
        title: panel.globalMode
            ? qsTr("Добавить в глобальную базу")
            : qsTr("Добавить актёра в проект")
        standardButtons: Dialog.Ok | Dialog.Cancel
        width: 360
        height: panel.globalMode ? 190 : 250

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
                panel.actorLibraryBackend.addGlobalActorToProject(
                    actorSourceCombo.currentValue
                )
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

            Label {
                text: qsTr("Источник")
                color: panel.softMuted
                visible: !panel.globalMode
            }

            ComboBox {
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

                ComboBox {
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
                panel.selectedActorId = ""
                panel.selectedActorName = ""
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
            ComboBox {
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
        anchors.margins: 6
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: panel.controlHeight

            Label {
                text: qsTr("Актёры")
                font.bold: true
                Layout.fillWidth: true
            }

            ComboBox {
                id: actorBaseMode
                Layout.preferredWidth: 130
                Layout.minimumHeight: panel.controlHeight
                Layout.preferredHeight: panel.controlHeight
                Layout.maximumHeight: panel.controlHeight
                Layout.alignment: Qt.AlignVCenter
                model: ["Проект", "Глобальная"]
                onActivated: {
                    panel.selectedActorId = ""
                    panel.selectedActorName = ""
                    panel.selectedActorGender = ""
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: panel.tableHeaderHeight
            color: panel.softHeader
            border.color: panel.softBorder

            Item {
                anchors.fill: parent

                ToolButton {
                    x: panel.nameColumnX
                    width: panel.nameColumnWidth
                    height: parent.height
                    text: panel.sortTitle(qsTr("Имя"), "name")
                    font.bold: true
                    flat: true
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    onClicked: panel.setActorSort("name")
                    Accessible.name: qsTr("Сортировать актёров по имени")
                }
                ToolButton {
                    x: panel.genderColumnX
                    width: panel.genderColumnWidth
                    height: parent.height
                    text: panel.sortTitle(qsTr("Пол"), "gender")
                    font.bold: true
                    flat: true
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    onClicked: panel.setActorSort("gender")
                    Accessible.name: qsTr("Сортировать актёров по полу")
                }
                ToolButton {
                    x: panel.trailingColumnX
                    width: panel.trailingColumnWidth
                    height: parent.height
                    text: panel.sortTitle(
                        panel.globalMode ? qsTr("Статус") : qsTr("Роли"),
                        panel.globalMode ? "status" : "roleCount"
                    )
                    font.bold: true
                    flat: true
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
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

            delegate: Rectangle {
                id: actorRow
                width: actorsView.viewportWidth
                height: 32
                color: panel.selectedActorId === model.id ? panel.selectedRow : (actorHover.hovered ? panel.softHover : (index % 2 === 0 ? panel.softRow : panel.softAltRow))

                HoverHandler {
                    id: actorHover
                }

                TapHandler {
                    onTapped: {
                        panel.selectedActorId = model.id
                        panel.selectedActorName = model.name
                        panel.selectedActorColor = model.color
                        panel.selectedActorGender = model.gender
                    }
                    onDoubleTapped: if (!panel.globalMode) {
                        panel.actorRolesRequested(model.id)
                    }
                }

                Item {
                    anchors.fill: parent

                    Rectangle {
                        x: panel.tablePadding
                        anchors.verticalCenter: parent.verticalCenter
                        width: 16
                        height: 16
                        color: model.color
                        border.color: panel.softBorder
                        visible: !panel.globalMode
                    }

                    Label {
                        x: panel.nameColumnX
                        width: panel.nameColumnWidth
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
            AdaptiveButton {
                text: qsTr("Добавить")
                highlighted: true
                onClicked: addActorDialog.open()
                Layout.fillWidth: true
            }
            AdaptiveButton {
                text: qsTr("Удалить")
                palette.buttonText: "#b42318"
                enabled: panel.selectedActorId.length > 0
                onClicked: {
                    if (panel.globalMode) {
                        panel.actorLibraryBackend.deleteGlobalActor(
                            panel.selectedActorId
                        )
                    } else {
                        panel.castingBackend.deleteActor(panel.selectedActorId)
                    }
                    panel.selectedActorId = ""
                    panel.selectedActorName = ""
                }
                Layout.fillWidth: true
            }
            AdaptiveButton {
                text: panel.globalMode ? "В проект" : "В базу"
                enabled: panel.selectedActorId.length > 0
                onClicked: {
                    if (panel.globalMode) {
                        panel.actorLibraryBackend.addGlobalActorToProject(
                            panel.selectedActorId
                        )
                    } else {
                        panel.actorLibraryBackend.addProjectActorToGlobal(
                            panel.selectedActorId
                        )
                    }
                }
                Layout.fillWidth: true
            }
        }

        AdaptiveButton {
            text: panel.globalMode ? "Переименовать" : "Роли актёра"
            enabled: panel.selectedActorId.length > 0
            onClicked: {
                if (panel.globalMode) renameActorDialog.open()
                else panel.actorRolesRequested(panel.selectedActorId)
            }
            Layout.fillWidth: true
        }

        AdaptiveButton {
            text: qsTr("Объединить с...")
            visible: !panel.globalMode
            enabled: panel.selectedActorId.length > 0
            onClicked: mergeActorDialog.open()
            Layout.fillWidth: true
        }

        AdaptiveButton {
            text: qsTr("Несколько актёров в базу...")
            visible: !panel.globalMode
            onClicked: panel.bulkTransferRequested()
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            AdaptiveButton {
                text: qsTr("Цвет")
                visible: !panel.globalMode
                enabled: panel.selectedActorId.length > 0
                onClicked: actorColorDialog.open()
                Layout.fillWidth: true
            }

            ComboBox {
                id: selectedActorGenderCombo
                Layout.preferredWidth: 82
                enabled: panel.selectedActorId.length > 0
                model: ["", "М", "Ж"]
                currentIndex: Math.max(0, indexOfValue(panel.selectedActorGender))
                onActivated: {
                    panel.selectedActorGender = currentText
                    if (panel.appBridge && panel.selectedActorId.length > 0) {
                        if (panel.globalMode) {
                            panel.actorLibraryBackend.updateGlobalActor(
                                panel.selectedActorId,
                                panel.selectedActorName,
                                currentText
                            )
                        } else {
                            panel.castingBackend.updateActorGender(
                                panel.selectedActorId,
                                currentText
                            )
                        }
                    }
                }
            }
        }

        AdaptiveButton {
            text: qsTr("Отчёт по проекту")
            enabled: panel.appBridge !== null
            onClicked: panel.projectSummaryRequested()
            Layout.fillWidth: true
        }
    }
}
