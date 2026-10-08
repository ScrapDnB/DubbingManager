"""Tests for replica merge service."""

from services.replica_merge_service import ReplicaMergeService


def test_replica_merge_service_merges_adjacent_same_character_lines():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 1.0, "char": "Hero", "text": "one"},
        {"id": 2, "s": 1.1, "e": 2.0, "char": "Hero", "text": "two"},
        {"id": 3, "s": 4.0, "e": 5.0, "char": "Other", "text": "three"},
    ]

    result = service.process(lines, {"merge": True, "merge_gap": 25, "fps": 25})

    assert len(result) == 2
    assert result[0]["text"] == "one  two"
    assert result[0]["source_ids"] == [1, 2]
    assert result[1]["text"] == "three"


def test_merge_can_respect_existing_separators_at_source_boundaries():
    service = ReplicaMergeService()
    lines = [
        {
            "id": 1,
            "s": 0.0,
            "e": 1.0,
            "char": "A",
            "text": "one / / middle /",
        },
        {"id": 2, "s": 1.7, "e": 2.0, "char": "A", "text": "/ two"},
        {"id": 3, "s": 2.7, "e": 3.0, "char": "A", "text": "three / /"},
        {"id": 4, "s": 3.7, "e": 4.0, "char": "A", "text": "four"},
    ]

    result = service.process(lines, {
        "merge": True,
        "respect_existing_separators": True,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    assert result[0]["text"] == "one // middle /  two /  three //  four"
    assert result[0]["source_texts"] == [
        "one / / middle /", "/ two", "three / /", "four",
    ]


def test_merge_respects_split_offscreen_and_onscreen_markers():
    service = ReplicaMergeService()
    config = {
        "merge": True,
        "respect_existing_separators": True,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    }

    for marker_start, marker_end, expected in (
        ("voice (з/", "к) text", "voice (з/к) text"),
        ("voice (в/", "к) text", "voice (в/к) text"),
        ("voice (", "в/к) text", "voice (в/к) text"),
    ):
        lines = [
            {
                "id": 1,
                "s": 0.0,
                "e": 1.0,
                "char": "A",
                "text": marker_start,
            },
            {
                "id": 2,
                "s": 3.5,
                "e": 4.0,
                "char": "A",
                "text": marker_end,
            },
        ]
        assert service.process(lines, config)[0]["text"] == expected


def test_automatic_long_pause_uses_adjacent_slashes():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 1.0, "char": "A", "text": "one"},
        {"id": 2, "s": 3.5, "e": 4.0, "char": "A", "text": "two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    assert result[0]["parts"][1]["sep"] == " //  "
    assert result[0]["text"] == "one //  two"


def test_spaced_double_slash_is_compact_without_respect_mode():
    service = ReplicaMergeService()
    lines = [
        {
            "id": 1,
            "s": 0.0,
            "e": 1.0,
            "char": "A",
            "text": "one / / middle /",
        },
        {"id": 2, "s": 1.7, "e": 2.0, "char": "A", "text": "two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "respect_existing_separators": False,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    assert result[0]["text"] == "one // middle //  two"
    assert result[0]["source_texts"] == ["one / / middle /", "two"]


def test_replica_merge_service_preserves_working_text_lines():
    service = ReplicaMergeService()
    lines = [{"id": 1, "_working_text": True, "text": "edited"}]

    result = service.process(lines, {"merge": True})

    assert result == lines
    assert result[0] is not lines[0]


def test_parallel_mode_merges_character_chains_across_overlapping_lines():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 4.0, "char": "A", "text": "A one"},
        {"id": 2, "s": 1.0, "e": 2.0, "char": "B", "text": "B one"},
        {"id": 3, "s": 3.0, "e": 4.5, "char": "B", "text": "B two"},
        {"id": 4, "s": 4.1, "e": 8.0, "char": "A", "text": "A two"},
    ]
    config = {
        "merge": True,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    }

    regular = service.process(lines, config)
    parallel = service.process(lines, {
        **config,
        "merge_parallel_replicas": True,
    })

    assert [line["char"] for line in regular] == ["A", "B", "A"]
    assert [line["text"] for line in regular] == [
        "A one", "B one /  B two", "A two"
    ]
    assert [line["char"] for line in parallel] == ["A", "B"]
    assert parallel[0]["text"] == "A one  A two"
    assert parallel[0]["source_ids"] == [1, 4]
    assert parallel[0]["parallel_merged"] is True
    assert parallel[0]["s"] == 0.0
    assert parallel[0]["e"] == 8.0
    assert parallel[1]["text"] == "B one /  B two"
    assert parallel[1]["parallel_merged"] is True
    assert "parallel_timecodes" not in parallel[0]
    assert "parallel_timecodes" not in parallel[1]
    assert parallel[1]["parts"][0]["sep"] == ""


def test_parallel_mode_does_not_cross_serial_interjection():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 2.0, "char": "A", "text": "A one"},
        {"id": 2, "s": 2.2, "e": 3.0, "char": "B", "text": "B"},
        {"id": 3, "s": 3.2, "e": 5.0, "char": "A", "text": "A two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_parallel_replicas": True,
        "merge_gap_seconds": 4.8,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    assert [line["text"] for line in result] == ["A one", "B", "A two"]


def test_parallel_timecodes_use_shared_brackets_and_hidden_zeros():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 10.0, "char": "A", "text": "A one"},
        {"id": 2, "s": 1.0, "e": 2.0, "char": "B", "text": "B one"},
        {"id": 3, "s": 8.0, "e": 9.0, "char": "B", "text": "B two"},
        {"id": 4, "s": 16.0, "e": 20.0, "char": "A", "text": "A two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_parallel_replicas": True,
        "merge_gap_seconds": 10.0,
        "p_short": 0.5,
        "p_long": 2.0,
        "hide_leading_timecode_zeros": True,
        "inline_timecode_brackets": "round",
    })

    assert result[0]["text"] == "A one //  (00:16) A two"
    assert result[1]["text"] == "B one //  (00:08) B two"
    assert result[0]["parallel_timecodes"][0]["pause"] == 6.0
    assert result[1]["parallel_timecodes"][0]["pause"] == 6.0


def test_parallel_timecode_requires_pause_strictly_over_five_seconds():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 4.0, "char": "A", "text": "A one"},
        {"id": 2, "s": 1.0, "e": 2.0, "char": "B", "text": "B"},
        {"id": 3, "s": 9.0, "e": 12.0, "char": "A", "text": "A two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_parallel_replicas": True,
        "merge_gap_seconds": 10.0,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    merged = next(line for line in result if line["char"] == "A")
    assert merged["text"] == "A one //  A two"
    assert "parallel_timecodes" not in merged


def test_parallel_timecodes_skip_single_source_replica():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 450.0, "e": 455.0, "char": "A", "text": "A one"},
        {
            "id": 2,
            "s": 455.79,
            "e": 461.5,
            "char": "МАССОВКА",
            "text": "(шум на фоне)",
        },
        {"id": 3, "s": 461.0, "e": 464.0, "char": "A", "text": "A two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_parallel_replicas": True,
        "merge_gap_seconds": 10.0,
        "p_short": 0.5,
        "p_long": 2.0,
    })

    crowd = next(line for line in result if line["char"] == "МАССОВКА")
    assert crowd["text"] == "(шум на фоне)"
    assert "parallel_timecodes" not in crowd
    merged = next(line for line in result if line["char"] == "A")
    assert not merged["text"].startswith("[")
    assert "[0:07:41] A two" in merged["text"]


def test_parallel_timecode_does_not_duplicate_inline_timecode():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 4.0, "char": "A", "text": "A one"},
        {"id": 2, "s": 1.0, "e": 2.0, "char": "B", "text": "B"},
        {"id": 3, "s": 10.0, "e": 14.0, "char": "A", "text": "A two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_parallel_replicas": True,
        "merge_gap_seconds": 10.0,
        "p_short": 0.5,
        "p_long": 2.0,
        "inline_timecodes_enabled": True,
        "inline_timecode_min_duration": 0.0,
        "inline_timecode_every": 1,
    })

    merged = next(line for line in result if line["char"] == "A")
    assert merged["text"].count("[0:00:10]") == 1
    assert merged["inline_timecodes"][0]["part_index"] == 1
    assert merged["parallel_timecodes"][0]["part_index"] == 1


def test_replica_merge_service_adds_timecodes_inside_long_merged_text():
    service = ReplicaMergeService()
    lines = [
        {
            "id": index,
            "s": float(index * 2),
            "e": float(index * 2 + 1.9),
            "char": "Hero",
            "text": f"line-{index + 1}",
        }
        for index in range(5)
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_gap": 25,
        "fps": 25,
        "inline_timecodes_enabled": True,
        "inline_timecode_min_duration": 5,
        "inline_timecode_every": 2,
    })

    assert len(result) == 1
    assert result[0]["text"] == (
        "line-1  line-2  [0:00:04] line-3  line-4  "
        "[0:00:08] line-5"
    )
    assert result[0]["content_text"] == (
        "line-1  line-2  line-3  line-4  line-5"
    )
    assert result[0]["source_texts"] == [
        "line-1", "line-2", "line-3", "line-4", "line-5"
    ]
    assert result[0]["inline_timecodes"] == [
        {
            "part_index": 2,
            "source_id": 2,
            "start": 4.0,
            "label": "0:00:04",
        },
        {
            "part_index": 4,
            "source_id": 4,
            "start": 8.0,
            "label": "0:00:08",
        },
    ]


def test_inline_timecodes_require_duration_strictly_above_threshold():
    service = ReplicaMergeService()
    lines = [
        {"id": 1, "s": 0.0, "e": 1.0, "char": "Hero", "text": "one"},
        {"id": 2, "s": 1.1, "e": 2.0, "char": "Hero", "text": "two"},
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_gap": 25,
        "fps": 25,
        "inline_timecodes_enabled": True,
        "inline_timecode_min_duration": 2.0,
        "inline_timecode_every": 1,
    })

    assert result[0]["text"] == "one  two"
    assert "inline_timecodes" not in result[0]


def test_inline_timecodes_can_hide_leading_hour_zero():
    service = ReplicaMergeService()
    lines = [
        {
            "id": index,
            "s": float(index * 2),
            "e": float(index * 2 + 1.9),
            "char": "Hero",
            "text": f"line-{index + 1}",
        }
        for index in range(3)
    ]

    result = service.process(lines, {
        "merge": True,
        "merge_gap_seconds": 1.0,
        "inline_timecodes_enabled": True,
        "inline_timecode_min_duration": 2.0,
        "inline_timecode_every": 2,
        "inline_timecode_brackets": "round",
        "hide_leading_timecode_zeros": True,
    })

    assert "(00:04)" in result[0]["text"]
    assert result[0]["inline_timecodes"][0]["label"] == "00:04"
