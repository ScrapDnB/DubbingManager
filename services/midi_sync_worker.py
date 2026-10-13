"""Nuendo MIDI sync. All native MIDI handles belong to one worker thread."""

from queue import Empty, Queue
from threading import Event
from time import monotonic
import logging
import sys

from PySide6.QtCore import QThread, Signal

from services.midi_timecode_service import MtcDecoder, mmc_locate

try:
    import rtmidi
except (ImportError, OSError):
    rtmidi = None

MIDI_AVAILABLE = rtmidi is not None
VIRTUAL_PORT = "__virtual__"
MTC_PORT_NAME = "Dubbing Manager MTC"
MMC_PORT_NAME = "Dubbing Manager MMC"
MTC_STOP_TIMEOUT = 0.3
logger = logging.getLogger(__name__)


def midi_ports() -> dict:
    """Enumerate ports without retaining native clients or opening endpoints."""
    result = {"inputs": [], "outputs": [], "error": ""}
    if not MIDI_AVAILABLE:
        result["error"] = "MIDI недоступен: установите python-rtmidi"
        return result
    endpoints = []
    try:
        for kind, factory in (("inputs", rtmidi.MidiIn), ("outputs", rtmidi.MidiOut)):
            endpoint = factory(name="Dubbing Manager ports")
            endpoints.append(endpoint)
            result[kind] = list(endpoint.get_ports())
    except Exception as exc:
        result["error"] = f"Ошибка MIDI: {exc}"
    finally:
        for endpoint in endpoints:
            endpoint.delete()
    return result


class MidiSyncWorker(QThread):
    time_changed = Signal(object, float)
    transport_playing_changed = Signal(object, bool)
    ready = Signal(object)
    error_occurred = Signal(object, str)

    def __init__(self, input_port: str, output_port: str, frame_rate: str,
                 device_id: int, send_enabled: bool, parent=None):
        super().__init__(parent)
        self.input_port = input_port
        self.output_port = output_port
        self.frame_rate = frame_rate
        self.device_id = device_id
        self.send_enabled = send_enabled
        self._stop_event = Event()
        self._commands: Queue = Queue()

    def send_locate(self, seconds: float) -> None:
        if not self.send_enabled:
            return
        # Validate synchronously so the bridge can display an out-of-range cue.
        self._commands.put(mmc_locate(seconds, self.frame_rate, self.device_id))

    @staticmethod
    def _open(endpoint, selected: str, virtual_name: str) -> None:
        if selected == VIRTUAL_PORT:
            if sys.platform == "win32":
                raise ValueError("На Windows выберите порт loopMIDI или MIDI-интерфейса")
            endpoint.open_virtual_port(virtual_name)
        else:
            ports = endpoint.get_ports()
            if not selected or selected not in ports:
                raise ValueError(f"MIDI-порт не найден: {selected or 'не выбран'}")
            if ports.count(selected) != 1:
                raise ValueError(f"Несколько MIDI-портов с одинаковым именем: {selected}")
            endpoint.open_port(ports.index(selected))

    def run(self) -> None:
        endpoints = []
        try:
            if not MIDI_AVAILABLE:
                raise RuntimeError("установите python-rtmidi")
            midiin = rtmidi.MidiIn(name="Dubbing Manager sync", queue_size_limit=4096)
            endpoints.append(midiin)
            midiin.ignore_types(sysex=False, timing=False, active_sense=True)
            self._open(midiin, self.input_port, MTC_PORT_NAME)
            midiout = None
            if self.send_enabled:
                midiout = rtmidi.MidiOut(name="Dubbing Manager sync")
                endpoints.append(midiout)
                self._open(midiout, self.output_port, MMC_PORT_NAME)
            decoder = MtcDecoder(self.frame_rate)
            playing = False
            last_quarter = None
            last_port_check = monotonic()
            self.ready.emit(self)
            while not self._stop_event.is_set():
                # Drain input before output, retaining message order and never
                # invoking Qt from a native MIDI callback.
                for _ in range(4096):
                    packet = midiin.get_message()
                    if packet is None:
                        break
                    message = packet[0]
                    sample = decoder.feed(message)
                    if sample is not None:
                        if decoder.rate != self.frame_rate:
                            raise ValueError(
                                f"Частота MTC {decoder.rate} fps не совпадает с настройкой "
                                f"{self.frame_rate} fps. Проверьте Project Setup в Nuendo."
                            )
                        if sample.playing:
                            last_quarter = monotonic()
                        else:
                            last_quarter = None
                        if playing != sample.playing:
                            playing = sample.playing
                            self.transport_playing_changed.emit(self, playing)
                        self.time_changed.emit(self, sample.seconds)
                    elif len(message) == 2 and message[0] == 0xF1:
                        # Keep the lock timer alive while assembling a cycle.
                        last_quarter = monotonic()
                if playing and last_quarter is not None and monotonic() - last_quarter > MTC_STOP_TIMEOUT:
                    playing = False
                    decoder.reset_quarters()
                    self.transport_playing_changed.emit(self, False)
                while not self._stop_event.is_set():
                    try:
                        command = self._commands.get_nowait()
                    except Empty:
                        break
                    if midiout is not None:
                        midiout.send_message(command)
                if monotonic() - last_port_check > 1:
                    last_port_check = monotonic()
                    for endpoint, selected in ((midiin, self.input_port), (midiout, self.output_port)):
                        if endpoint is not None and selected != VIRTUAL_PORT and selected not in endpoint.get_ports():
                            raise RuntimeError(f"MIDI-порт отключён: {selected}")
                self._stop_event.wait(0.005)
        except Exception as exc:
            self.error_occurred.emit(self, str(exc))
        finally:
            for endpoint in reversed(endpoints):
                try:
                    endpoint.close_port()
                except Exception:
                    logger.warning("Could not close MIDI endpoint", exc_info=True)
                try:
                    endpoint.delete()
                except Exception:
                    logger.warning("Could not release MIDI endpoint", exc_info=True)

    def stop(self) -> None:
        self._stop_event.set()
        self.wait()
