"""Tests for the headless teleprompter diagnostic command."""

import argparse

import pytest

from tools.teleprompter_diagnostics import (
    build_parser,
    parse_time,
    parse_viewport,
    scroll_plan_properties,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.5", 12.5),
        ("08:28", 508.0),
        ("1:02:03.5", 3723.5),
    ],
)
def test_parse_time_accepts_seconds_and_timecodes(value, expected):
    assert parse_time(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "-1", "nan", "inf"])
def test_parse_time_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_time(value)


def test_diagnostics_parser_exposes_scrolling_modes_and_seeks():
    args = build_parser().parse_args([
        "example.dub",
        "--mode", "continuous",
        "--seek", "4:25",
        "--seek", "8:28",
        "--json-lines",
        "--all-samples",
        "--resize", "1000x650",
        "--font-size", "48",
        "--smoothness", "100",
        "--focus", "0.3",
        "--layout", "Сценарий 3",
        "--stress-events", "25",
        "--seed", "42",
    ])

    assert args.mode == "continuous"
    assert args.seek == [265.0, 508.0]
    assert args.json_lines
    assert args.all_samples
    assert args.resize == [(1000, 650)]
    assert args.font_size == [48]
    assert args.smoothness == [100]
    assert args.focus == [0.3]
    assert args.layout == ["Сценарий 3"]
    assert args.stress_events == 25
    assert args.seed == 42
    with pytest.raises(SystemExit):
        build_parser().parse_args(["example.dub", "--mode", "smooth"])


def test_parse_viewport_accepts_ascii_and_typographic_separator():
    assert parse_viewport("1240x820") == (1240, 820)
    assert parse_viewport("1000×650") == (1000, 650)


@pytest.mark.parametrize("value", ["", "1000", "wide", "700x500"])
def test_parse_viewport_rejects_invalid_or_too_small_sizes(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_viewport(value)


def test_scroll_plan_properties_exposes_scheduler_decision():
    class FakeView:
        values = {
            "scrollDebugSmoothnessLevel": 88,
            "scrollDebugDistanceScreens": 0.6254,
            "scrollDebugDesiredDurationMs": 2400,
            "scrollDebugAvailableDurationMs": 950,
            "scrollDebugActualDurationMs": 950,
            "scrollDebugDeadline": 123.4567,
            "scrollDebugDurationLimit": "дедлайн",
        }

        def property(self, name):
            return self.values.get(name)

    assert scroll_plan_properties(FakeView()) == {
        "smoothness_level": 88,
        "distance_screens": 0.625,
        "desired_duration_ms": 2400,
        "available_duration_ms": 950,
        "actual_duration_ms": 950,
        "scroll_deadline": 123.457,
        "duration_limit": "дедлайн",
    }
