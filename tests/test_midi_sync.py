"""Protocol and device-lifecycle tests; no MIDI hardware required."""

from types import SimpleNamespace

import pytest

from services.midi_timecode_service import MtcDecoder, mmc_locate, timecode_seconds, timecode_origin_seconds
from services import midi_sync_worker as midi


def full_frame(hour=0, minute=0, second=0, frame=0, code=1):
    return [0xF0, 0x7F, 0x7F, 1, 1, hour | (code << 5), minute, second, frame, 0xF7]


def quarters(hour=0, minute=0, second=0, frame=0, code=1, reverse=False):
    values = [frame & 15, frame >> 4, second & 15, second >> 4,
              minute & 15, minute >> 4, hour & 15, (hour >> 4) | (code << 1)]
    messages = [[0xF1, (i << 4) | value] for i, value in enumerate(values)]
    return list(reversed(messages)) if reverse else messages


@pytest.mark.parametrize("rate,code,frames", [("24", 0, 24), ("25", 1, 25), ("30", 3, 30)])
def test_full_frame_and_mmc_known_position(rate, code, frames):
    sample = MtcDecoder(rate).feed(full_frame(1, 2, 3, frames // 2, code))
    assert sample.seconds == pytest.approx(3723 + (frames // 2) / frames)
    assert not sample.playing
    assert mmc_locate(sample.seconds, rate, 7) == [
        0xF0, 0x7F, 7, 6, 0x44, 6, 1, 1 | (code << 5), 2, 3, frames // 2, 0, 0xF7,
    ]


def test_mmc_subframe_negative_preroll_and_midnight():
    assert mmc_locate(10.02, "25")[9:12] == [10, 0, 50]
    assert mmc_locate(-2)[7:12] == [32, 0, 0, 0, 0]
    for seconds in (86400, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            mmc_locate(seconds)


@pytest.mark.parametrize("hour,minute,second,frame,real_frames", [
    (0, 0, 59, 29, 1799), (0, 1, 0, 2, 1800),
    (0, 10, 0, 0, 17982), (1, 0, 0, 0, 107892),
    (23, 59, 59, 29, 2589407),
])
def test_drop_frame_boundaries(hour, minute, second, frame, real_frames):
    seconds = real_frames * 1001 / 30000
    assert timecode_seconds(hour, minute, second, frame, "29.97df") == pytest.approx(seconds)
    assert mmc_locate(seconds, "29.97df")[7:12] == [64 | hour, minute, second, frame, 0]


def test_fractional_rates_use_project_rate_and_incoming_standard():
    assert MtcDecoder("23.976").feed(full_frame(second=1, code=0)).seconds == pytest.approx(1.001)
    assert MtcDecoder("29.97").feed(full_frame(second=1, code=3)).seconds == pytest.approx(1.001)
    # An incoming 25 fps message overrides an incompatible configured standard.
    assert MtcDecoder("24").feed(full_frame(second=1, frame=5, code=1)).seconds == pytest.approx(1.2)


@pytest.mark.parametrize("rate,expected", [
    ("25", 3600.0), ("23.976", 3603.6), ("29.97", 3603.6),
    ("29.97df", 3599.9964),
])
def test_one_hour_origin_has_no_fractional_rate_drift(rate, expected):
    origin = timecode_origin_seconds(3600, rate)
    assert origin == pytest.approx(expected)
    assert mmc_locate(origin, rate)[7:12] == [_hour_for_rate(rate), 0, 0, 0, 0]


def _hour_for_rate(rate):
    return {"25": 33, "23.976": 1, "29.97": 97, "29.97df": 65}[rate]


@pytest.mark.parametrize("reverse,expected", [(False, 10.08), (True, 9.92)])
def test_quarter_frame_lag_correction_and_order(reverse, expected):
    decoder = MtcDecoder()
    messages = quarters(second=10, reverse=reverse)
    for message in messages[:-1]:
        assert decoder.feed(message) is None
    sample = decoder.feed(messages[-1])
    assert sample.playing
    assert sample.seconds == pytest.approx(expected)
    next_message = quarters(second=10, frame=2, reverse=reverse)[0]
    assert decoder.feed(next_message).seconds == pytest.approx(expected + (-.01 if reverse else .01))


def test_incomplete_quarters_seek_and_relock():
    decoder = MtcDecoder()
    messages = quarters(second=10)
    for message in messages[:3] + messages[4:]:
        assert decoder.feed(message) is None
    assert decoder.feed(full_frame(second=3)).seconds == 3
    for message in messages[:-1]:
        assert decoder.feed(message) is None
    assert decoder.feed(messages[-1]).seconds == pytest.approx(10.08)
    decoder.reset_quarters()
    assert decoder.feed([0xF1, 0x10]) is None


@pytest.mark.parametrize("message", [
    [0x90, 60, 127], [0xF1], [0xF1, 128], [0xF1, 0x7F],
    full_frame(hour=24), full_frame(second=60), full_frame(frame=25),
    full_frame(minute=1, frame=0, code=2), full_frame()[:-1],
])
def test_unrelated_and_invalid_messages_never_move_cursor(message):
    assert MtcDecoder().feed(message) is None


def fake_backend(packets=(), inputs=("MTC cable",), outputs=("MMC cable",), fail_output=False):
    endpoints = []
    class Endpoint:
        def __init__(self, kind, **kwargs):
            self.kind = kind
            self.packets = list(packets)
            self.sent = []
            self.opened = None
            self.closed = self.deleted = False
            endpoints.append(self)
        def get_ports(self):
            return list(inputs if self.kind == "input" else outputs)
        def open_port(self, index):
            if fail_output and self.kind == "output":
                raise RuntimeError("port in use")
            self.opened = index
        def open_virtual_port(self, name):
            self.opened = name
        def ignore_types(self, **kwargs):
            self.filters = kwargs
        def get_message(self):
            return (self.packets.pop(0), 0) if self.packets else None
        def send_message(self, message):
            self.sent.append(message)
        def close_port(self):
            self.closed = True
        def delete(self):
            self.deleted = True
    return SimpleNamespace(MidiIn=lambda **kw: Endpoint("input", **kw),
                           MidiOut=lambda **kw: Endpoint("output", **kw)), endpoints


class OneIteration:
    stopped = False
    def is_set(self):
        return self.stopped
    def wait(self, timeout):
        self.stopped = True
    def set(self):
        self.stopped = True


def test_windows_existing_ports_receive_mtc_send_mmc_and_close(monkeypatch):
    backend, endpoints = fake_backend([full_frame(second=3), *quarters(second=3)])
    monkeypatch.setattr(midi, "rtmidi", backend)
    monkeypatch.setattr(midi, "MIDI_AVAILABLE", True)
    monkeypatch.setattr(midi, "sys", SimpleNamespace(platform="win32"))
    worker = midi.MidiSyncWorker("MTC cable", "MMC cable", "25", 127, True)
    worker._stop_event = OneIteration()
    positions, transport, errors = [], [], []
    worker.time_changed.connect(lambda source, value: positions.append(value))
    worker.transport_playing_changed.connect(lambda source, value: transport.append(value))
    worker.error_occurred.connect(lambda source, value: errors.append(value))
    worker.send_locate(15.02)
    worker.run()
    assert not errors
    assert positions == pytest.approx([3.0, 3.08])
    assert transport == [True]
    assert endpoints[0].filters == {"sysex": False, "timing": False, "active_sense": True}
    assert endpoints[1].sent == [mmc_locate(15.02)]
    assert all(endpoint.closed and endpoint.deleted for endpoint in endpoints)


def test_windows_virtual_ports_report_error_and_release_handles(monkeypatch):
    backend, endpoints = fake_backend()
    monkeypatch.setattr(midi, "rtmidi", backend)
    monkeypatch.setattr(midi, "MIDI_AVAILABLE", True)
    monkeypatch.setattr(midi, "sys", SimpleNamespace(platform="win32"))
    worker = midi.MidiSyncWorker(midi.VIRTUAL_PORT, midi.VIRTUAL_PORT, "25", 127, True)
    errors = []
    worker.error_occurred.connect(lambda source, value: errors.append(value))
    worker.run()
    assert "Windows" in errors[0]
    assert endpoints[0].closed and endpoints[0].deleted


def test_failed_output_releases_both_ports(monkeypatch):
    backend, endpoints = fake_backend(fail_output=True)
    monkeypatch.setattr(midi, "rtmidi", backend)
    monkeypatch.setattr(midi, "MIDI_AVAILABLE", True)
    worker = midi.MidiSyncWorker("MTC cable", "MMC cable", "25", 127, True)
    errors = []
    worker.error_occurred.connect(lambda source, value: errors.append(value))
    worker.run()
    assert errors == ["port in use"]
    assert all(endpoint.closed and endpoint.deleted for endpoint in endpoints)


def test_port_enumeration_retains_names_and_releases_clients(monkeypatch):
    backend, endpoints = fake_backend(inputs=("A", "B"), outputs=("C",))
    monkeypatch.setattr(midi, "rtmidi", backend)
    monkeypatch.setattr(midi, "MIDI_AVAILABLE", True)
    assert midi.midi_ports() == {"inputs": ["A", "B"], "outputs": ["C"], "error": ""}
    assert all(endpoint.deleted for endpoint in endpoints)


def test_mtc_silence_stops_playback_and_disconnected_port_reports_error(monkeypatch):
    backend, endpoints = fake_backend(quarters(second=3))
    monkeypatch.setattr(midi, "rtmidi", backend)
    monkeypatch.setattr(midi, "MIDI_AVAILABLE", True)
    now = [0.0]
    monkeypatch.setattr(midi, "monotonic", lambda: now[0])
    worker = midi.MidiSyncWorker("MTC cable", "MMC cable", "25", 127, False)
    class AdvancingEvent(OneIteration):
        def wait(self, timeout):
            now[0] += .4
            if now[0] > .7:
                endpoints[0].get_ports = lambda: []
    worker._stop_event = AdvancingEvent()
    transport, errors = [], []
    worker.transport_playing_changed.connect(lambda source, value: transport.append(value))
    worker.error_occurred.connect(lambda source, value: errors.append(value))
    worker.run()
    assert transport == [True, False]
    assert "отключён" in errors[0]
    assert len(endpoints) == 1  # output isn't opened when sync_out is disabled
    assert endpoints[0].closed and endpoints[0].deleted
