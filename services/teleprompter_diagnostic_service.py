"""Long-running structured diagnostics for the teleprompter UI."""

from __future__ import annotations

import gzip
import json
import queue
import re
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any, Dict, Optional


CHUNK_SECONDS = 5 * 60
CHUNK_UNCOMPRESSED_BYTES = 10 * 1024 * 1024
FAST_SCROLL_MIN_DURATION_MS = 250
FAST_SCROLL_MIN_DISTANCE_SCREENS = 0.20
TELEPORT_MIN_DISTANCE_SCREENS = 0.25
REVERSE_SCROLL_MIN_DISTANCE_SCREENS = 0.05
MARKER_COALESCE_MS = 10_000


def _json_value(value: Any) -> Any:
    """Return a compact JSON-safe representation of a QML value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "-", str(value or "").strip(), flags=re.UNICODE)
    return cleaned.strip("-._")[:60] or "episode"


class TeleprompterDiagnosticService:
    """Write diagnostic events without blocking the Qt render thread."""

    def __init__(self) -> None:
        self._queue: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue(
            maxsize=50000
        )
        self._thread: Optional[threading.Thread] = None
        self._started_monotonic = 0.0
        self._started_at = ""
        self._session_dir: Optional[Path] = None
        self._recording = False
        self._sequence = 0
        self._anomaly_sequence = 0
        self._event_counts: Counter[str] = Counter()
        self._anomaly_counts: Counter[str] = Counter()
        self._dropped_events = 0
        self._writer_error = ""
        self._last_viewport_sample: Optional[Dict[str, Any]] = None
        self._last_allowed_jump_ms = -10000.0
        self._last_marker_signature: Optional[tuple[Any, ...]] = None
        self._last_marker_reaper_time = -1.0
        self._last_marker_t_ms = -10000.0
        self._last_marker_anomaly_id = ""
        self._last_marker_coalesced = False
        self._marker_counts: Counter[str] = Counter()

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def session_dir(self) -> Optional[Path]:
        return self._session_dir

    @property
    def elapsed_seconds(self) -> float:
        if not self._recording:
            return 0.0
        return max(0.0, monotonic() - self._started_monotonic)

    @property
    def writer_error(self) -> str:
        return self._writer_error

    @property
    def last_marker_coalesced(self) -> bool:
        return self._last_marker_coalesced

    @property
    def last_marker_anomaly_id(self) -> str:
        return self._last_marker_anomaly_id

    def start(
        self,
        root: Path,
        episode: str,
        manifest: Dict[str, Any],
    ) -> Path:
        if self._recording:
            assert self._session_dir is not None
            return self._session_dir

        started = datetime.now().astimezone()
        directory_name = (
            f"{started.strftime('%Y-%m-%d_%H-%M-%S')}"
            f"_episode-{_slug(episode)}"
        )
        session_dir = Path(root) / directory_name
        suffix = 2
        while session_dir.exists():
            session_dir = Path(root) / f"{directory_name}-{suffix}"
            suffix += 1
        (session_dir / "screenshots").mkdir(parents=True, exist_ok=False)

        self._queue = queue.Queue(maxsize=50000)
        self._started_monotonic = monotonic()
        self._started_at = started.isoformat(timespec="milliseconds")
        self._session_dir = session_dir
        self._recording = True
        self._sequence = 0
        self._anomaly_sequence = 0
        self._event_counts.clear()
        self._anomaly_counts.clear()
        self._dropped_events = 0
        self._writer_error = ""
        self._last_viewport_sample = None
        self._last_allowed_jump_ms = -10000.0
        self._last_marker_signature = None
        self._last_marker_reaper_time = -1.0
        self._last_marker_t_ms = -10000.0
        self._last_marker_anomaly_id = ""
        self._last_marker_coalesced = False
        self._marker_counts.clear()

        manifest_payload = {
            "schema": "dubbing-manager.teleprompter-diagnostics",
            "schema_version": 2,
            "started_at": self._started_at,
            "episode": str(episode),
            **_json_value(manifest),
        }
        self._write_json(session_dir / "manifest.json", manifest_payload)
        self._thread = threading.Thread(
            target=self._writer_main,
            name="teleprompter-diagnostics",
            daemon=True,
        )
        self._thread.start()
        self.record("session_started", {"episode": str(episode)})
        return session_dir

    def record(self, event: str, payload: Dict[str, Any]) -> str:
        """Queue an event and return a new anomaly id when one is detected."""
        if not self._recording:
            return ""
        self._sequence += 1
        event_name = str(event or "event")
        entry = {
            "seq": self._sequence,
            "t_ms": round(
                (monotonic() - self._started_monotonic) * 1000, 3
            ),
            "event": event_name,
            **_json_value(payload if isinstance(payload, dict) else {}),
        }
        self._event_counts[event_name] += 1
        self._enqueue(entry, low_priority=event_name == "viewport_sample")

        if event_name in {
            "instant_position",
            "local_navigation",
            "scroll_target_corrected",
            "page_scroll_finished",
            "continuous_scroll_finished",
            "episode_changed",
            "viewport_config_changed",
        }:
            self._last_allowed_jump_ms = self._number(entry.get("t_ms"), 0)

        anomaly = self._detect_anomaly(event_name, entry)
        if anomaly is None:
            return ""
        return self._record_anomaly(anomaly, entry)

    def mark_problem(self, payload: Optional[Dict[str, Any]] = None) -> str:
        if not self._recording:
            return ""
        context = _json_value(payload or {})
        now_ms = round((monotonic() - self._started_monotonic) * 1000, 3)
        reaper_time = self._number(context.get("reaper_time"), -1)
        signature = (
            str(context.get("episode") or ""),
            int(self._number(context.get("current_index"), -1)),
            str(context.get("comment") or ""),
        )
        same_marker = (
            signature == self._last_marker_signature
            and now_ms - self._last_marker_t_ms <= MARKER_COALESCE_MS
            and abs(reaper_time - self._last_marker_reaper_time) <= 0.02
            and bool(self._last_marker_anomaly_id)
        )
        if same_marker:
            self._last_marker_coalesced = True
            self._last_marker_t_ms = now_ms
            self._marker_counts[self._last_marker_anomaly_id] += 1
            self.record("operator_marker_repeated", {
                **context,
                "anomaly_id": self._last_marker_anomaly_id,
                "marker_count": self._marker_counts[self._last_marker_anomaly_id],
            })
            return ""

        self._last_marker_coalesced = False
        self.record("operator_marker", context)
        anomaly_id = self._record_anomaly(
            {
                "kind": "operator_marker",
                "reason": str(context.get("comment") or "Ручная метка оператора"),
            },
            context,
        )
        self._last_marker_signature = signature
        self._last_marker_reaper_time = reaper_time
        self._last_marker_t_ms = now_ms
        self._last_marker_anomaly_id = anomaly_id
        self._marker_counts[anomaly_id] = 1
        return anomaly_id

    def screenshot_path(self, label: str) -> str:
        if not self._recording or self._session_dir is None:
            return ""
        safe_label = _slug(label)
        elapsed_ms = int(
            max(0.0, monotonic() - self._started_monotonic) * 1000
        )
        return str(
            self._session_dir
            / "screenshots"
            / f"{elapsed_ms:010d}_{safe_label}.jpg"
        )

    def stop(self) -> Optional[Path]:
        if not self._recording:
            return self._session_dir
        session_dir = self._session_dir
        self.record("session_stopped", {})
        duration_ms = round(
            (monotonic() - self._started_monotonic) * 1000, 3
        )
        self._recording = False
        self._queue.put(None)
        thread = self._thread
        if thread is not None:
            thread.join(timeout=10.0)
            if thread.is_alive():
                self._writer_error = "Диагностический писатель не завершился вовремя"
        ended_at = datetime.now().astimezone().isoformat(timespec="milliseconds")
        if session_dir is not None:
            self._write_json(session_dir / "summary.json", {
                "schema_version": 2,
                "started_at": self._started_at,
                "ended_at": ended_at,
                "duration_ms": duration_ms,
                "event_count": sum(self._event_counts.values()),
                "event_counts": dict(sorted(self._event_counts.items())),
                "anomaly_count": sum(self._anomaly_counts.values()),
                "anomaly_counts": dict(sorted(self._anomaly_counts.items())),
                "operator_markers": dict(sorted(self._marker_counts.items())),
                "dropped_events": self._dropped_events,
                "writer_error": self._writer_error,
                "chunks": sorted(
                    path.name for path in session_dir.glob("events-*.jsonl.gz")
                ),
            })
        self._thread = None
        return session_dir

    def _detect_anomaly(
        self,
        event: str,
        entry: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if event in {"page_scroll_started", "continuous_scroll_started"}:
            duration = self._number(entry.get("actual_duration_ms"), -1)
            distance = abs(self._number(entry.get("distance_screens"), 0))
            signed_distance = self._number(
                entry.get("signed_distance_screens"),
                self._number(entry.get("distance_screens"), 0),
            )
            if (
                signed_distance <= -REVERSE_SCROLL_MIN_DISTANCE_SCREENS
                and not bool(entry.get("reverse_allowed"))
            ):
                return {
                    "kind": "reverse_auto_scroll",
                    "reason": (
                        f"Автоматическая прокрутка назад на {distance:.2f} экрана"
                    ),
                }
            if (
                0 <= duration < FAST_SCROLL_MIN_DURATION_MS
                and distance >= FAST_SCROLL_MIN_DISTANCE_SCREENS
            ):
                return {
                    "kind": "fast_scroll",
                    "reason": (
                        f"Переход {distance:.2f} экрана за {duration:.0f} мс"
                    ),
                }

            if bool(entry.get("deadline_expired")):
                return {
                    "kind": "expired_scroll_deadline",
                    "reason": "Прокрутка запущена с уже прошедшим дедлайном",
                }

        if event == "scroll_retargeted" and not bool(entry.get("allowed")):
            return {
                "kind": "unexpected_scroll_retarget",
                "reason": str(
                    entry.get("reason")
                    or "Цель незавершённой прокрутки была изменена"
                ),
            }

        if event == "prefetch_released" and bool(entry.get("unexpected")):
            return {
                "kind": "prefetch_interrupted",
                "reason": str(
                    entry.get("reason")
                    or "Prefetch был неожиданно прерван"
                ),
            }

        if event == "viewport_sample":
            previous = self._last_viewport_sample
            self._last_viewport_sample = entry
            if previous is None:
                return None
            viewport = max(1.0, self._number(entry.get("viewport_height"), 1))
            delta = abs(
                self._number(entry.get("content_y"), 0)
                - self._number(previous.get("content_y"), 0)
            )
            distance = delta / viewport
            allowed = any(bool(entry.get(key)) for key in (
                "animation_running",
                "manual_scroll",
                "local_navigation",
                "seek_in_progress",
                "model_refresh",
            ))
            allowed = allowed or (
                self._number(entry.get("t_ms"), 0)
                - self._last_allowed_jump_ms <= 300
            )
            origin_delta = abs(
                self._number(entry.get("origin_y"), 0)
                - self._number(previous.get("origin_y"), 0)
            )
            if distance >= TELEPORT_MIN_DISTANCE_SCREENS and not allowed:
                return {
                    "kind": "teleport",
                    "reason": (
                        f"Позиция изменилась на {distance:.2f} экрана без анимации"
                    ),
                    "origin_delta": round(origin_delta, 3),
                }

        if event == "scroll_target_corrected":
            viewport = max(1.0, self._number(entry.get("viewport_height"), 1))
            distance = abs(self._number(entry.get("delta_y"), 0)) / viewport
            if distance >= TELEPORT_MIN_DISTANCE_SCREENS:
                return {
                    "kind": "large_correction",
                    "reason": f"Коррекция конечной позиции на {distance:.2f} экрана",
                }

        if event == "viewport_invalid":
            return {
                "kind": "invalid_viewport",
                "reason": str(entry.get("reason") or "Некорректная область просмотра"),
            }
        return None

    def _record_anomaly(
        self,
        anomaly: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        self._anomaly_sequence += 1
        anomaly_id = f"a{self._anomaly_sequence:05d}"
        kind = str(anomaly.get("kind") or "anomaly")
        self._anomaly_counts[kind] += 1
        entry = {
            "seq": self._sequence,
            "t_ms": round(
                (monotonic() - self._started_monotonic) * 1000, 3
            ),
            "event": "anomaly",
            "anomaly_id": anomaly_id,
            **_json_value(anomaly),
            "context": _json_value(context),
        }
        self._event_counts["anomaly"] += 1
        self._enqueue(entry)
        return anomaly_id

    def _enqueue(self, entry: Dict[str, Any], low_priority: bool = False) -> None:
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            self._dropped_events += 1
            if not low_priority:
                try:
                    self._queue.put(entry, timeout=0.05)
                except queue.Full:
                    pass

    def _writer_main(self) -> None:
        assert self._session_dir is not None
        chunk_index = 0
        chunk_started_ms = -1.0
        chunk_bytes = 0
        stream = None
        anomaly_stream = None
        try:
            anomaly_stream = open(
                self._session_dir / "anomalies.jsonl",
                "a",
                encoding="utf-8",
            )
            while True:
                entry = self._queue.get()
                if entry is None:
                    break
                event_ms = self._number(entry.get("t_ms"), 0)
                line = json.dumps(
                    entry, ensure_ascii=False, separators=(",", ":")
                )
                if (
                    stream is None
                    or event_ms - chunk_started_ms >= CHUNK_SECONDS * 1000
                    or chunk_bytes >= CHUNK_UNCOMPRESSED_BYTES
                ):
                    if stream is not None:
                        stream.close()
                    chunk_index += 1
                    chunk_started_ms = event_ms
                    chunk_bytes = 0
                    stream = gzip.open(
                        self._session_dir
                        / f"events-{chunk_index:04d}.jsonl.gz",
                        "at",
                        encoding="utf-8",
                    )
                stream.write(line + "\n")
                chunk_bytes += len(line.encode("utf-8")) + 1
                if entry.get("event") == "anomaly":
                    anomaly_stream.write(line + "\n")
                    anomaly_stream.flush()
            if stream is not None:
                stream.close()
                stream = None
            anomaly_stream.close()
            anomaly_stream = None
        except Exception as exc:  # pragma: no cover - filesystem failures
            self._writer_error = str(exc)
        finally:
            if stream is not None:
                stream.close()
            if anomaly_stream is not None:
                anomaly_stream.close()

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
        temporary.replace(path)

    @staticmethod
    def _number(value: Any, fallback: float) -> float:
        try:
            number = float(value)
            return number if number == number else fallback
        except (TypeError, ValueError):
            return fallback
