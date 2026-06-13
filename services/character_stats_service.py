"""Character statistics helpers."""

import csv
from io import StringIO
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple

from services.assignment_service import get_actor_for_character
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

    def project_casting_csv_rows(
        self,
        get_episode_lines: Callable[[str], List[Dict[str, Any]]],
    ) -> List[List[Any]]:
        """Return casting summary rows by character, actor and episode rings."""
        episodes = sorted(
            (str(ep) for ep in self.data_ref.get("episodes", {}).keys()),
            key=natural_sort_key
        )
        header: List[Any] = ["Персонаж", "Актёр", *episodes, "Всего"]
        rows_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
        export_service = ExportService(self.data_ref)
        actors = self.data_ref.get("actors", {})
        next_order = 0

        for ep in episodes:
            lines = get_episode_lines(ep)
            if not lines:
                continue

            processed = export_service.process_merge_logic(
                lines,
                self.data_ref.get("replica_merge_config", {})
            )

            for line in processed:
                char = line.get("char", "")
                if not char:
                    continue

                actor_id = get_actor_for_character(self.data_ref, char, ep)
                actor_name = (
                    actors.get(actor_id, {}).get("name", "")
                    if actor_id
                    else ""
                )
                key = (char, actor_name)
                row = rows_by_key.get(key)
                if row is None:
                    row = {
                        "char": char,
                        "actor": actor_name,
                        "first_ep": ep,
                        "order": next_order,
                        "episodes": defaultdict(int),
                    }
                    rows_by_key[key] = row
                    next_order += 1
                row["episodes"][ep] += 1

        rows: List[List[Any]] = [header]
        rows_by_first_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows_by_key.values():
            rows_by_first_episode[row["first_ep"]].append(row)

        for ep in episodes:
            episode_rows = sorted(
                rows_by_first_episode.get(ep, []),
                key=lambda row: row["order"]
            )
            if not episode_rows:
                continue

            if len(rows) > 1:
                rows.append([f"{ep} серия", "", *["" for _ in episodes], 0])

            for row in episode_rows:
                counts = [row["episodes"].get(ep_num, 0) for ep_num in episodes]
                total = sum(counts)
                rows.append([
                    row["char"],
                    row["actor"],
                    *[count if count else "" for count in counts],
                    total,
                ])

        return rows

    def project_casting_csv(
        self,
        get_episode_lines: Callable[[str], List[Dict[str, Any]]],
    ) -> str:
        """Return a CSV summary ready for Google Sheets import/paste."""
        buffer = StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerows(self.project_casting_csv_rows(get_episode_lines))
        return buffer.getvalue()
