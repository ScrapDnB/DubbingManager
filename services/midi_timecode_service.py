"""MTC decoding and MMC Locate encoding, independent of Qt and MIDI devices.

MTC encodes 24, 25, 29.97 drop-frame or 30 fps. The project rate selects
23.976/29.97 non-drop variants, which cannot be distinguished on the wire.
Quarter-frame timestamps lag the sender by two frames (MIDI 1.0 specification).
"""

from dataclasses import dataclass
import math
from typing import Optional, Sequence


FRAME_RATES = ("24", "25", "29.97df", "30", "23.976", "29.97")
# wire code, nominal frames per second, actual frames per second
_RATES = {
    "24": (0, 24, 24.0), "25": (1, 25, 25.0),
    "29.97df": (2, 30, 30000 / 1001), "30": (3, 30, 30.0),
    "23.976": (0, 24, 24000 / 1001), "29.97": (3, 30, 30000 / 1001),
}


def _rate_for_code(code: int, project_rate: str) -> str:
    if _RATES[project_rate][0] == code:
        return project_rate
    return FRAME_RATES[code]


def timecode_seconds(hour: int, minute: int, second: int, frame: int,
                     rate: str) -> float:
    """Convert a SMPTE label to elapsed seconds, including drop-frame skips."""
    _, nominal, actual = _RATES[rate]
    if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60
            and 0 <= frame < nominal):
        raise ValueError("Invalid SMPTE timecode")
    total_minutes = hour * 60 + minute
    frames = ((hour * 3600 + minute * 60 + second) * nominal + frame)
    if rate == "29.97df":
        if minute % 10 and second == 0 and frame < 2:
            raise ValueError("Skipped drop-frame label")
        frames -= 2 * (total_minutes - total_minutes // 10)
    return frames / actual


def timecode_origin_seconds(label_seconds: float, rate: str) -> float:
    """Project origin is an HH:MM:SS label, not elapsed wall-clock seconds.

    At fractional rates 01:00:00 is not exactly 3600 elapsed seconds. For a
    skipped DF minute boundary use its first legal frame (02).
    """
    whole = int(label_seconds)
    hour, remainder = divmod(whole, 3600)
    minute, second = divmod(remainder, 60)
    frame = 2 if rate == "29.97df" and minute % 10 and second == 0 else 0
    return timecode_seconds(hour, minute, second, frame, rate)


def mmc_locate(seconds: float, rate: str = "25", device_id: int = 127) -> list[int]:
    """Encode a Universal Real-Time MMC Locate with hundredth-frame precision.

    Never wrap past midnight: a wrapped command could seek to a different cue.
    Negative pre-roll is clamped to the beginning of the session.
    """
    if rate not in _RATES or not 0 <= device_id <= 127:
        raise ValueError("Invalid MMC rate or device ID")
    if not math.isfinite(seconds):
        raise ValueError("Invalid MMC position")
    code, nominal, actual = _RATES[rate]
    frame_hundredths = int(math.floor(max(0.0, seconds) * actual * 100 + 0.5))
    frame_count, subframe = divmod(frame_hundredths, 100)
    if rate == "29.97df":
        # Each ten-minute block has 17982 frames; its first minute has 1800,
        # and the other nine minutes have 1798 frames each.
        blocks, remainder = divmod(frame_count, 17982)
        skipped = 18 * blocks + 2 * max(0, (remainder - 2) // 1798)
        frame_count += skipped
    whole_seconds, frame = divmod(frame_count, nominal)
    hour, remainder = divmod(whole_seconds, 3600)
    minute, second = divmod(remainder, 60)
    if hour >= 24:
        raise ValueError("MMC timecode exceeds 23:59:59")
    return [0xF0, 0x7F, device_id, 0x06, 0x44, 0x06, 0x01,
            (code << 5) | hour, minute, second, frame, subframe, 0xF7]


@dataclass(frozen=True)
class TimecodeSample:
    seconds: float
    playing: bool


class MtcDecoder:
    """Accept complete full frames and ordered forward/reverse quarter frames.

    Incomplete/out-of-order sequences are discarded rather than combining
    nibbles from different positions. Once locked, report every quarter frame.
    """

    def __init__(self, project_rate: str = "25") -> None:
        if project_rate not in FRAME_RATES:
            raise ValueError("Invalid project frame rate")
        self.project_rate = project_rate
        self.rate = project_rate
        self.reset_quarters()

    def reset_quarters(self) -> None:
        self._parts: list[int] = []
        self._last_index: Optional[int] = None
        self._direction = 0
        self._position: Optional[float] = None

    def feed(self, message: Sequence[int]) -> Optional[TimecodeSample]:
        if not message or any(not isinstance(b, int) or not 0 <= b <= 255
                              for b in message):
            return None
        if (len(message) == 10 and list(message[:2]) == [0xF0, 0x7F]
                and list(message[3:5]) == [0x01, 0x01]
                and message[-1] == 0xF7 and all(b < 128 for b in message[2:-1])):
            self.reset_quarters()
            return self._decode(*message[5:9], playing=False)
        if len(message) != 2 or message[0] != 0xF1 or message[1] >= 128:
            return None
        index, nibble = message[1] >> 4, message[1] & 15
        if index in {1, 3, 5, 7} and nibble > {1: 1, 3: 3, 5: 3, 7: 7}[index]:
            self.reset_quarters()
            return None
        if self._last_index is not None:
            if not self._direction:
                self._direction = 1 if self._last_index == 0 else -1
            if index != (self._last_index + self._direction) % 8:
                self.reset_quarters()
        if self._last_index is None:
            if index not in {0, 7}:
                return None
            self._parts = [0] * 8
            self._count = 0
        self._parts[index] = nibble
        self._last_index = index
        self._count += 1
        if self._count == 8:
            p = self._parts
            sample = self._decode(p[6] | (p[7] << 4), p[4] | (p[5] << 4),
                                  p[2] | (p[3] << 4), p[0] | (p[1] << 4),
                                  playing=True)
            self._count = 0
            if sample is None:
                self.reset_quarters()
                return None
            actual = _RATES[self.rate][2]
            day_frames = 2589408 if self.rate == "29.97df" else _RATES[self.rate][1] * 86400
            self._position = (sample.seconds + self._direction * 2 / actual) % (day_frames / actual)
        elif self._position is not None:
            self._position += self._direction / (4 * _RATES[self.rate][2])
        if self._position is not None:
            return TimecodeSample(max(0.0, self._position), True)
        return None

    def _decode(self, hour: int, minute: int, second: int, frame: int,
                *, playing: bool) -> Optional[TimecodeSample]:
        if hour & 0x80:
            return None
        rate = _rate_for_code((hour >> 5) & 3, self.project_rate)
        try:
            seconds = timecode_seconds(hour & 31, minute, second, frame, rate)
        except ValueError:
            return None
        self.rate = rate
        return TimecodeSample(seconds, playing)
