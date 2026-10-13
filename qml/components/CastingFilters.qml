pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: filters
    required property var appBridge
    property color softMuted
    signal globalSearchRequested()
    function focusSearch() {
        search.forceActiveFocus();
        search.selectAll();
    }
    spacing: 8
    RowLayout {
        Layout.fillWidth: true
        Label {
            text: qsTr("Персонажи")
            font.pixelSize: 19
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }
        Label {
            text: filters.appBridge.workspace.characterCount + qsTr(" персонажей · ") + filters.appBridge.workspace.unassignedCount + qsTr(" без актёра")
            color: filters.softMuted
            visible: filters.width > 570
        }
    }
    RowLayout {
        Layout.fillWidth: true
        TextField {
            id: search
            objectName: "castingSearch"
            Layout.fillWidth: true
            Layout.minimumWidth: 80
            placeholderText: qsTr("Поиск персонажа")
            Accessible.name: placeholderText
            text: filters.appBridge.casting.searchText
            onTextEdited: filters.appBridge.casting.setSearchText(text)
            selectByMouse: true
        }
        PlatformComboBox {
            id: actorFilter
            Layout.preferredWidth: filters.width < 550 ? 145 : 210
            model: filters.appBridge.casting.actorFilterModel
            textRole: "name"
            valueRole: "id"
            Accessible.name: qsTr("Фильтр по актёру")
            onActivated: filters.appBridge.casting.setActorFilter(currentValue)
            function sync() {
                var value = filters.appBridge.casting.showUnassignedOnly ? "__unassigned__" : filters.appBridge.casting.actorFilter;
                currentIndex = Math.max(0, indexOfValue(value));
            }
            onCountChanged: sync()
            Connections {
                target: filters.appBridge.casting
                function onActorFilterChanged() {
                    actorFilter.sync();
                }
                function onShowUnassignedOnlyChanged() {
                    actorFilter.sync();
                }
            }
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/search.svg")
            toolTipText: qsTr("Поиск по всему проекту")
            onClicked: filters.globalSearchRequested()
        }
        CompactToolButton {
            iconSource: Qt.resolvedUrl("../icons/x.svg")
            toolTipText: qsTr("Сбросить фильтры")
            enabled: filters.appBridge.casting.searchText.length > 0 || filters.appBridge.casting.actorFilter.length > 0 || filters.appBridge.casting.showUnassignedOnly
            onClicked: filters.appBridge.casting.resetFilters()
        }
    }
}
