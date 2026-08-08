"""Tests for the headless teleprompter diagnostic command."""

import argparse

import pytest

from tools.teleprompter_diagnostics import (
    build_parser,
    parse_time,
    parse_viewport,
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
        "--focus", "0.3",
        "--layout", "Сценарий 3",
    ])

    assert args.mode == "continuous"
    assert args.seek == [265.0, 508.0]
    assert args.json_lines
    assert args.all_samples
    assert args.resize == [(1000, 650)]
    assert args.font_size == [48]
    assert args.focus == [0.3]
    assert args.layout == ["Сценарий 3"]


def test_parse_viewport_accepts_ascii_and_typographic_separator():
    assert parse_viewport("1240x820") == (1240, 820)
    assert parse_viewport("1000×650") == (1000, 650)


@pytest.mark.parametrize("value", ["", "1000", "wide", "700x500"])
def test_parse_viewport_rejects_invalid_or_too_small_sizes(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_viewport(value)
