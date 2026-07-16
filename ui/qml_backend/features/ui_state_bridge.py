"""Persistent UI state shared by QML windows and file dialogs."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QSettings, QStandardPaths, QUrl, Slot


def _local_path(path_or_url: str) -> str:
    value = str(path_or_url or "")
    url = QUrl(value)
    return url.toLocalFile() if url.isLocalFile() else value


class UiStateBridge(QObject):
    """Keep non-project UI preferences outside the application data model."""

    def __init__(
        self,
        settings: Optional[QSettings] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings or QSettings(
            "DubbingTools",
            "Dubbing Manager",
        )

    @Slot(str, result=QUrl)
    def folderUrl(self, category: str) -> QUrl:
        key = self._folder_key(category)
        stored = str(self._settings.value(key, "") or "")
        if stored and Path(stored).is_dir():
            return QUrl.fromLocalFile(stored)
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        fallback = documents or str(Path.home())
        return QUrl.fromLocalFile(fallback)

    @Slot(str, result=str)
    def localPath(self, path_or_url: str) -> str:
        return _local_path(path_or_url)

    @Slot(str, str)
    def rememberFile(self, category: str, path_or_url: str) -> None:
        path = _local_path(path_or_url)
        if not path:
            return
        self._remember_folder(category, Path(path).expanduser().parent)

    @Slot(str, str)
    def rememberFolder(self, category: str, path_or_url: str) -> None:
        path = _local_path(path_or_url)
        if path:
            self._remember_folder(category, Path(path).expanduser())

    @Slot(str, int, result=int)
    def intValue(self, key: str, default: int) -> int:
        try:
            return int(self._settings.value(self._state_key(key), default))
        except (TypeError, ValueError):
            return int(default)

    @Slot(str, bool, result=bool)
    def boolValue(self, key: str, default: bool) -> bool:
        value = self._settings.value(self._state_key(key), default)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @Slot(str, int)
    def setIntValue(self, key: str, value: int) -> None:
        self._settings.setValue(self._state_key(key), int(value))

    @Slot(str, bool)
    def setBoolValue(self, key: str, value: bool) -> None:
        self._settings.setValue(self._state_key(key), bool(value))

    def _remember_folder(self, category: str, folder: Path) -> None:
        if not folder.is_dir():
            return
        self._settings.setValue(
            self._folder_key(category),
            str(folder.resolve()),
        )

    @staticmethod
    def _folder_key(category: str) -> str:
        name = str(category or "general").strip() or "general"
        return f"fileDialogs/{name}"

    @staticmethod
    def _state_key(key: str) -> str:
        name = str(key or "general").strip() or "general"
        return f"ui/{name}"
