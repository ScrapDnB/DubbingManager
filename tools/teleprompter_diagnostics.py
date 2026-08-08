#!/usr/bin/env python3
"""Headless diagnostics for teleprompter timing, navigation, and scrolling."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Select the headless platform before importing Qt.  Users may override it
# when they intentionally want to watch the diagnostic window.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QMetaObject, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from ui.qml_backend.app_bridge import AppBridge  # noqa: E402
from ui.macos_integration import MacOSIntegration  # noqa: E402
from utils.helpers import ordered_episode_names  # noqa: E402


def parse_time(value: str) -> float:
    """Parse seconds or an HH:MM:SS-style timecode."""
    text = str(value or "").strip()
    if not text:
        raise argparse.ArgumentTypeError("empty timecode")
    try:
        parts = [float(part) for part in text.split(":")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid timecode: {value}") from exc
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    if not math.isfinite(seconds) or seconds < 0:
        raise argparse.ArgumentTypeError(f"invalid timecode: {value}")
    return seconds


def parse_viewport(value: str) -> tuple[int, int]:
    """Parse WIDTHxHEIGHT for a live resize diagnostic."""
    text = str(value or "").strip().lower().replace("×", "x")
    try:
        width, height = (int(part) for part in text.split("x", 1))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            f"invalid viewport {value!r}; expected WIDTHxHEIGHT"
        ) from exc
    if width < 760 or height < 520:
        raise argparse.ArgumentTypeError(
            "viewport must respect the teleprompter minimum 760x520"
        )
    return width, height


def emit(payload: dict[str, Any], json_lines: bool) -> None:
    """Write one stable diagnostic record to stdout."""
    if json_lines:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    kind = str(payload.get("type", "record")).upper()
    details = "  ".join(
        f"{key}={value}"
        for key, value in payload.items()
        if key != "type"
    )
    print(f"[{kind}] {details}")


def numeric_property(obj: QObject, name: str, default: float = 0.0) -> float:
    value = obj.property(name)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_property(obj: QObject, name: str, default: int = 0) -> int:
    return int(round(numeric_property(obj, name, default)))


def process_for(milliseconds: int) -> None:
    QTest.qWait(max(0, int(milliseconds)))
    QGuiApplication.processEvents()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the real teleprompter bridge and QML ListView against a .dub "
            "project, inject REAPER positions, and print scroll decisions."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("--episode", default="")
    parser.add_argument("--from", dest="start", type=parse_time, default=0.0)
    parser.add_argument("--to", dest="end", type=parse_time)
    parser.add_argument("--step", type=float, default=0.25)
    parser.add_argument("--tick-ms", type=int, default=10)
    parser.add_argument("--settle-ms", type=int, default=220)
    parser.add_argument("--width", type=int, default=1240)
    parser.add_argument("--height", type=int, default=820)
    parser.add_argument(
        "--resize", action="append", type=parse_viewport, default=[],
        help="Live-resize to WIDTHxHEIGHT before playback; may be repeated.",
    )
    parser.add_argument(
        "--font-size", action="append", type=float, default=[],
        help="Live-change replica font size before playback; may be repeated.",
    )
    parser.add_argument(
        "--smoothness", action="append", type=int, default=[],
        help="Live-change scroll smoothness (0..100) before playback.",
    )
    parser.add_argument(
        "--focus", action="append", type=float, default=[],
        help="Live-change focus ratio (0.1..0.9); may be repeated.",
    )
    parser.add_argument(
        "--layout", action="append",
        choices=("Сценарий 1", "Сценарий 2", "Сценарий 3"),
        default=[],
        help="Live-change the layout before playback; may be repeated.",
    )
    parser.add_argument(
        "--mode", choices=("page", "continuous"), default="page"
    )
    parser.add_argument(
        "--seek", action="append", type=parse_time, default=[],
        help="Additional isolated seek to validate; may be repeated.",
    )
    parser.add_argument(
        "--check-navigation", action="store_true",
        help="Validate local jump and next/previous navigation for every row.",
    )
    parser.add_argument(
        "--all-samples", action="store_true",
        help="Print every changed scroll target instead of concise transitions.",
    )
    parser.add_argument(
        "--stress-events", type=int, default=0,
        help="Run deterministic disruptive mid-session events after playback.",
    )
    parser.add_argument(
        "--seed", type=int, default=20260808,
        help="Random seed used by --stress-events.",
    )
    parser.add_argument("--json-lines", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project.expanduser().resolve()
    if not project.is_file():
        print(f"Project does not exist: {project}", file=sys.stderr)
        return 2
    if args.step <= 0:
        print("--step must be positive", file=sys.stderr)
        return 2
    if args.stress_events < 0:
        print("--stress-events must not be negative", file=sys.stderr)
        return 2

    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    bridge = AppBridge()

    # Load without ProjectBridge.open(): diagnostics must not modify the user's
    # recent-project list or write application settings.
    try:
        project_data = bridge._project_service.load_project(str(project))
    except Exception as exc:
        print(f"Could not load project: {exc}", file=sys.stderr)
        return 2
    if project_data is None:
        print(f"Could not load project: {project}", file=sys.stderr)
        return 2
    bridge._project_folder_service.prepare_project_paths(
        project_data, str(project)
    )
    bridge._script_text_service.link_existing_working_texts(
        project_data, str(project)
    )
    ordered_episodes = ordered_episode_names(project_data)
    bridge._session.replace_project(
        project_data,
        ordered_episodes[0] if ordered_episodes else "",
    )
    bridge.refresh()
    process_for(1)

    episodes = bridge._session.data.get("episodes", {})
    episode = str(args.episode or bridge._session.current_episode or "")
    if not episode and ordered_episodes:
        episode = str(ordered_episodes[0])
    if episode not in episodes:
        print(f"Episode not found: {episode}", file=sys.stderr)
        return 2

    # Override diagnostics in memory only.  Do not mutate the user's global
    # settings file or start a real OSC listener from this process.
    config = bridge._global_settings_service.get_default_prompter_config()
    config.update({
        "osc_enabled": False,
        "sync_in": True,
        "page_debug_overlay": True,
        "page_scroll_mode": args.mode == "page",
    })
    bridge._global_settings_service.set_default_prompter_config(config)
    bridge.teleprompter.configChanged.emit()

    engine = QQmlApplicationEngine()
    platform_integration = MacOSIntegration(app)
    engine.rootContext().setContextProperty(
        "platformIntegration", platform_integration
    )
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(ROOT / "qml" / "components" / "TeleprompterWindow.qml")),
    )
    window = component.createWithInitialProperties({
        "appBridge": bridge,
        "softBorder": "#555555",
        "softHeader": "#222222",
        "softRow": "#181818",
        "softAltRow": "#202020",
        "softMuted": "#999999",
        "ownerWindow": None,
    })
    if window is None:
        for error in component.errors():
            print(error.toString(), file=sys.stderr)
        return 2

    window.setProperty("width", args.width)
    window.setProperty("height", args.height)
    if not bridge.teleprompter.prepare(episode):
        print(f"Could not prepare episode: {episode}", file=sys.stderr)
        return 2
    bridge.teleprompter.debugSetSimulationActive(True)
    window.setProperty("visible", True)
    process_for(args.settle_ms)

    view = window.findChild(QObject, "teleprompterReplicaView")
    if view is None:
        print("Could not locate teleprompterReplicaView", file=sys.stderr)
        return 2

    rows = bridge.teleprompter.model.rows()
    if not rows:
        print(f"Episode {episode} has no teleprompter rows", file=sys.stderr)
        return 2

    end = args.end
    if end is None:
        end = float(rows[-1].get("end", rows[-1].get("start", args.start)))
    if end < args.start:
        print("--to must not precede --from", file=sys.stderr)
        return 2

    emit({
        "type": "config",
        "project": project.name,
        "episode": episode,
        "mode": args.mode,
        "rows": len(rows),
        "timed_rows": sum(bool(row.get("timingGuides")) for row in rows),
        "timing_guides": sum(
            len(row.get("timingGuides") or []) for row in rows
        ),
        "window": f"{args.width}x{args.height}",
        "viewport": (
            f"{numeric_property(view, 'width'):.1f}x"
            f"{numeric_property(view, 'height'):.1f}"
        ),
        "from": round(args.start, 3),
        "to": round(end, 3),
        "step": args.step,
        "gap_prefetch_seconds": config.get("page_gap_prefetch_seconds"),
        "gap_prefetch_delay_seconds": config.get(
            "page_gap_prefetch_delay_seconds"
        ),
        "highlight_fade_ms": config.get("page_target_highlight_fade_ms"),
    }, args.json_lines)

    failures: list[str] = []

    def record_reflow(cause: str) -> None:
        bridge.teleprompter.debugSetReaperTime(args.start)
        process_for(args.settle_ms)
        index = bridge.teleprompter.currentIndex
        qml_index = int_property(view, "currentIndex", -1)
        content_y = numeric_property(view, "contentY")
        origin_y = numeric_property(view, "originY")
        content_height = numeric_property(view, "contentHeight")
        viewport_height = numeric_property(view, "height")
        maximum_y = origin_y + max(0.0, content_height - viewport_height)
        geometry_ok = (
            math.isfinite(content_y)
            and origin_y - 2 <= content_y <= maximum_y + 2
        )
        if index != qml_index:
            failures.append(
                f"{cause}: backend index {index}, QML index {qml_index}"
            )
        if not geometry_ok:
            failures.append(
                f"{cause}: contentY {content_y:.1f} outside "
                f"{origin_y:.1f}..{maximum_y:.1f}"
            )
        emit({
            "type": "reflow",
            "cause": cause,
            "index": index,
            "qml_index": qml_index,
            "viewport": (
                f"{numeric_property(view, 'width'):.1f}x"
                f"{numeric_property(view, 'height'):.1f}"
            ),
            "rendered_height": round(
                numeric_property(view, "pageDebugRenderedHeight"), 1
            ),
            "pages": int_property(view, "pageDebugPageCount", 1),
            "timing_guides": len(rows[index].get("timingGuides") or [])
                if 0 <= index < len(rows) else 0,
            "timing_source": str(
                view.property("pageDebugTimingSource") or ""
            ),
            "threshold_time": round(
                numeric_property(view, "pageDebugThresholdTime", -1), 3
            ),
            "prefetch_index": int_property(
                view, "pageGapPrefetchIndex", -1
            ),
            "content_y": round(content_y, 1),
            "origin_y": round(origin_y, 1),
            "target_y": round(
                numeric_property(view, "pageDebugTargetY"), 1
            ),
            "ok": index == qml_index and geometry_ok,
        }, args.json_lines)

    for width, height in args.resize:
        window.setProperty("width", width)
        window.setProperty("height", height)
        process_for(args.settle_ms)
        record_reflow(f"resize:{width}x{height}")

    def update_config(**changes: Any) -> None:
        current_config = (
            bridge._global_settings_service.get_default_prompter_config()
        )
        if "f_text" in changes:
            layout = str(current_config.get("layout_type", "Сценарий 1"))
            profiles = deepcopy(current_config.get("layout_font_sizes", {}))
            profile = dict(profiles.get(layout, {}))
            profile["f_text"] = float(changes.pop("f_text"))
            profiles[layout] = profile
            current_config["layout_font_sizes"] = profiles
        current_config.update(changes)
        bridge._global_settings_service.set_default_prompter_config(
            current_config
        )
        bridge.teleprompter.configChanged.emit()
        process_for(args.settle_ms)

    for font_size in args.font_size:
        if not 8 <= font_size <= 200:
            print("--font-size must be between 8 and 200", file=sys.stderr)
            return 2
        update_config(f_text=font_size)
        record_reflow(f"font-size:{font_size:g}")

    for smoothness in args.smoothness:
        if not 0 <= smoothness <= 100:
            print("--smoothness must be between 0 and 100", file=sys.stderr)
            return 2
        update_config(scroll_smoothness_slider=smoothness)

    for focus in args.focus:
        if not 0.1 <= focus <= 0.9:
            print("--focus must be between 0.1 and 0.9", file=sys.stderr)
            return 2
        update_config(focus_ratio=focus)
        record_reflow(f"focus:{focus:g}")

    for layout in args.layout:
        update_config(layout_type=layout)
        record_reflow(f"layout:{layout}")

    previous_signature: tuple[Any, ...] | None = None
    previous_index = -1
    previous_page = -1
    previous_threshold = -1.0
    previous_timing_source = ""
    ass_page_turns = 0
    fallback_page_turns = 0
    prefetch_starts = 0
    previous_prefetch_index = -1
    sample_count = 0
    transition_count = 0
    long_replica_motion: dict[int, dict[str, list[float]]] = {}
    current = args.start
    while current <= end + 1e-9:
        bridge.teleprompter.debugSetReaperTime(current)
        process_for(args.tick_ms)
        sample_count += 1
        index = bridge.teleprompter.currentIndex
        qml_index = int_property(view, "currentIndex", -1)
        page = int_property(view, "pageDebugPage", 0)
        pages = int_property(view, "pageDebugPageCount", 1)
        content_y = numeric_property(view, "contentY")
        target_y = numeric_property(view, "pageDebugTargetY")
        event = str(view.property("pageDebugEvent") or "")
        timing_source = str(view.property("pageDebugTimingSource") or "")
        threshold_time = numeric_property(
            view, "pageDebugThresholdTime", -1
        )
        prefetch_index = int_property(view, "pageGapPrefetchIndex", -1)
        rendered_height = numeric_property(view, "pageDebugRenderedHeight")
        highlight_opacity = numeric_property(
            view, "pageTargetHighlightOpacity"
        )
        highlight_line_only = bool(
            view.property("pageTargetHighlightLineOnly")
        )
        highlight_height = numeric_property(
            view, "pageTargetHighlightHeight"
        )
        settled = False
        if (
            args.mode == "page"
            and rendered_height > numeric_property(view, "height")
            and (index != previous_index or page != previous_page)
        ):
            process_for(max(
                args.settle_ms,
                int(numeric_property(window, "scrollDurationMs")) + 30,
            ))
            settled = True
            qml_index = int_property(view, "currentIndex", -1)
            page = int_property(view, "pageDebugPage", 0)
            pages = int_property(view, "pageDebugPageCount", 1)
            content_y = numeric_property(view, "contentY")
            target_y = numeric_property(view, "pageDebugTargetY")
            event = str(view.property("pageDebugEvent") or "")
            timing_source = str(
                view.property("pageDebugTimingSource") or ""
            )
            threshold_time = numeric_property(
                view, "pageDebugThresholdTime", -1
            )
            prefetch_index = int_property(
                view, "pageGapPrefetchIndex", -1
            )
            rendered_height = numeric_property(
                view, "pageDebugRenderedHeight"
            )
            highlight_opacity = numeric_property(
                view, "pageTargetHighlightOpacity"
            )
            highlight_line_only = bool(
                view.property("pageTargetHighlightLineOnly")
            )
            highlight_height = numeric_property(
                view, "pageTargetHighlightHeight"
            )
        origin_y = numeric_property(view, "originY")
        content_height = numeric_property(view, "contentHeight")
        viewport_height = numeric_property(view, "height")
        signature = (
            index, page, pages, round(target_y, 1), event,
            timing_source, round(threshold_time, 3),
            prefetch_index,
        )

        if qml_index != index:
            failures.append(
                f"time {current:.3f}: backend index {index}, QML index {qml_index}"
            )
        if not all(math.isfinite(value) for value in (content_y, target_y)):
            failures.append(f"time {current:.3f}: non-finite scroll coordinate")
        maximum_y = origin_y + max(0.0, content_height - viewport_height)
        if content_y < origin_y - 2 or content_y > maximum_y + 2:
            failures.append(
                f"time {current:.3f}: contentY {content_y:.1f} outside "
                f"{origin_y:.1f}..{maximum_y:.1f}"
            )
        if (
            highlight_opacity > 0.001
            and highlight_line_only
            and (not math.isfinite(highlight_height) or highlight_height <= 0)
        ):
            failures.append(
                f"time {current:.3f}: invalid line highlight height "
                f"{highlight_height:.1f}"
            )
        if prefetch_index >= 0 and previous_prefetch_index < 0:
            prefetch_starts += 1
            row = rows[index] if 0 <= index < len(rows) else {}
            expected_earliest = float(row.get("end", current)) + float(
                config.get("page_gap_prefetch_delay_seconds", 0) or 0
            )
            if current + 0.001 < expected_earliest:
                failures.append(
                    f"time {current:.3f}: prefetch started before "
                    f"{expected_earliest:.3f}"
                )
        if index == previous_index and page < previous_page:
            failures.append(
                f"time {current:.3f}: page moved backwards {previous_page}->{page}"
            )
        if (
            args.mode == "page"
            and index == previous_index
            and page > previous_page
        ):
            if previous_threshold >= 0:
                if current + 0.001 < previous_threshold:
                    failures.append(
                        f"time {current:.3f}: page advanced before "
                        f"threshold {previous_threshold:.3f}"
                    )
                if current - previous_threshold > args.step + 0.001:
                    failures.append(
                        f"time {current:.3f}: page advanced late after "
                        f"threshold {previous_threshold:.3f}"
                    )
            if previous_timing_source.startswith("ASS:"):
                ass_page_turns += 1
            elif "визуаль" in previous_timing_source:
                fallback_page_turns += 1

        if index >= 0 and rendered_height > numeric_property(view, "height"):
            motion = long_replica_motion.setdefault(
                index, {"target": [], "content": []}
            )
            motion["target"].append(target_y)
            motion["content"].append(content_y)

        concise_signature = (
            index, page, pages, event, timing_source, prefetch_index
        )
        output_signature = signature if args.all_samples else concise_signature
        if output_signature != previous_signature:
            transition_count += 1
            row = rows[index] if 0 <= index < len(rows) else {}
            emit({
                "type": "transition",
                "time": round(current, 3),
                "timecode": bridge.teleprompter.timecode,
                "index": index,
                "row_start": round(float(row.get("start", 0.0)), 3),
                "row_end": round(float(row.get("end", 0.0)), 3),
                "page": page + 1,
                "pages": pages,
                "progress": round(
                    numeric_property(view, "pageDebugProgress") * 100, 2
                ),
                "rendered_height": round(
                    rendered_height, 1
                ),
                "timing_guides": len(row.get("timingGuides") or []),
                "timing_source": timing_source,
                "threshold_time": round(threshold_time, 3),
                "prefetch_index": prefetch_index,
                "content_y": round(content_y, 1),
                "target_y": round(target_y, 1),
                "highlight_scope": (
                    "none" if highlight_opacity <= 0.001
                    else "line" if highlight_line_only else "block"
                ),
                "highlight_height": round(highlight_height, 1),
                "highlight_opacity": round(highlight_opacity, 3),
                "settled": settled,
                "event": event,
            }, args.json_lines)
            previous_signature = output_signature
        previous_index = index
        previous_page = page
        previous_threshold = threshold_time
        previous_timing_source = timing_source
        previous_prefetch_index = prefetch_index
        current += args.step

    for seconds in args.seek:
        bridge.teleprompter.debugSetReaperTime(seconds)
        process_for(args.settle_ms)
        index = bridge.teleprompter.currentIndex
        qml_index = int_property(view, "currentIndex", -1)
        row = rows[index] if 0 <= index < len(rows) else {}
        ok = qml_index == index
        if not ok:
            failures.append(
                f"seek {seconds:.3f}: backend index {index}, QML index {qml_index}"
            )
        emit({
            "type": "seek",
            "time": round(seconds, 3),
            "index": index,
            "qml_index": qml_index,
            "row_start": round(float(row.get("start", 0.0)), 3),
            "page": int_property(view, "pageDebugPage", 0) + 1,
            "pages": int_property(view, "pageDebugPageCount", 1),
            "rendered_height": round(
                numeric_property(view, "pageDebugRenderedHeight"), 1
            ),
            "timing_guides": len(row.get("timingGuides") or []),
            "timing_source": str(
                view.property("pageDebugTimingSource") or ""
            ),
            "threshold_time": round(
                numeric_property(view, "pageDebugThresholdTime", -1), 3
            ),
            "prefetch_index": int_property(
                view, "pageGapPrefetchIndex", -1
            ),
            "content_y": round(numeric_property(view, "contentY"), 1),
            "target_y": round(numeric_property(view, "pageDebugTargetY"), 1),
            "event": str(view.property("pageDebugEvent") or ""),
            "ok": ok,
        }, args.json_lines)

    if args.check_navigation:
        active = [i for i, row in enumerate(rows) if row.get("active")]
        for position, index in enumerate(active):
            bridge.teleprompter.jumpToIndex(index)
            process_for(args.settle_ms)
            actual = bridge.teleprompter.currentIndex
            qml_index = int_property(view, "currentIndex", -1)
            ok = actual == index and qml_index == index
            if not ok:
                failures.append(
                    f"jump row {index}: backend {actual}, QML {qml_index}"
                )
            next_ok = True
            expected_next = index
            if len(active) > 1:
                expected_next = active[(position + 1) % len(active)]
                bridge.teleprompter.navigate(1)
                process_for(args.settle_ms)
                actual_next = bridge.teleprompter.currentIndex
                qml_next = int_property(view, "currentIndex", -1)
                next_ok = (
                    actual_next == expected_next and qml_next == expected_next
                )
                if not next_ok:
                    failures.append(
                        f"next from {index}: expected {expected_next}, "
                        f"backend {actual_next}, QML {qml_next}"
                    )
            emit({
                "type": "navigation",
                "index": index,
                "time": round(float(rows[index]["start"]), 3),
                "jump_ok": ok,
                "next_index": expected_next,
                "next_ok": next_ok,
                "ok": ok and next_ok,
            }, args.json_lines)

    for index, motion in long_replica_motion.items():
        target_travel = max(motion["target"]) - min(motion["target"])
        content_travel = max(motion["content"]) - min(motion["content"])
        if target_travel > 100 and content_travel < min(20, target_travel * 0.1):
            failures.append(
                f"row {index}: scroll appears stuck; target travelled "
                f"{target_travel:.1f}px, content only {content_travel:.1f}px"
            )

    stress_rng = random.Random(args.seed)
    edited_originals: dict[str, str] = {}
    stress_actions = (
        "rapid-seek",
        "seek-resize",
        "font",
        "focus",
        "mode",
        "model-refresh",
        "edit-current",
        "manual-scroll",
        "actor-filter",
    )

    def stress_time() -> float:
        return stress_rng.uniform(args.start, end)

    def validate_stress(event_number: int, action: str) -> None:
        process_for(min(max(args.tick_ms, 20), max(args.settle_ms, 20), 120))
        live_rows = bridge.teleprompter.model.rows()
        index = bridge.teleprompter.currentIndex
        qml_index = int_property(view, "currentIndex", -1)
        content_y = numeric_property(view, "contentY")
        origin_y = numeric_property(view, "originY")
        content_height = numeric_property(view, "contentHeight")
        viewport_height = numeric_property(view, "height")
        target_y = numeric_property(view, "pageDebugTargetY")
        highlight_opacity = numeric_property(
            view, "pageTargetHighlightOpacity"
        )
        highlight_line_only = bool(
            view.property("pageTargetHighlightLineOnly")
        )
        highlight_height = numeric_property(
            view, "pageTargetHighlightHeight"
        )
        prefetch_index = int_property(view, "pageGapPrefetchIndex", -1)
        event_failures: list[str] = []
        if index != qml_index:
            event_failures.append(
                f"backend index {index}, QML index {qml_index}"
            )
        if not all(math.isfinite(value) for value in (
            content_y, content_height, viewport_height, target_y
        )):
            event_failures.append("non-finite QML geometry")
        maximum_y = origin_y + max(0.0, content_height - viewport_height)
        if content_y < origin_y - 2 or content_y > maximum_y + 2:
            event_failures.append(
                f"contentY {content_y:.1f} outside "
                f"{origin_y:.1f}..{maximum_y:.1f}"
            )
        if (
            highlight_opacity > 0.001
            and highlight_line_only
            and (not math.isfinite(highlight_height) or highlight_height <= 0)
        ):
            event_failures.append(
                f"invalid line highlight height {highlight_height:.1f}"
            )
        if prefetch_index >= 0:
            if prefetch_index >= len(live_rows):
                event_failures.append(
                    f"stale prefetch index {prefetch_index}/{len(live_rows)}"
                )
            elif (
                prefetch_index <= index
                or not live_rows[prefetch_index].get("active")
            ):
                event_failures.append(
                    f"invalid prefetch target {prefetch_index} from {index}"
                )
        for message in event_failures:
            failures.append(
                f"stress {event_number} {action}: {message}"
            )
        emit({
            "type": "stress",
            "event": event_number,
            "action": action,
            "time": round(bridge.teleprompter.time, 3),
            "index": index,
            "qml_index": qml_index,
            "mode": "page" if bool(view.property("pageScrollMode"))
                else "continuous",
            "viewport": (
                f"{numeric_property(view, 'width'):.1f}x"
                f"{viewport_height:.1f}"
            ),
            "content_y": round(content_y, 1),
            "origin_y": round(origin_y, 1),
            "target_y": round(target_y, 1),
            "highlight_scope": (
                "none" if highlight_opacity <= 0.001
                else "line" if highlight_line_only else "block"
            ),
            "highlight_height": round(highlight_height, 1),
            "highlight_opacity": round(highlight_opacity, 3),
            "prefetch_index": prefetch_index,
            "ok": not event_failures,
        }, args.json_lines)

    for event_number in range(1, args.stress_events + 1):
        action = stress_rng.choice(stress_actions)
        if action == "rapid-seek":
            bridge.teleprompter.debugSetReaperTime(stress_time())
            bridge.teleprompter.debugSetReaperTime(stress_time())
        elif action == "seek-resize":
            bridge.teleprompter.debugSetReaperTime(stress_time())
            window.setProperty("width", stress_rng.randint(760, 1500))
            window.setProperty("height", stress_rng.randint(520, 980))
        elif action == "font":
            update_config(f_text=stress_rng.choice((20, 28, 36, 48, 64)))
        elif action == "focus":
            update_config(focus_ratio=stress_rng.choice((0.15, 0.25, 0.5, 0.75)))
        elif action == "mode":
            update_config(
                page_scroll_mode=not bool(view.property("pageScrollMode"))
            )
        elif action == "model-refresh":
            bridge.teleprompter.refresh()
        elif action == "edit-current":
            live_rows = bridge.teleprompter.model.rows()
            index = bridge.teleprompter.currentIndex
            payload = bridge._script_text_service.get_episode_payload(
                bridge._session.data, episode
            )
            if 0 <= index < len(live_rows) and isinstance(payload, dict):
                source_ids = list(live_rows[index].get("sourceIds") or [])
                working_id = str(source_ids[0]) if source_ids else ""
                for line in payload.get("lines", []):
                    if str(line.get("id")) != working_id:
                        continue
                    if working_id not in edited_originals:
                        edited_originals[working_id] = str(line.get("text") or "")
                    original = edited_originals[working_id]
                    line["text"] = (
                        original
                        if str(line.get("text") or "") != original
                        else original + " [диагностический reflow]"
                    )
                    bridge.teleprompter.refresh()
                    break
        elif action == "manual-scroll":
            invoked = QMetaObject.invokeMethod(
                view, "beginManualDragScroll"
            )
            if not invoked:
                view.setProperty("manualDragScroll", True)
            origin_y = numeric_property(view, "originY")
            maximum_y = origin_y + max(
                0.0,
                numeric_property(view, "contentHeight")
                    - numeric_property(view, "height"),
            )
            view.setProperty(
                "contentY", stress_rng.uniform(origin_y, maximum_y)
            )
            invoked = QMetaObject.invokeMethod(
                view, "finishManualDragScroll"
            )
            if not invoked:
                view.setProperty("manualDragScroll", False)
            bridge.teleprompter.debugSetReaperTime(stress_time())
        elif action == "actor-filter":
            actor_rows = bridge.teleprompter.actorModel.rows()
            if actor_rows:
                actor = stress_rng.choice(actor_rows)
                bridge.teleprompter.setActorSelected(
                    str(actor.get("actorId") or ""),
                    not bool(actor.get("selected")),
                )
            else:
                bridge.teleprompter.refresh()
        validate_stress(event_number, action)

    for failure in failures:
        emit({"type": "failure", "message": failure}, args.json_lines)
    emit({
        "type": "summary",
        "status": "PASS" if not failures else "FAIL",
        "failures": len(failures),
        "samples": sample_count,
        "transitions": transition_count,
        "ass_page_turns": ass_page_turns,
        "fallback_page_turns": fallback_page_turns,
        "prefetch_starts": prefetch_starts,
        "stress_events": args.stress_events,
        "seed": args.seed,
    }, args.json_lines)

    window.setProperty("visible", False)
    bridge.teleprompter.debugSetSimulationActive(False)
    bridge.teleprompter.close()
    window.deleteLater()
    process_for(1)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
