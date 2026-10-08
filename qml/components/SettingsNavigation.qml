pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: navigation

    property var sections: []
    property int currentIndex: 0
    property bool searchEnabled: false
    property string searchPlaceholder: qsTr("Найти настройку")
    property color softMuted: navPalette.placeholderText
    readonly property bool darkPalette: (
        navPalette.window.r + navPalette.window.g + navPalette.window.b
    ) < 1.5
    readonly property bool macOSStyle: Qt.platform.os === "osx"

    function filteredSections() {
        var query = searchField.text.trim().toLocaleLowerCase()
        if (!query.length)
            return sections
        var result = []
        var heading = null
        var headingAdded = false
        for (var index = 0; index < sections.length; ++index) {
            var item = sections[index]
            if (typeof item === "object" && item.heading) {
                heading = item
                headingAdded = false
                continue
            }
            var title = typeof item === "object"
                ? String(item.title || "") : String(item)
            var keywords = typeof item === "object"
                ? String(item.keywords || "") : ""
            var headingMatches = heading && String(
                heading.title || ""
            ).toLocaleLowerCase().indexOf(query) >= 0
            var matches = headingMatches
                || (title + " " + keywords).toLocaleLowerCase().indexOf(query) >= 0
            if (!matches)
                continue
            if (heading && !headingAdded) {
                result.push(heading)
                headingAdded = true
            }
            result.push(item)
        }
        return result
    }

    implicitWidth: macOSStyle ? 190 : 184

    SystemPalette {
        id: navPalette
        colorGroup: SystemPalette.Active
    }

    Rectangle {
        anchors.fill: parent
        color: navigation.macOSStyle
            ? "transparent"
            : Qt.rgba(
                navPalette.window.r,
                navPalette.window.g,
                navPalette.window.b,
                navigation.darkPalette ? 0.10 : 0.32
            )
    }

    Rectangle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        width: 1
        color: Qt.rgba(
            navPalette.text.r,
            navPalette.text.g,
            navPalette.text.b,
            navigation.macOSStyle ? 0.12 : 0.16
        )
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: navigation.macOSStyle ? 4 : 6
        anchors.rightMargin: navigation.macOSStyle ? 10 : 10
        anchors.topMargin: navigation.macOSStyle ? 4 : 6
        anchors.bottomMargin: navigation.macOSStyle ? 4 : 6
        spacing: navigation.macOSStyle ? 3 : 2

        TextField {
            id: searchField
            visible: navigation.searchEnabled
            Layout.fillWidth: true
            Layout.leftMargin: 2
            Layout.rightMargin: 2
            placeholderText: navigation.searchPlaceholder
            selectByMouse: true
        }

        PersistentListView {
            id: sectionList

            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: navigation.filteredSections()
            currentIndex: -1

            delegate: Item {
                id: sectionDelegate

                required property int index
                required property var modelData
                readonly property bool heading: Boolean(
                    typeof modelData === "object" && modelData.heading
                )
                readonly property int pageIndex: typeof modelData === "object"
                    ? Number(modelData.page ?? -1) : index
                readonly property string titleText: typeof modelData === "object"
                    ? String(modelData.title || "") : String(modelData)
                readonly property bool selected: !heading
                    && pageIndex === navigation.currentIndex

                width: sectionList.viewportWidth
                height: heading
                    ? (navigation.macOSStyle ? 28 : 30)
                    : (navigation.macOSStyle ? 30 : 36)

                Accessible.name: titleText
                Accessible.role: heading
                    ? Accessible.StaticText : Accessible.PageTab
                Accessible.selected: selected

                Rectangle {
                    anchors.fill: parent
                    visible: !sectionDelegate.heading
                    radius: navigation.macOSStyle ? 7 : 4
                    color: sectionDelegate.selected
                        ? Qt.rgba(
                            navPalette.highlight.r,
                            navPalette.highlight.g,
                            navPalette.highlight.b,
                            navigation.macOSStyle
                                ? (navigation.darkPalette ? 0.72 : 0.82)
                                : (navigation.darkPalette ? 0.42 : 0.20)
                        )
                        : sectionMouse.containsMouse
                            ? Qt.rgba(
                                navPalette.text.r,
                                navPalette.text.g,
                                navPalette.text.b,
                                0.07
                            )
                            : "transparent"
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: 20
                    radius: 2
                    visible: sectionDelegate.selected
                        && !navigation.macOSStyle
                    color: navPalette.highlight
                }

                Label {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: sectionDelegate.heading
                        ? (navigation.macOSStyle ? 8 : 10)
                        : (navigation.macOSStyle ? 18 : 20)
                    anchors.rightMargin: 8
                    text: sectionDelegate.titleText
                    elide: Text.ElideRight
                    font.weight: sectionDelegate.heading
                        || sectionDelegate.selected ? Font.DemiBold : Font.Normal
                    font.pixelSize: sectionDelegate.heading
                        ? Math.max(10, Application.font.pixelSize - 1)
                        : Application.font.pixelSize
                    font.capitalization: sectionDelegate.heading
                        ? Font.AllUppercase : Font.MixedCase
                    color: sectionDelegate.selected && navigation.macOSStyle
                        ? navPalette.highlightedText
                        : sectionDelegate.heading
                            ? navigation.softMuted : navPalette.text
                }

                MouseArea {
                    id: sectionMouse
                    anchors.fill: parent
                    enabled: !sectionDelegate.heading
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        navigation.currentIndex = sectionDelegate.pageIndex
                        sectionList.forceActiveFocus()
                    }
                }

            }
        }
    }
}
