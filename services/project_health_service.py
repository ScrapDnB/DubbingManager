"""Project health diagnostics."""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.assignment_service import get_actor_for_character


@dataclass(frozen=True)
class ProjectHealthIssue:
    """Project Health Issue class."""

    severity: str
    category: str
    message: str
    episode: Optional[str] = None
    path: Optional[str] = None


class ProjectHealthService:
    """Project Health Service implementation."""

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"

    def check_project(self, project_data: Dict[str, Any]) -> List[ProjectHealthIssue]:
        """Return project health issues."""
        issues: List[ProjectHealthIssue] = []

        episodes = project_data.get("episodes", {})
        episode_texts = project_data.get("episode_texts", {})
        video_paths = project_data.get("video_paths", {})

        all_episode_nums = sorted(
            set(episodes) | set(episode_texts) | set(video_paths),
            key=self._episode_sort_key
        )

        if not all_episode_nums:
            issues.append(ProjectHealthIssue(
                self.SEVERITY_WARNING,
                "Проект",
                "В проекте нет серий."
            ))
            return issues

        for ep_num in all_episode_nums:
            source_path = episodes.get(ep_num)
            text_path = episode_texts.get(ep_num)
            video_path = video_paths.get(ep_num)

            self._check_source_file(issues, ep_num, source_path, text_path)
            lines = self._check_working_text(issues, ep_num, text_path, source_path)
            self._check_video_file(issues, ep_num, video_path)

            if lines:
                self._check_lines(issues, project_data, ep_num, lines)

        return issues

    def get_summary(self, issues: List[ProjectHealthIssue]) -> Dict[str, int]:
        """Count issues by severity."""
        return {
            "errors": sum(1 for item in issues if item.severity == self.SEVERITY_ERROR),
            "warnings": sum(1 for item in issues if item.severity == self.SEVERITY_WARNING),
            "info": sum(1 for item in issues if item.severity == self.SEVERITY_INFO),
            "total": len(issues),
        }

    def _check_source_file(
        self,
        issues: List[ProjectHealthIssue],
        ep_num: str,
        source_path: Optional[str],
        text_path: Optional[str]
    ) -> None:
        if not source_path:
            if not text_path:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_ERROR,
                    "Текст",
                    "Не указан ни исходный файл, ни рабочий текст.",
                    ep_num
                ))
            return

        if not os.path.exists(source_path):
            severity = self.SEVERITY_WARNING if text_path else self.SEVERITY_ERROR
            issues.append(ProjectHealthIssue(
                severity,
                "Файлы",
                "Исходный файл серии не найден.",
                ep_num,
                source_path
            ))

    def _check_working_text(
        self,
        issues: List[ProjectHealthIssue],
        ep_num: str,
        text_path: Optional[str],
        source_path: Optional[str]
    ) -> List[Dict[str, Any]]:
        if not text_path:
            if source_path:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_WARNING,
                    "Рабочий текст",
                    "Рабочий JSON ещё не создан.",
                    ep_num,
                    source_path
                ))
            return []

        if not os.path.exists(text_path):
            issues.append(ProjectHealthIssue(
                self.SEVERITY_ERROR,
                "Рабочий текст",
                "Рабочий JSON указан, но файл не найден.",
                ep_num,
                text_path
            ))
            return []

        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(ProjectHealthIssue(
                self.SEVERITY_ERROR,
                "Рабочий текст",
                f"Не удалось прочитать рабочий JSON: {exc}",
                ep_num,
                text_path
            ))
            return []

        lines = payload.get("lines")
        if not isinstance(lines, list):
            issues.append(ProjectHealthIssue(
                self.SEVERITY_ERROR,
                "Рабочий текст",
                "В рабочем JSON нет списка lines.",
                ep_num,
                text_path
            ))
            return []

        if not lines:
            issues.append(ProjectHealthIssue(
                self.SEVERITY_WARNING,
                "Рабочий текст",
                "В рабочем тексте нет реплик.",
                ep_num,
                text_path
            ))

        return lines

    def _check_video_file(
        self,
        issues: List[ProjectHealthIssue],
        ep_num: str,
        video_path: Optional[str]
    ) -> None:
        if video_path and not os.path.exists(video_path):
            issues.append(ProjectHealthIssue(
                self.SEVERITY_WARNING,
                "Видео",
                "Видео файл не найден.",
                ep_num,
                video_path
            ))

    def _check_lines(
        self,
        issues: List[ProjectHealthIssue],
        project_data: Dict[str, Any],
        ep_num: str,
        lines: List[Dict[str, Any]]
    ) -> None:
        missing_actor_chars = set()

        for index, line in enumerate(lines, start=1):
            text = str(line.get("text") or "").strip()
            character = str(
                line.get("display_character") or line.get("character") or ""
            ).strip()
            start = self._as_float(line.get("start", line.get("s")))
            end = self._as_float(line.get("end", line.get("e")))
            line_label = f"Реплика {index}"

            if not text:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_WARNING,
                    "Реплики",
                    f"{line_label}: пустой текст.",
                    ep_num
                ))

            if not character:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_WARNING,
                    "Реплики",
                    f"{line_label}: не указан персонаж.",
                    ep_num
                ))
            elif get_actor_for_character(project_data, character, ep_num) is None:
                missing_actor_chars.add(character)

            if start is None or end is None:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_WARNING,
                    "Тайминг",
                    f"{line_label}: некорректный тайминг.",
                    ep_num
                ))
            elif end <= start:
                issues.append(ProjectHealthIssue(
                    self.SEVERITY_ERROR,
                    "Тайминг",
                    f"{line_label}: конец фразы не позже начала.",
                    ep_num
                ))

        for character in sorted(missing_actor_chars):
            issues.append(ProjectHealthIssue(
                self.SEVERITY_INFO,
                "Назначения",
                f"Персонаж без назначенного актёра: {character}",
                ep_num
            ))

    def _as_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _episode_sort_key(self, value: Any) -> tuple:
        text = str(value)
        if text.isdigit():
            return (0, int(text))
        return (1, text.lower())
