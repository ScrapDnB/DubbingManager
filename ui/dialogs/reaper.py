"""Reaper export dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCheckBox,
    QDialogButtonBox
)
import os
from typing import Tuple, Optional


class ReaperExportDialog(QDialog):
    """Reaper Export Dialog dialog."""

    def __init__(self, video_path: Optional[str], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки проекта Reaper")
        self.resize(350, 150)

        self._chk_video: QCheckBox
        self._chk_regions: QCheckBox
        self._button_box: QDialogButtonBox
        self._init_ui(video_path)

    def _init_ui(self, video_path: Optional[str]) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        layout.addWidget(QLabel("Выберите компоненты для экспорта:"))

        self._chk_video = QCheckBox("Добавить дорожку с видео")
        self._chk_regions = QCheckBox("Создать регионы (реплики с текстом)")

        # Internal implementation detail
        has_video: bool = bool(video_path and os.path.exists(video_path))
        if has_video:
            self._chk_video.setChecked(True)
            self._chk_video.setText(
                f"Добавить видео ({os.path.basename(video_path)})"
            )
        else:
            self._chk_video.setChecked(False)
            self._chk_video.setEnabled(False)
            self._chk_video.setText("Видео не найдено (опция недоступна)")

        self._chk_regions.setChecked(True)

        layout.addWidget(self._chk_video)
        layout.addWidget(self._chk_regions)

        # Internal implementation detail
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def get_options(self) -> Tuple[bool, bool]:
        """Return options."""
        return self._chk_video.isChecked(), self._chk_regions.isChecked()