"""Regression tests for efficient teleprompter position lookup."""

from ui.qml_backend.features.teleprompter_bridge import _replica_index_at_time


def test_update_index_uses_cached_start_times_without_copying_model_rows():
    start_times = [float(value) for value in range(100_000)]

    assert _replica_index_at_time(start_times, 54_321.5) == 54_321


def test_update_index_keeps_first_row_selected_before_its_start():
    assert _replica_index_at_time([10.0, 20.0], 0.0) == 0
    assert _replica_index_at_time([], 0.0) == -1
