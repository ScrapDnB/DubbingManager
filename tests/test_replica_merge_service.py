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


def test_replica_merge_service_preserves_working_text_lines():
    service = ReplicaMergeService()
    lines = [{"id": 1, "_working_text": True, "text": "edited"}]

    result = service.process(lines, {"merge": True})

    assert result == lines
    assert result[0] is not lines[0]
