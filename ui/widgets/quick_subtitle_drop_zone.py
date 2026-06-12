"""Drop zone widgets."""

import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class QuickSubtitleDropZone(QFrame):
    """Drop zone for quick subtitle-to-montage conversion."""

    filesDropped = Signal(list, bool)

    SUPPORTED_EXTENSIONS = {".ass", ".srt"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(92)
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            "Зажмите Option/Alt при перетаскивании, чтобы сначала открыть превью."
        )
        self.setStyleSheet(
            """
            QuickSubtitleDropZone {
                border: 1px dashed palette(placeholder-text);
                border-radius: 6px;
                background: transparent;
            }
            QuickSubtitleDropZone[dragActive="true"] {
                border: 2px solid palette(highlight);
                background: palette(alternate-base);
            }
            QLabel {
                color: palette(text);
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("Быстрый конвертер")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 600; color: palette(text);")
        layout.addWidget(title)

        hint = QLabel("Перетащите ASS или SRT\nМонтажные листы появятся рядом")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _set_drag_active(self, active: bool) -> None:
        """Update drop zone visual state."""
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _supported_files(self, event) -> List[str]:
        """Return supported local files from a drag event."""
        if not event.mimeData().hasUrls():
            return []

        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self.is_supported_path(path):
                files.append(path)
        return files

    @classmethod
    def is_supported_path(cls, path: str) -> bool:
        """Return True if path is a supported subtitle source."""
        return os.path.splitext(path)[1].lower() in cls.SUPPORTED_EXTENSIONS

    def dragEnterEvent(self, event) -> None:
        """Accept ASS/SRT files."""
        if self._supported_files(event):
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Keep drag accepted while hovering."""
        if self._supported_files(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Reset visual state when drag leaves."""
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event) -> None:
        """Emit dropped subtitle files."""
        files = self._supported_files(event)
        self._set_drag_active(False)
        if files:
            event.acceptProposedAction()
            preview_first = bool(event.keyboardModifiers() & Qt.AltModifier)
            self.filesDropped.emit(files, preview_first)
        else:
            event.ignore()
