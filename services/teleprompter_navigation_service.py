"""Pure teleprompter navigation and text helpers."""

from typing import List


class TeleprompterNavigationService:
    """Small pure helpers used by the teleprompter UI."""

    def compute_scroll_tau(self, slider_value: int) -> float:
        """Compute smooth-scroll time constant from a 0-100 slider value."""
        if slider_value <= 0:
            return 0.0

        min_tau = 0.01
        max_tau = 2.0
        p = 1.15
        n = float(slider_value) / 100.0
        return min_tau + (n ** p) * (max_tau - min_tau)

    def split_merged_text(self, text: str, ids: List[int]) -> List[str]:
        """Split edited merged text back into per-line parts when unambiguous."""
        if not text or len(ids) < 2:
            return []

        parts = []
        if ' // ' in text:
            parts = [p.strip() for p in text.split(' // ') if p.strip()]
        elif ' / ' in text:
            parts = [p.strip() for p in text.split(' / ') if p.strip()]

        if len(parts) == len(ids):
            return parts
        return []
