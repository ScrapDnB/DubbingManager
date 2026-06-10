"""Tests for pure teleprompter navigation helpers."""

from services.teleprompter_navigation_service import TeleprompterNavigationService


def test_compute_scroll_tau_handles_disabled_and_monotonic_values():
    service = TeleprompterNavigationService()

    assert service.compute_scroll_tau(0) == 0.0
    assert service.compute_scroll_tau(10) < service.compute_scroll_tau(80)


def test_split_merged_text_supports_known_separators():
    service = TeleprompterNavigationService()

    assert service.split_merged_text("one // two", [1, 2]) == ["one", "two"]
    assert service.split_merged_text("one / two", [1, 2]) == ["one", "two"]
    assert service.split_merged_text("one two", [1, 2]) == []
    assert service.split_merged_text("one // two", [1, 2, 3]) == []
