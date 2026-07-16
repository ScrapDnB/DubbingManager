"""Shared state and command execution for QML feature bridges."""

from typing import Any, Dict, Optional, Set

from PySide6.QtCore import QObject, Signal

from core.commands import UndoStack
from services.project_service import ProjectService


class ProjectSession(QObject):
    """Own the open project and publish targeted domain changes."""

    projectReplaced = Signal()
    currentEpisodeChanged = Signal()
    domainChanged = Signal(str)
    dirtyChanged = Signal()
    undoStateChanged = Signal()

    def __init__(
        self,
        project_service: ProjectService,
        project_data: Dict[str, Any],
        undo_stack: Optional[UndoStack] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.project_service = project_service
        self.undo_stack = undo_stack or UndoStack()
        self.undo_stack.on_change(self.undoStateChanged.emit)
        self._project_data = project_data
        self._current_episode = ""
        self._edit_backups_created: Set[str] = set()

    @property
    def data(self) -> Dict[str, Any]:
        return self._project_data

    @property
    def current_episode(self) -> str:
        return self._current_episode

    @current_episode.setter
    def current_episode(self, episode: str) -> None:
        episode = str(episode or "")
        if episode == self._current_episode:
            return
        self._current_episode = episode
        self.currentEpisodeChanged.emit()

    def replace_project(
        self,
        project_data: Dict[str, Any],
        current_episode: str = "",
    ) -> None:
        self._project_data = project_data
        self._current_episode = str(current_episode or "")
        self._edit_backups_created.clear()
        self.projectReplaced.emit()
        self.currentEpisodeChanged.emit()

    def execute(self, command, domain: str = "project") -> None:
        self.undo_stack.push(command)
        self.mark_dirty()
        self.domainChanged.emit(domain)

    def ensure_edit_backup(self, scope: str) -> bool:
        """Create one full-project backup before the first edit in a scope."""
        scope = str(scope or "project")
        if scope in self._edit_backups_created:
            return True
        if not self.project_service.create_backup(
            self._project_data,
            f"editing_{scope}",
        ):
            return False
        self._edit_backups_created.add(scope)
        return True

    def mark_dirty(self) -> None:
        if self.project_service.is_dirty:
            return
        self.project_service.is_dirty = True
        self.dirtyChanged.emit()

    def notify_changed(self, domain: str) -> None:
        self.domainChanged.emit(str(domain or "project"))
