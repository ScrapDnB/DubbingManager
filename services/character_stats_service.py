"""Character statistics helpers."""

from collections import defaultdict
from typing import Any, Callable, Dict, List

from services.export_service import ExportService
from utils.helpers import natural_sort_key


class CharacterStatsService:
    """Calculate episode and project character statistics."""

    def __init__(self, data_ref: Dict[str, Any]) -> None:
        self.data_ref = data_ref

    def episode_stats(
        self,
        lines: List[Dict[str, Any]],
        merge_gap: int,
        fps: float
    ) -> List[Dict[str, Any]]:
        """Calculate per-character stats for one episode."""
        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        for line in lines:
            char = line.get('char', '')
            if char:
                char_data[char]["lines"] += 1
                char_data[char]["raw"].append(line)

        merge_gap_seconds = merge_gap / fps

        stats = []
        for char, info in char_data.items():
            rings = 1
            words = 0
            char_lines = info["raw"]

            if char_lines:
                words = len(char_lines[0]['text'].split())

                for i in range(1, len(char_lines)):
                    if char_lines[i]['s'] - char_lines[i - 1]['e'] >= merge_gap_seconds:
                        rings += 1
                    words += len(char_lines[i]['text'].split())

            stats.append({
                "name": char,
                "lines": info["lines"],
                "rings": rings,
                "words": words
            })

        return stats

    def project_stats(
        self,
        char_name: str,
        get_episode_lines: Callable[[str], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Calculate per-character stats across all project episodes."""
        result: Dict[str, Any] = {
            "rings": 0,
            "words": 0,
            "episodes": []
        }
        export_service = ExportService(self.data_ref)

        for ep in sorted(
            self.data_ref.get("episodes", {}).keys(),
            key=natural_sort_key
        ):
            lines = get_episode_lines(str(ep))
            if not lines:
                continue

            processed = export_service.process_merge_logic(
                lines,
                self.data_ref.get("replica_merge_config", {})
            )
            ep_rings = 0
            ep_words = 0

            for line in processed:
                if line.get("char") != char_name:
                    continue
                ep_rings += 1
                ep_words += len(line.get("text", "").split())

            if ep_rings:
                result["episodes"].append({
                    "episode": str(ep),
                    "rings": ep_rings,
                    "words": ep_words
                })
                result["rings"] += ep_rings
                result["words"] += ep_words

        return result
