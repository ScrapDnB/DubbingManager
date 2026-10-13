"""Isolated MIDI loopback and DAW settings visual check.

Run normally on macOS for real CoreMIDI loopback (no DAW or hardware needed).
--fluent previews the Windows controls/port selection; it is not a Windows run.
"""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FLUENT = "--fluent" in sys.argv
if FLUENT:
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "FluentWinUI3"

from PySide6.QtCore import QObject, Property, QSettings, QUrl, Signal, Slot, QCoreApplication, QEvent, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from shiboken6 import getCppPointer, wrapInstance

import services.global_settings_service as settings_module
from services.midi_sync_worker import MTC_PORT_NAME, MMC_PORT_NAME
from services.midi_timecode_service import mmc_locate
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge


app = QGuiApplication(sys.argv)
temporary = tempfile.TemporaryDirectory(prefix="dm-daw-smoke-")
scratch = Path(temporary.name)
settings_module.SETTINGS_FILE = scratch / "settings.json"
bridge = AppBridge(ui_state=UiStateBridge(QSettings(str(scratch / "ui.ini"), QSettings.IniFormat)))
bridge.theme.setMode("light")
prompter = bridge.teleprompter
failures = []
qml_errors = []


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError(f"Timeout: {prompter.syncStatus}")


def check(value, message):
    if not value:
        failures.append(message)
    print(("PASS " if value else "FAIL ") + message, flush=True)


def native_loopback():
    import rtmidi
    data = bridge._session.data
    data["episodes"] = {"1": str(scratch / "episode.ass")}
    data["episode_working_texts"] = {"1": {"characters": {"Герой": {}}, "lines": [
        {"id": "one", "start": 1., "end": 2., "character": "Герой", "text": "Первая реплика"},
        {"id": "two", "start": 3., "end": 4., "character": "Герой", "text": "Вторая реплика"},
    ]}}
    bridge.refresh()
    config = prompter.config
    config.update({"sync_daw": "nuendo", "osc_enabled": True, "sync_in": True,
                   "sync_out": True, "midi_timecode_origin_seconds": 3600.0,
                   "nuendo_offset_enabled": True, "nuendo_offset_seconds": -2.0})
    bridge._global_settings_service.set_default_prompter_config(config)
    sender = receiver = None
    try:
        assert prompter.prepare("1")
        wait_until(lambda: prompter._midi_ready)
        sender = rtmidi.MidiOut(name="DM Nuendo test sender")
        receiver = rtmidi.MidiIn(name="DM Nuendo test receiver")
        receiver.ignore_types(sysex=False, timing=False)
        sender.open_port(sender.get_ports().index(MTC_PORT_NAME))
        receiver.open_port(receiver.get_ports().index(MMC_PORT_NAME))
        sender.send_message([0xF0, 0x7F, 127, 1, 1, 33, 0, 3, 0, 0xF7])
        wait_until(lambda: prompter.time == 3.)
        check(prompter.currentIndex == 1, "CoreMIDI Full Frame follows exact cue with one-hour origin")
        prompter.jumpToIndex(1)
        packets = []
        def received():
            packet = receiver.get_message()
            if packet:
                packets.append(packet[0])
            return bool(packets)
        wait_until(received)
        check(packets[-1] == mmc_locate(3601.), "CoreMIDI MMC Locate includes project origin and -2s pre-roll")
        sender.send_message([0xF0, 0x7F, 127, 1, 1, 33, 0, 1, 0, 0xF7])
        wait_until(lambda: prompter._pending_reaper_time is None)
        check(prompter.time == 3., "MMC acknowledgement preserves selected cue")
        # A complete 25 fps forward MTC cycle: 01:00:03:00.
        for i, nibble in enumerate([0, 0, 3, 0, 0, 0, 1, 2]):
            sender.send_message([0xF1, i * 16 + nibble])
        wait_until(lambda: prompter.dawPlaying and abs(prompter.time - 3.08) < .00001)
        check(True, "CoreMIDI Quarter Frame includes two-frame correction")
        wait_until(lambda: not prompter.dawPlaying)
        check(prompter.syncConnectionState == "active", "stopped MTC keeps MIDI ready")
    finally:
        for endpoint in (sender, receiver):
            if endpoint:
                endpoint.close_port()
                endpoint.delete()
        prompter.close()
        app.processEvents()
    prompter.refreshMidiPorts()
    check(MMC_PORT_NAME not in prompter.midiPorts["inputs"]
          and MTC_PORT_NAME not in prompter.midiPorts["outputs"], "closing releases native virtual ports")


class WindowsMidiPreview(QObject):
    changed = Signal()
    @Property(bool, constant=True)
    def midiSupportsVirtual(self):
        return False
    @Property(bool, constant=True)
    def midiAvailable(self):
        return True
    @Property("QVariantMap", notify=changed)
    def midiPorts(self):
        return {"inputs": ["Nuendo to Dubbing Manager", "Dubbing Manager to Nuendo"],
                "outputs": ["Nuendo to Dubbing Manager", "Dubbing Manager to Nuendo"], "error": ""}
    @Slot()
    def refreshMidiPorts(self):
        self.changed.emit()


try:
    if sys.platform == "darwin" and not FLUENT:
        native_loopback()
    config = prompter.config
    config.update({"sync_daw": "nuendo", "osc_enabled": False})
    if FLUENT:
        config.update({"midi_input_port": "Nuendo to Dubbing Manager",
                       "midi_output_port": "Dubbing Manager to Nuendo"})
    bridge._global_settings_service.set_default_prompter_config(config)
    qml_dir = ROOT / "qml"
    if FLUENT:
        qml_dir = scratch / "qml"
        shutil.copytree(ROOT / "qml", qml_dir)
        for path in qml_dir.rglob("*.qml"):
            source = path.read_text().replace('Qt.platform.os === "osx"', 'false').replace('Qt.platform.os === "windows"', 'true')
            path.write_text(source)
    proxy = WindowsMidiPreview() if FLUENT else prompter
    def handler(kind, context, message):
        if any(word in message for word in ("ReferenceError", "TypeError", "Binding loop", "Cannot assign", "Unable to assign")):
            qml_errors.append(message)
        print(message, flush=True)
    qInstallMessageHandler(handler)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("syncBridge", bridge)
    engine.rootContext().setContextProperty("syncBackend", proxy)
    engine.loadData(f'''import QtQuick
import QtQuick.Controls
import "{(qml_dir / 'components').as_uri()}"
Window {{
    width: 840; height: 850; visible: true; color: "#f7f7f7"
    title: "Синхронизация с DAW"
    DawSyncSettingsPane {{
        id: pane; objectName: "dawPane"; anchors.fill: parent; anchors.margins: 24
        configuration: syncBridge.teleprompter.config
        teleprompter: syncBackend; softMuted: "#666666"
        onConfigEdited: function(config) {{
            syncBridge.settings.saveConfigAsDefault("prompter", config)
        }}
    }}
}}'''.encode(), QUrl.fromLocalFile(str(scratch / "preview.qml")))
    assert engine.rootObjects(), "DAW settings failed to load"
    window = wrapInstance(getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    output = ROOT / "output" / "daw-sync"
    output.mkdir(parents=True, exist_ok=True)
    prefix = "windows-preview" if FLUENT else "macos"
    wait_until(lambda: window.isVisible())
    time.sleep(.2)
    app.processEvents()
    pane = window.findChild(QObject, "dawPane")
    check(window.findChild(QObject, "syncDawSelector").property("currentIndex") == 1, "Nuendo selected in DAW settings")
    check(window.findChild(QObject, "midiRateSelector").property("currentIndex") == 1, "25 fps selected")
    window.grabWindow().save(str(output / (prefix + "-nuendo.png")))
    expression = QQmlExpression(engine.rootContext(), pane, "contentItem.contentY = contentHeight - height")
    expression.evaluate()
    app.processEvents()
    window.grabWindow().save(str(output / (prefix + "-instructions.png")))
    expression = QQmlExpression(engine.rootContext(), pane, 'setValue("sync_daw", "reaper")')
    expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    app.processEvents()
    check(window.findChild(QObject, "syncDawSelector").property("currentIndex") == 0, "switch back to Reaper updates controls")
    window.grabWindow().save(str(output / (prefix + "-reaper.png")))
    check(not qml_errors, "no QML runtime errors")
    window.close()
    engine.rootObjects()[0].deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
finally:
    prompter.close()

(ROOT / "output" / "daw-sync" / (prefix + "-checks.json")).write_text(json.dumps({"failures": failures, "qmlErrors": qml_errors}, ensure_ascii=False, indent=2))
sys.exit(1 if failures or qml_errors else 0)
