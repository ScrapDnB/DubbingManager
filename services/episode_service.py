"""Service for managing episodes and parsing ASS/SRT files."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from utils.helpers import ass_time_to_seconds, srt_time_to_seconds

logger = logging.getLogger(__name__)


class EpisodeService:
    """Episode Service implementation."""

    def __init__(self, merge_gap: int = 5, fps: float = 25.0):
        self.merge_gap = merge_gap
        self.fps = fps
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
                        text = re.sub(r'\{.*?\}', '', parts[9]).strip()

                        if text:
                            line_data = {
                                's': ass_time_to_seconds(parts[1]),
                                'e': ass_time_to_seconds(parts[2]),
                                'char': char,
                                'text': text,
                                's_raw': parts[1]
                            }
                            lines_list.append(line_data)

                            char_data[char]["lines"] += 1
                            char_data[char]["raw"].append(line_data)

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
                full_text = '\n'.join(text_lines).strip()

                # Extract the character name from text formatted as "Name: replica"
                char_name = ""
                replica_text = full_text

                # Use the first colon to extract the name
                colon_match = re.match(r'^([^:]+):\s*(.*)', full_text, re.DOTALL)
                if colon_match:
                    char_name = colon_match.group(1).strip()
                    replica_text = colon_match.group(2).strip()

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
                            lines.append({
                                'id': idx,
                                's': ass_time_to_seconds(parts[1]),
                                'e': ass_time_to_seconds(parts[2]),
                                'char': parts[4].strip(),
                                'text': re.sub(r'\{.*?\}', '', parts[9]).strip(),
                                's_raw': parts[1]
                            })
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
        """Save episode to ass."""
        if not memory_lines:
            return False, "Нет данных для сохранения"

        source_path = episodes.get(ep_num)
        if not source_path:
            return False, "Файл не найден"

        # Save DOCX imports to a new ASS file because they do not exist on disk
        if not os.path.exists(source_path) or source_path.lower().endswith('.docx'):
            # Save as a new ASS file
            if target_path is None:
                target_path = source_path.replace('.docx', '.ass') if source_path.lower().endswith('.docx') else f"{ep_num}.ass"
            return self.save_episode_to_ass_new(ep_num, memory_lines, target_path)

        save_path = target_path or source_path

        # Detect the file type
        if source_path.lower().endswith('.srt'):
            return self.save_episode_to_srt(ep_num, episodes, memory_lines, target_path)

        new_file_content = []

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                dia_idx = 0

                for line in f:
                    if line.startswith("Dialogue:"):
                        if dia_idx < len(memory_lines):
                            current_data = memory_lines[dia_idx]
                            parts = line.strip().split(',', 9)

                            if len(parts) > 9:
                                parts[4] = current_data['char']
                                new_line = (
                                    f"{','.join(parts[:9])},"
                                    f"{current_data['text']}\n"
                                )
                                new_file_content.append(new_line)
                            else:
                                new_file_content.append(line)
                        else:
                            new_file_content.append(line)

                        dia_idx += 1
                    else:
                        new_file_content.append(line)

            with open(save_path, 'w', encoding='utf-8') as f:
                f.writelines(new_file_content)

            logger.info(f"ASS saved to {save_path}")
            return True, f"Серия {ep_num} сохранена"

        except Exception as e:
            logger.error(f"Error saving ASS: {e}")
            return False, f"Ошибка записи: {e}"

    def save_episode_to_ass_new(
        self,
        ep_num: str,
        memory_lines: List[Dict[str, Any]],
        save_path: str
    ) -> Tuple[bool, str]:
        """Save episode to ass new."""
        if not memory_lines:
            return False, "Нет данных для сохранения"

        # Standard ASS file header
        ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(ass_header)

                for line in memory_lines:
                    # Convert seconds back to ASS time format
                    start_time = self._seconds_to_ass_time(line.get('s', 0))
                    end_time = self._seconds_to_ass_time(line.get('e', 0))
                    char = line.get('char', '')
                    text = line.get('text', '')

                    # ASS format: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                    # Name (Actor) stores the character name
                    dialogue_line = f"Dialogue: 0,{start_time},{end_time},,{char},0,0,0,,{text}\n"
                    f.write(dialogue_line)

            logger.info(f"New ASS saved to {save_path}")
            return True, f"Серия {ep_num} сохранена в {save_path}"

        except Exception as e:
            logger.error(f"Error saving new ASS: {e}")
            return False, f"Ошибка записи: {e}"

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
        """Save episode to srt."""
        if not memory_lines:
            return False, "Нет данных для сохранения"

        source_path = episodes.get(ep_num)
        if not source_path or not os.path.exists(source_path):
            return False, "Файл не найден"

        save_path = target_path or source_path

        try:
            # Read the original SRT to preserve timings
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()

            blocks = re.split(r'\n\s*\n', content.strip())
            new_file_content = []
            line_idx = 0

            for block in blocks:
                block_lines = block.strip().split('\n')
                if len(block_lines) < 2:
                    continue

                try:
                    # The first line is the number
                    block_num = block_lines[0].strip()
                    
                    # The second line is timing
                    time_line = block_lines[1].strip()
                    
                    # If this replica has data
                    if line_idx < len(memory_lines):
                        current_data = memory_lines[line_idx]
                        # Build text as "Name: replica" or just "replica"
                        if current_data.get('char'):
                            full_text = f"{current_data['char']}: {current_data['text']}"
                        else:
                            full_text = current_data['text']
                        
                        new_block = f"{block_num}\n{time_line}\n{full_text}"
                        new_file_content.append(new_block)
                        line_idx += 1
                    else:
                        # Keep the original block
                        new_file_content.append(block.strip())
                        
                except Exception:
                    # Keep the original block on errors
                    new_file_content.append(block.strip())

            # Write the file
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(new_file_content) + '\n')

            logger.info(f"SRT saved to {save_path}")
            return True, f"Серия {ep_num} сохранена"

        except Exception as e:
            logger.error(f"Error saving SRT: {e}")
            return False, f"Ошибка записи: {e}"

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
