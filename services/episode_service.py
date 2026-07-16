"""Service for managing episodes and parsing ASS/SRT files."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from config.constants import DEFAULT_ASS_IMPORT_CONFIG, DEFAULT_SRT_IMPORT_CONFIG
from utils.helpers import ass_time_to_seconds, srt_time_to_seconds

logger = logging.getLogger(__name__)


class EpisodeService:
    """Episode Service implementation."""

    def __init__(
        self,
        merge_gap: int = 5,
        fps: float = 25.0,
        ass_import_config: Optional[Dict[str, Any]] = None,
        srt_import_config: Optional[Dict[str, Any]] = None,
    ):
        self.merge_gap = merge_gap
        self.fps = fps
        self.ass_import_config = {
            **DEFAULT_ASS_IMPORT_CONFIG,
            **(ass_import_config or {}),
        }
        self.srt_import_config = {
            **DEFAULT_SRT_IMPORT_CONFIG,
            **(srt_import_config or {}),
        }
        self._loaded_episodes: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_timestamps: Dict[str, float] = {}  # Cache timestamps

    def set_merge_gap_from_config(self, replica_merge_config: Dict[str, Any]) -> None:
        """Set merge gap from config."""
        self.merge_gap = replica_merge_config.get('merge_gap', 5)
        # Guard against None and zero values
        self.fps = replica_merge_config.get('fps', 25.0) or 25.0

    def set_fps(self, fps: float) -> None:
        """Set the frame rate."""
        self.fps = fps

    def set_import_configs(
        self,
        ass_config: Optional[Dict[str, Any]] = None,
        srt_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.ass_import_config = {
            **DEFAULT_ASS_IMPORT_CONFIG,
            **(ass_config or {}),
        }
        self.srt_import_config = {
            **DEFAULT_SRT_IMPORT_CONFIG,
            **(srt_config or {}),
        }

    def _split_ass_characters(self, raw_character: str) -> List[str]:
        """Return one or more ASS Name/Actor values split by semicolon."""
        if not self.ass_import_config.get('split_character_names', True):
            return [str(raw_character or "").strip()]
        separator = str(
            self.ass_import_config.get('character_separator', ';') or ';'
        )
        characters = [
            part.strip()
            for part in str(raw_character or "").split(separator)
            if part.strip()
        ]
        return characters or [str(raw_character or "").strip()]

    def _expand_ass_line_by_characters(
        self,
        line_data: Dict[str, Any],
        raw_character: str
    ) -> List[Dict[str, Any]]:
        """Duplicate ASS line data for each semicolon-separated character."""
        expanded = []
        for character in self._split_ass_characters(raw_character):
            character_line = line_data.copy()
            character_line["char"] = character
            expanded.append(character_line)
        return expanded

    def parse_ass_file(self, path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse ass file."""
        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines_list = []

                for line in f:
                    if line.startswith("Dialogue:"):
                        parts = line.split(',', 9)
                        if len(parts) < 10:
                            continue

                        char = parts[4].strip()
                        text = parts[9]
                        if self.ass_import_config.get('strip_override_tags', True):
                            text = re.sub(r'\{.*?\}', '', text)
                        text = text.strip()

                        if not text and not char:
                            continue

                        line_data = {
                            's': ass_time_to_seconds(parts[1]),
                            'e': ass_time_to_seconds(parts[2]),
                            'text': text,
                            's_raw': parts[1]
                        }

                        for character_line in self._expand_ass_line_by_characters(
                            line_data,
                            char
                        ):
                            lines_list.append(character_line)
                            character = character_line["char"]
                            char_data[character]["lines"] += 1
                            char_data[character]["raw"].append(character_line)

                # Calculate statistics
                # Convert merge_gap from frames to seconds
                merge_gap_seconds = self.merge_gap / self.fps

                stats = []
                for char, info in char_data.items():
                    rings = 1
                    words = 0
                    char_lines = info["raw"]

                    if char_lines:
                        words = len(char_lines[0]['text'].split())

                        for i in range(1, len(char_lines)):
                            if char_lines[i]['s'] - char_lines[i-1]['e'] >= merge_gap_seconds:
                                rings += 1
                            words += len(char_lines[i]['text'].split())

                    stats.append({
                        "name": char,
                        "lines": info["lines"],
                        "rings": rings,
                        "words": words
                    })

                return stats, lines_list

        except Exception as e:
            logger.error(f"Error parsing ASS: {e}")
            return [], []

    def _parse_srt_content(
        self,
        content: str,
        add_id: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse SRT content."""
        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        # Split into blocks, one block per replica
        blocks = re.split(r'\n\s*\n', content.strip())
        lines_list = []
        idx = 0

        for block in blocks:
            block_lines = block.strip().split('\n')
            if len(block_lines) < 3:
                continue

            try:
                time_line = block_lines[1]
                time_parts = time_line.split(' --> ')
                if len(time_parts) != 2:
                    continue

                start_time = time_parts[0].strip()
                end_time = time_parts[1].strip()

                # Replica text, possibly spanning several lines
                text_lines = block_lines[2:]
                joiner = (
                    '\n'
                    if self.srt_import_config.get('keep_multiline', True)
                    else ' '
                )
                full_text = joiner.join(text_lines).strip()

                # Extract the character name from text formatted as "Name: replica"
                char_name = str(
                    self.srt_import_config.get('default_character', '')
                ).strip()
                replica_text = full_text

                if self.srt_import_config.get('detect_character_prefix', True):
                    separator = str(
                        self.srt_import_config.get('character_separator', ':')
                        or ':'
                    )
                    prefix_match = re.match(
                        rf'^(.+?){re.escape(separator)}\s*(.*)',
                        full_text,
                        re.DOTALL,
                    )
                    if prefix_match:
                        char_name = prefix_match.group(1).strip()
                        replica_text = prefix_match.group(2).strip()

                if replica_text:
                    line_data = {
                        's': srt_time_to_seconds(start_time),
                        'e': srt_time_to_seconds(end_time),
                        'char': char_name,
                        'text': replica_text,
                        's_raw': start_time
                    }
                    if add_id:
                        line_data['id'] = idx
                    lines_list.append(line_data)

                    char_data[char_name]["lines"] += 1
                    char_data[char_name]["raw"].append(line_data)
                    idx += 1

            except (IndexError, ValueError) as e:
                logger.warning(f"Skipping invalid SRT block: {e}")
                continue

        # Calculate statistics
        # Convert merge_gap from frames to seconds
        merge_gap_seconds = self.merge_gap / self.fps

        stats = []
        for char, info in char_data.items():
            rings = 1
            words = 0
            char_lines = info["raw"]

            if char_lines:
                words = len(char_lines[0]['text'].split())

                for i in range(1, len(char_lines)):
                    # Ignore the "Character:" prefix when merging replicas
                    if char_lines[i]['s'] - char_lines[i-1]['e'] >= merge_gap_seconds:
                        rings += 1
                    words += len(char_lines[i]['text'].split())

            stats.append({
                "name": char,
                "lines": info["lines"],
                "rings": rings,
                "words": words
            })

        return stats, lines_list

    def parse_srt_file(self, path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse srt file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            return self._parse_srt_content(content, add_id=False)

        except Exception as e:
            logger.error(f"Error parsing SRT: {e}")
            return [], []

    def load_episode(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Load an episode into memory and refresh stale cache entries."""
        path = episodes.get(ep_num)
        
        # Check the cache only when the file exists and has not changed
        if ep_num in self._loaded_episodes and path:
            # Check the file timestamp
            try:
                file_mtime = Path(path).stat().st_mtime
                cache_mtime = self._cache_timestamps.get(ep_num, 0)
                
                if file_mtime <= cache_mtime:
                    # The cache is current
                    return self._loaded_episodes[ep_num]
            except (OSError, FileNotFoundError):
                pass  # Reload on errors
        
        # The file is missing or the cache is stale
        if not path or not os.path.exists(path):
            return []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = []
                idx = 0

                for line in f:
                    if line.startswith("Dialogue:"):
                        parts = line.split(',', 9)
                        if len(parts) >= 10:
                            line_data = {
                                's': ass_time_to_seconds(parts[1]),
                                'e': ass_time_to_seconds(parts[2]),
                                'text': re.sub(r'\{.*?\}', '', parts[9]).strip(),
                                's_raw': parts[1]
                            }
                            for character_line in self._expand_ass_line_by_characters(
                                line_data,
                                parts[4].strip()
                            ):
                                character_line['id'] = idx
                                lines.append(character_line)
                                idx += 1

                self._loaded_episodes[ep_num] = lines
                # Store the cache timestamp
                self._cache_timestamps[ep_num] = Path(path).stat().st_mtime
                return lines

        except Exception as e:
            logger.error(f"Read error: {e}")
            return []

    def load_srt_episode(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Load an SRT episode into memory and refresh stale cache entries."""
        path = episodes.get(ep_num)
        
        # Check the cache only when the file exists and has not changed
        if ep_num in self._loaded_episodes and path:
            try:
                file_mtime = Path(path).stat().st_mtime
                cache_mtime = self._cache_timestamps.get(ep_num, 0)
                
                if file_mtime <= cache_mtime:
                    return self._loaded_episodes[ep_num]
            except (OSError, FileNotFoundError):
                pass
        
        if not path or not os.path.exists(path):
            return []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Use the shared parser without statistics
            _, lines = self._parse_srt_content(content, add_id=True)
            self._loaded_episodes[ep_num] = lines
            # Store the cache timestamp
            self._cache_timestamps[ep_num] = Path(path).stat().st_mtime
            return lines

        except Exception as e:
            logger.error(f"Read error: {e}")
            return []

    def get_episode_lines(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Return episode lines, loading them when needed."""
        return self.load_episode(ep_num, episodes)

    def save_episode_to_ass(
        self,
        ep_num: str,
        episodes: Dict[str, str],
        memory_lines: List[Dict[str, Any]],
        target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Reject legacy writes back to subtitle source files."""
        return False, "Запись изменений обратно в ASS/SRT отключена"

    def save_episode_to_ass_new(
        self,
        ep_num: str,
        memory_lines: List[Dict[str, Any]],
        save_path: str
    ) -> Tuple[bool, str]:
        """Reject legacy ASS creation from imported episode data."""
        return False, "Создание ASS из рабочего текста отключено"

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def save_episode_to_srt(
        self,
        ep_num: str,
        episodes: Dict[str, str],
        memory_lines: List[Dict[str, Any]],
        target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Reject legacy writes back to subtitle source files."""
        return False, "Запись изменений обратно в ASS/SRT отключена"

    def clear_cache(self, ep_num: Optional[str] = None) -> None:
        """Clear the loaded episode cache."""
        if ep_num:
            self._loaded_episodes.pop(ep_num, None)
            self._cache_timestamps.pop(ep_num, None)
        else:
            self._loaded_episodes.clear()
            self._cache_timestamps.clear()

    def invalidate_episode(self, ep_num: str) -> None:
        """Invalidate the episode cache after changes."""
        if ep_num in self._loaded_episodes:
            del self._loaded_episodes[ep_num]
        if ep_num in self._cache_timestamps:
            del self._cache_timestamps[ep_num]

    def set_merge_gap(self, gap: int) -> None:
        """Set the replica merge gap."""
        self.merge_gap = gap
