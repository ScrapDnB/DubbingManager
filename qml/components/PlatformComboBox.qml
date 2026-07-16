import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    implicitHeight: Qt.platform.os === "windows" ? 30 : 26
    wheelEnabled: false
}
