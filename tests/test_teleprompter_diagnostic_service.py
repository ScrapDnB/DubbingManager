"""Tests for long-running teleprompter diagnostic sessions."""

import gzip
import json

from services.teleprompter_diagnostic_service import (
    TeleprompterDiagnosticService,
)


def _events(session_dir):
    result = []
    for path in sorted(session_dir.glob("events-*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            result.extend(json.loads(line) for line in handle if line.strip())
    return result


def test_diagnostic_session_writes_manifest_events_and_summary(tmp_path):
    service = TeleprompterDiagnosticService()

    session_dir = service.start(
        tmp_path,
        "05",
        {"config": {"page_scroll_mode": True}, "replica_count": 42},
    )
    service.record("viewport_sample", {
        "content_y": 10,
        "origin_y": 0,
        "viewport_height": 700,
    })
    service.mark_problem({"comment": "Мерцание"})
    assert service.screenshot_path("a00001").endswith("_a00001.png")
    assert service.stop() == session_dir

    manifest = json.loads((session_dir / "manifest.json").read_text("utf-8"))
    summary = json.loads((session_dir / "summary.json").read_text("utf-8"))
    anomalies = [
        json.loads(line)
        for line in (session_dir / "anomalies.jsonl").read_text("utf-8").splitlines()
    ]

    assert manifest["schema_version"] == 1
    assert manifest["episode"] == "05"
    assert manifest["replica_count"] == 42
    assert summary["event_count"] >= 5
    assert summary["anomaly_counts"] == {"operator_marker": 1}
    assert summary["dropped_events"] == 0
    assert anomalies[0]["kind"] == "operator_marker"
    assert {event["event"] for event in _events(session_dir)} >= {
        "session_started",
        "viewport_sample",
        "operator_marker",
        "anomaly",
        "session_stopped",
    }


def test_diagnostic_session_detects_fast_scroll_and_unexplained_teleport(
    tmp_path,
):
    service = TeleprompterDiagnosticService()
    session_dir = service.start(tmp_path, "1", {})

    fast = service.record("page_scroll_started", {
        "distance_screens": 0.8,
        "actual_duration_ms": 120,
    })
    service.record("viewport_sample", {
        "content_y": 0,
        "origin_y": 0,
        "viewport_height": 800,
        "animation_running": False,
    })
    teleport = service.record("viewport_sample", {
        "content_y": 400,
        "origin_y": 0,
        "viewport_height": 800,
        "animation_running": False,
    })
    service.stop()

    assert fast == "a00001"
    assert teleport == "a00002"
    summary = json.loads((session_dir / "summary.json").read_text("utf-8"))
    assert summary["anomaly_counts"] == {
        "fast_scroll": 1,
        "teleport": 1,
    }


def test_expected_exact_position_does_not_report_a_teleport(tmp_path):
    service = TeleprompterDiagnosticService()
    service.start(tmp_path, "1", {})
    service.record("viewport_sample", {
        "content_y": 0,
        "origin_y": 0,
        "viewport_height": 800,
    })
    service.record("instant_position", {
        "source_y": 0,
        "target_y": 600,
    })
    anomaly = service.record("viewport_sample", {
        "content_y": 600,
        "origin_y": 0,
        "viewport_height": 800,
    })
    service.stop()

    assert anomaly == ""
