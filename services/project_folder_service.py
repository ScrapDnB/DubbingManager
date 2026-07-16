"""Service for project folder management and file discovery."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

from utils.helpers import natural_sort_key

logger = logging.getLogger(__name__)


class ProjectFolderService:
    """Project Folder Service implementation."""

    # File extensions
    SOURCE_EXTENSIONS = {'.ass', '.srt', '.docx'}
    ASS_EXTENSIONS = SOURCE_EXTENSIONS  # Compatibility with existing callers.
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv'}
    TEXT_EXTENSIONS = {'.json'}

    def __init__(self):
        self._found_files_cache: Dict[str, Dict[str, str]] = {}

    def set_project_folder(
        self,
        data: Dict,
        folder_path: str
    ) -> bool:
        """Set the project folder."""
        if not os.path.isdir(folder_path):
            logger.error(f"Folder does not exist: {folder_path}")
            return False

        # Normalize the path
        folder_path = os.path.abspath(folder_path)
        
        # Save into project data
        data["project_folder"] = folder_path
        
        logger.info(f"Project folder set: {folder_path}")
        return True

    def clear_project_folder(self, data: Dict) -> None:
        """Clear the project folder."""
        data.pop("project_folder", None)
        self._found_files_cache.clear()
        logger.info("Project folder cleared")

    def get_project_folder(self, data: Dict) -> Optional[str]:
        """Return the project folder path."""
        return data.get("project_folder")

    def prepare_project_paths(self, data: Dict, project_path: str) -> bool:
        """Rebase portable relative paths when a project is opened elsewhere."""
        project_dir = Path(project_path).expanduser().resolve().parent
        raw_folder = data.get("project_folder")
        references = [
            str(path)
            for field in ("episodes", "video_paths", "episode_texts")
            for path in data.get(field, {}).values()
            if path
        ]

        if not raw_folder:
            if any(not Path(path).expanduser().is_absolute() for path in references):
                data["project_folder"] = str(project_dir)
                return True
            return False

        expanded = Path(str(raw_folder)).expanduser()
        if not expanded.is_absolute():
            data["project_folder"] = str((project_dir / expanded).resolve())
            return data["project_folder"] != str(raw_folder)

        # A portable project may retain an absolute folder from another
        # computer. Prefer the folder containing the opened project whenever
        # its relative references resolve there. This is also robust when a
        # foreign POSIX path is interpreted as an absolute Windows path.
        local_reference_count = sum(
            1
            for reference in references
            if not Path(reference).expanduser().is_absolute()
            and (project_dir / reference).exists()
        )
        if local_reference_count:
            replacement = str(project_dir)
            if replacement != str(raw_folder):
                data["project_folder"] = replacement
                return True
        if expanded.is_dir():
            return False

        candidates = [project_dir, project_dir / expanded.name]
        ranked = sorted(
            (
                sum(
                    1
                    for reference in references
                    if not Path(reference).expanduser().is_absolute()
                    and (candidate / reference).exists()
                ),
                candidate,
            )
            for candidate in candidates
            if candidate.is_dir()
        )
        if not ranked:
            return False
        score, replacement = ranked[-1]
        if score == 0 and replacement == project_dir:
            return False
        data["project_folder"] = str(replacement.resolve())
        return True

    def resolve_project_path(
        self,
        data: Dict,
        path: Optional[str]
    ) -> Optional[str]:
        """Return an absolute path, resolving relative paths from project_folder."""
        if not path:
            return path

        expanded_path = os.path.expanduser(path)
        if os.path.isabs(expanded_path):
            return expanded_path

        folder_path = self.get_project_folder(data)
        if not folder_path:
            return expanded_path

        return os.path.abspath(os.path.join(folder_path, expanded_path))

    def project_path_exists(
        self,
        data: Dict,
        path: Optional[str]
    ) -> bool:
        """Return whether a project path exists after relative resolution."""
        resolved_path = self.resolve_project_path(data, path)
        return bool(resolved_path and os.path.exists(resolved_path))

    def find_all_media_files(
        self,
        folder_path: str
    ) -> Dict[str, Dict[str, str]]:
        """Find all media files."""
        if not os.path.isdir(folder_path):
            return {"ass": {}, "video": {}, "text": {}}

        # Check the cache
        cache_key = folder_path
        if cache_key in self._found_files_cache:
            return self._found_files_cache[cache_key]

        result = {"ass": {}, "video": {}, "text": {}}

        # Recursively walk the folder
        for root, dirs, files in os.walk(folder_path):
            # Skip hidden folders and cache folders
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Extract the episode number from the filename
                episode_num = self._extract_episode_number(file)

                if episode_num:
                    if ext in self.SOURCE_EXTENSIONS:
                        result["ass"][episode_num] = file_path
                    elif ext in self.VIDEO_EXTENSIONS:
                        result["video"][episode_num] = file_path
                    elif ext in self.TEXT_EXTENSIONS and self._is_episode_text_file(file):
                        result["text"][episode_num] = file_path

        # Cache the result
        self._found_files_cache[cache_key] = result

        logger.info(
            f"Found {len(result['ass'])} ASS files "
            f"{len(result['video'])} video files "
            f"and {len(result['text'])} text files"
        )

        return result

    def _is_episode_text_file(self, filename: str) -> bool:
        """Is episode text file."""
        name = os.path.splitext(filename)[0].lower()
        return bool(re.search(r'^(episode|ep|text|script)[_\-\s]*\d+$', name))

    def _extract_episode_number(self, filename: str) -> Optional[str]:
        """Extract an episode number from a filename."""
        # Remove the extension
        name = os.path.splitext(filename)[0]

        # Patterns for finding episode numbers
        patterns = [
            # S01E01, S1E1
            r'[Ss](\d+)[Ee](\d+)',
            # EP01, Ep01, ep01
            r'[Ee][Pp]?(\d+)',
            # Episode 01
            r'[Ee]pisode\s*(\d+)',
            r'-\s*(\d+)',
            # [01]
            r'\[(\d+)\]',
            r'^(\d+)',
            r'(\d+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Combine parts for S01E01
                    return f"{int(groups[0])} {int(groups[1])}"
                else:
                    # Normalize the number by removing leading zeroes
                    num = str(int(groups[0]))
                    return num

        return None

    def _normalize_episode_key(self, episode_num: str) -> str:
        """Return a normalized key for matching episode numbers."""
        value = str(episode_num).strip()
        return str(int(value)) if value.isdigit() else value.lower()

    def _find_replacement_path(
        self,
        found_files: Dict[str, str],
        episode_num: str,
        old_path: Optional[str]
    ) -> Optional[str]:
        """Find a replacement path by episode number or old filename."""
        if episode_num in found_files:
            return found_files[episode_num]

        normalized_episode = self._normalize_episode_key(episode_num)
        for found_episode, path in found_files.items():
            if self._normalize_episode_key(found_episode) == normalized_episode:
                return path

        old_name = os.path.basename(old_path or "")
        if old_name:
            for path in found_files.values():
                if os.path.basename(path) == old_name:
                    return path

        return None

    def _find_file_by_basename(
        self,
        folder_path: str,
        old_path: Optional[str],
        extensions: Set[str]
    ) -> Optional[str]:
        """Find a file in the project folder by the old path basename."""
        old_name = os.path.basename(old_path or "")
        if not old_name:
            return None

        old_ext = os.path.splitext(old_name)[1].lower()
        if old_ext not in extensions:
            return None

        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in files:
                if filename.startswith('.'):
                    continue
                if filename == old_name:
                    return os.path.join(root, filename)

        return None

    def scan_and_link_files(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Tuple[int, int, int]:
        """Scan and link files."""
        if not folder_path:
            folder_path = self.get_project_folder(data)

        if not folder_path:
            return 0, 0, 0

        found = self.find_all_media_files(folder_path)
        
        ass_count = 0
        video_count = 0

        # Update subtitle paths only for existing episodes
        for ep_num, old_path in data.get("episodes", {}).items():
            if self.project_path_exists(data, old_path):
                continue

            path = (
                self._find_replacement_path(found["ass"], ep_num, old_path) or
                self._find_file_by_basename(
                    folder_path, old_path, self.SOURCE_EXTENSIONS
                )
            )
            if path:
                data["episodes"][ep_num] = path
                ass_count += 1
                logger.info(f"Updated subtitle path for episode {ep_num}")

        # Update video paths only for existing entries
        if "video_paths" not in data:
            data["video_paths"] = {}

        for ep_num, old_path in data.get("video_paths", {}).items():
            if self.project_path_exists(data, old_path):
                continue

            path = (
                self._find_replacement_path(found["video"], ep_num, old_path) or
                self._find_file_by_basename(folder_path, old_path, self.VIDEO_EXTENSIONS)
            )
            if path:
                data["video_paths"][ep_num] = path
                video_count += 1
                logger.info(f"Updated video path for episode {ep_num}")

        if "episode_texts" not in data:
            data["episode_texts"] = {}

        text_count = 0
        for ep_num, old_path in data.get("episode_texts", {}).items():
            if self.project_path_exists(data, old_path):
                continue

            path = (
                self._find_replacement_path(found["text"], ep_num, old_path) or
                self._find_file_by_basename(folder_path, old_path, self.TEXT_EXTENSIONS)
            )
            if path:
                data["episode_texts"][ep_num] = path
                text_count += 1
                logger.info(f"Updated text path for episode {ep_num}")

        logger.info(
            f"Relinked {ass_count} subtitle files, "
            f"{video_count} video files and {text_count} text files"
        )

        return ass_count, video_count, text_count

    def find_missing_files(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Find missing files."""
        if not folder_path:
            folder_path = self.get_project_folder(data)

        result = {"ass": [], "video": [], "text": []}

        if not folder_path:
            return result

        found = self.find_all_media_files(folder_path)

        # Check ASS files
        for ep_num in data.get("episodes", {}).keys():
            if ep_num not in found["ass"]:
                result["ass"].append(ep_num)

        # Check video files
        for ep_num in data.get("video_paths", {}).keys():
            if ep_num not in found["video"]:
                result["video"].append(ep_num)

        # Check working-text files
        for ep_num in data.get("episode_texts", {}).keys():
            if ep_num not in found["text"]:
                result["text"].append(ep_num)

        return result

    def get_folder_stats(self, folder_path: str) -> Dict:
        """Return folder stats."""
        found = self.find_all_media_files(folder_path)

        return {
            "ass_count": len(found["ass"]),
            "video_count": len(found["video"]),
            "text_count": len(found["text"]),
            "episodes": sorted(
                set(found["ass"].keys()) |
                set(found["video"].keys()) |
                set(found["text"].keys()),
                key=natural_sort_key
            )
        }

    def invalidate_cache(self, folder_path: Optional[str] = None) -> None:
        """Invalidate cache."""
        if folder_path:
            self._found_files_cache.pop(folder_path, None)
        else:
            self._found_files_cache.clear()

    def suggest_video_for_episode(
        self,
        data: Dict,
        episode_num: str
    ) -> Optional[str]:
        """Suggest video for episode."""
        folder_path = self.get_project_folder(data)
        if not folder_path:
            return None

        found = self.find_all_media_files(folder_path)
        return self._find_replacement_path(
            found["video"], episode_num, None
        )

    def batch_import_from_folder(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Tuple[int, int]:
        """Batch import from folder."""
        if not folder_path:
            folder_path = self.get_project_folder(data)

        if not folder_path:
            return 0, 0

        found = self.find_all_media_files(folder_path)

        added_ass = 0
        added_video = 0

        # Add ASS files
        for ep_num, path in found["ass"].items():
            if ep_num not in data.get("episodes", {}):
                data["episodes"][ep_num] = path
                added_ass += 1

        # Attach videos only to project episodes. Unrelated media in the folder
        # must not create phantom rows in the project.
        if "video_paths" not in data:
            data["video_paths"] = {}

        for ep_num in data.get("episodes", {}):
            path = self._find_replacement_path(
                found["video"], ep_num, None
            )
            if path and ep_num not in data["video_paths"]:
                data["video_paths"][ep_num] = path
                added_video += 1

        logger.info(
            f"Batch imported: {added_ass} ASS, {added_video} video"
        )

        return added_ass, added_video
