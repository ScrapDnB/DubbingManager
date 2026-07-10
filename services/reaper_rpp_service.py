"""Service for generating Reaper RPP project files."""

import csv
from typing import Any, Dict, List, Optional, Set

from services.assignment_service import get_actor_for_character
from services.replica_merge_service import ReplicaMergeService


class ReaperRppService:
    """Generate Reaper RPP exports and previews."""

    def __init__(self, project_data: Dict[str, Any]):
        self.project_data = project_data
        self.replica_merge_service = ReplicaMergeService()

    def _hex_to_reaper_color(self, hex_color: str) -> int:
        """Hex to reaper color."""
        if not hex_color or not isinstance(hex_color, str):
            return 0

        value = hex_color.strip().lstrip('#')
        if len(value) != 6:
            return 0

        try:
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
        except ValueError:
            return 0

        return 0x01000000 | (blue << 16) | (green << 8) | red

    def _escape_rpp_text(self, text: Any) -> str:
        """Escape rpp text."""
        return (
            str(text)
            .replace('"', "' ")
            .replace('\r', ' ')
            .replace('\n', ' ')
            .strip()
        )

    def _transliterate_cyrillic(self, text: Any) -> str:
        """Transliterate Cyrillic text to Latin for DAW-friendly track names."""
        mapping = {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
            "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
            "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
            "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
            "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
            "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
            "э": "e", "ю": "yu", "я": "ya",
        }
        result = []
        for char in str(text):
            lower = char.lower()
            replacement = mapping.get(lower)
            if replacement is None:
                result.append(char)
            elif char.isupper():
                result.append(replacement[:1].upper() + replacement[1:])
            else:
                result.append(replacement)
        return "".join(result)

    def _reaper_actor_name(
        self,
        actor: Dict[str, Any],
        transliterate_actor_names: bool = False
    ) -> str:
        """Return actor name prepared for Reaper track display."""
        name = actor.get("name", "")
        if transliterate_actor_names:
            return self._transliterate_cyrillic(name)
        return str(name)

    def save(self, save_path: str, rpp_content: str) -> None:
        """Save an RPP file with an encoding Reaper reads reliably."""
        with open(save_path, 'w', encoding='utf-8-sig') as f:
            f.write(rpp_content)

    def save_marker_csv(
        self,
        save_path: str,
        ep: str,
        lines: List[Dict[str, Any]]
    ) -> None:
        """Save Reaper marker data as CSV."""
        actors = self.project_data.get("actors", {})
        with open(save_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Number",
                "Start",
                "End",
                "Name",
                "Character",
                "Actor",
                "Text",
                "Color",
            ])
            for idx, line in enumerate(lines, 1):
                char = line.get("char", "")
                text = line.get("text", "")
                actor_id = get_actor_for_character(self.project_data, char, ep)
                actor = actors.get(actor_id, {}) if actor_id else {}
                writer.writerow([
                    idx,
                    f"{float(line.get('s', 0.0)):.4f}",
                    f"{float(line.get('e', 0.0)):.4f}",
                    f"{char}: {text}".strip(),
                    char,
                    actor.get("name", ""),
                    text,
                    actor.get("color", ""),
                ])

    def generate(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        merge_cfg: Optional[Dict[str, Any]] = None,
        video_path: Optional[str] = None,
        use_video: bool = False,
        use_regions: bool = True,
        transliterate_actor_names: bool = False,
        marker_lines: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a Reaper RPP project from episode lines."""
        if merge_cfg is None:
            merge_cfg = self.project_data.get("replica_merge_config", {})

        processed_lines = self.replica_merge_service.process(lines, merge_cfg)
        region_lines = marker_lines if marker_lines is not None else processed_lines
        actors = self.project_data.get("actors", {})

        active_actor_ids: Set[str] = set()
        for line in region_lines:
            actor_id = get_actor_for_character(
                self.project_data,
                line.get('char', ''),
                ep
            )
            if actor_id:
                active_actor_ids.add(actor_id)

        max_time = 600.0
        timed_lines = processed_lines + [
            line for line in region_lines if line not in processed_lines
        ]
        if timed_lines:
            max_time = max(float(line.get('e', 0.0)) for line in timed_lines)
            max_time += 600.0

        rpp = ['<REAPER_PROJECT 0.1 "7.0"']

        if use_regions:
            for i, line in enumerate(region_lines):
                start = float(line.get('s', 0.0))
                end = float(line.get('e', 0.0))

                char = line.get('char', '')
                label = (
                    f"{self._escape_rpp_text(char)}: "
                    f"{self._escape_rpp_text(line.get('text', ''))}"
                )

                actor_id = get_actor_for_character(self.project_data, char, ep)
                actor = actors.get(actor_id, {}) if actor_id else {}
                color_int = self._hex_to_reaper_color(actor.get("color", ""))

                rpp.append(
                    f'  MARKER {i + 1} {start:.4f} "{label}" 1 {color_int}'
                )
                rpp.append(
                    f'  MARKER {i + 1} {end:.4f} "" 1 {color_int}'
                )

        if use_video and video_path:
            rpp.append('   <TRACK')
            rpp.append('    NAME "VIDEO"')
            rpp.append('     <ITEM')
            rpp.append('      POSITION 0.0')
            rpp.append('      LOOP 0')
            rpp.append(f'      LENGTH {max_time:.4f}')
            rpp.append('       <SOURCE VIDEO')
            rpp.append(f'        FILE "{self._escape_rpp_text(video_path)}"')
            rpp.append('       >')
            rpp.append('     >')
            rpp.append('   >')

        sorted_actors = sorted(
            (
                actors[actor_id]
                for actor_id in active_actor_ids
                if actor_id in actors
            ),
            key=lambda actor: self._reaper_actor_name(
                actor, transliterate_actor_names
            ).lower()
        )

        for actor in sorted_actors:
            color_int = self._hex_to_reaper_color(actor.get('color', ''))
            actor_name = self._reaper_actor_name(
                actor,
                transliterate_actor_names
            )
            rpp.append('   <TRACK')
            rpp.append(f'    NAME "{self._escape_rpp_text(actor_name)}"')
            rpp.append(f'    PEAKCOL {color_int}')
            rpp.append('    REC 0')
            rpp.append('    SHOWINMIX 1')
            rpp.append('   >')

        rpp.append('>')
        return '\n'.join(rpp)

    def preview(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        merge_cfg: Optional[Dict[str, Any]] = None,
        video_path: Optional[str] = None,
        use_video: bool = False,
        use_regions: bool = True,
        transliterate_actor_names: bool = False,
        marker_lines: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Return a user-facing preview summary for RPP export."""
        if merge_cfg is None:
            merge_cfg = self.project_data.get("replica_merge_config", {})

        processed_lines = self.replica_merge_service.process(lines, merge_cfg)
        region_lines = marker_lines if marker_lines is not None else processed_lines
        actors = self.project_data.get("actors", {})

        active_actor_ids: Set[str] = set()
        invalid_lines = 0
        sample_regions: List[str] = []

        for line in region_lines:
            start = float(line.get('s', 0.0))
            end = float(line.get('e', 0.0))
            if end <= start:
                invalid_lines += 1

            char = line.get('char', '')
            actor_id = get_actor_for_character(self.project_data, char, ep)
            if actor_id:
                active_actor_ids.add(actor_id)

            if use_regions and len(sample_regions) < 5:
                label = (
                    f"{self._escape_rpp_text(char)}: "
                    f"{self._escape_rpp_text(line.get('text', ''))}"
                )
                sample_regions.append(f"{start:.2f}-{end:.2f}  {label}")

        active_actor_names = sorted(
            self._reaper_actor_name(
                actors.get(actor_id, {"name": actor_id}),
                transliterate_actor_names
            )
            for actor_id in active_actor_ids
        )

        return {
            "regions": len(region_lines) if use_regions else 0,
            "tracks": len(active_actor_ids),
            "actors": active_actor_names,
            "video": bool(use_video and video_path),
            "video_path": video_path if use_video and video_path else None,
            "invalid_lines": invalid_lines,
            "sample_regions": sample_regions,
        }
