"""Reaper export dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCheckBox,
    QDialogButtonBox, QFrame, QSizePolicy, QComboBox
)
import os
from typing import Any, Callable, Dict, Optional, Tuple
from utils.i18n import translate_source, translate_widget_tree


class ReaperExportDialog(QDialog):
    """Reaper Export Dialog dialog."""

    def __init__(
        self,
        video_path: Optional[str],
        parent: Optional[QDialog] = None,
        preview_provider: Optional[
            Callable[[bool, bool, bool, str], Dict[str, Any]]
        ] = None,
        source_markers_available: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки проекта Reaper")
        self.resize(460, 360)
        self._preview_provider = preview_provider
        self._source_markers_available = source_markers_available

        self._chk_video: QCheckBox
        self._chk_regions: QCheckBox
        self._chk_transliterate: QCheckBox
        self._combo_marker_mode: QComboBox
        self._combo_output_format: QComboBox
        self._preview_label: QLabel
        self._button_box: QDialogButtonBox
        self._has_video: bool = False
        self._init_ui(video_path)
        translate_widget_tree(self)

    def _init_ui(self, video_path: Optional[str]) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        layout.addWidget(QLabel("Выберите компоненты для экспорта:"))

        self._chk_video = QCheckBox("Добавить дорожку с видео")
        self._chk_regions = QCheckBox("Создать регионы (реплики с текстом)")
        self._chk_transliterate = QCheckBox(
            "Транслитерировать имена актёров"
        )
        self._chk_transliterate.setToolTip(
            "Имена дорожек актёров в RPP будут записаны латиницей. "
            "Имена персонажей и текст регионов не меняются."
        )
        self._combo_marker_mode = QComboBox()
        self._combo_marker_mode.addItem("Маркеры объединённых реплик", "merged")
        self._combo_marker_mode.addItem("Построчные маркеры из исходника", "source")
        if not self._source_markers_available:
            item = self._combo_marker_mode.model().item(1)
            if item is not None:
                item.setEnabled(False)
                item.setToolTip(
                    "В этом проекте нет точных исходных строк. "
                    "Пересоздайте рабочий текст из ASS/SRT, чтобы включить режим."
                )
        self._combo_marker_mode.setToolTip(
            "Построчный режим использует исходные строки, сохранённые в проекте "
            "при импорте ASS/SRT."
        )
        self._combo_output_format = QComboBox()
        self._combo_output_format.addItem("Проект Reaper (.rpp)", "rpp")
        self._combo_output_format.addItem("Только CSV с маркерами", "csv")

        self._has_video = bool(video_path and os.path.exists(video_path))
        if self._has_video:
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
        layout.addWidget(self._chk_transliterate)
        layout.addWidget(QLabel("Маркеры:"))
        layout.addWidget(self._combo_marker_mode)
        layout.addWidget(QLabel("Сохранить:"))
        layout.addWidget(self._combo_output_format)

        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.StyledPanel)
        preview_frame.setMinimumHeight(190)
        preview_frame.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.addWidget(QLabel("Предпросмотр:"))

        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._preview_label.setMinimumHeight(145)
        self._preview_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self._preview_label.setTextInteractionFlags(
            self._preview_label.textInteractionFlags() |
            Qt.TextSelectableByMouse
        )
        preview_layout.addWidget(self._preview_label, 1)
        layout.addWidget(preview_frame, 1)

        self._chk_video.toggled.connect(self._update_preview)
        self._chk_regions.toggled.connect(self._update_preview)
        self._chk_transliterate.toggled.connect(self._update_preview)
        self._combo_marker_mode.currentIndexChanged.connect(self._update_preview)
        self._combo_output_format.currentIndexChanged.connect(
            self._sync_output_options
        )
        self._update_preview()

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def get_options(self) -> Tuple[bool, bool, bool, str, str]:
        """Return options."""
        return (
            self._chk_video.isChecked(),
            self._chk_regions.isChecked(),
            self._chk_transliterate.isChecked(),
            self._combo_marker_mode.currentData(),
            self._combo_output_format.currentData(),
        )

    def _sync_output_options(self) -> None:
        """Disable RPP-only options for CSV-only export."""
        csv_only = self._combo_output_format.currentData() == "csv"
        self._chk_video.setEnabled(not csv_only and self._has_video)
        if csv_only:
            self._chk_video.setChecked(False)
        self._chk_transliterate.setEnabled(not csv_only)
        self._update_preview()

    def _update_preview(self) -> None:
        """Refresh the RPP preview summary."""
        if not self._preview_provider:
            self._preview_label.setText("Предпросмотр недоступен.")
            return

        preview = self._preview_provider(
            self._chk_video.isChecked(),
            self._chk_regions.isChecked(),
            self._chk_transliterate.isChecked(),
            self._combo_marker_mode.currentData()
        )
        self._preview_label.setText(self._format_preview(preview))

    def _format_preview(self, preview: Dict[str, Any]) -> str:
        actors = preview.get("actors", [])
        actor_text = ", ".join(actors[:8]) if actors else translate_source("нет")
        if len(actors) > 8:
            actor_text += f" {translate_source('и ещё')} {len(actors) - 8}"

        sample = preview.get("sample_regions", [])
        details = "\n".join(sample) if sample else translate_source(
            "Регионов не будет создано."
        )
        if len(sample) < preview.get("regions", 0):
            details += "\n..."

        warning = ""
        if preview.get("invalid_lines", 0):
            warning = (
                f"\n{translate_source('Внимание: реплик с некорректной длиной:')} "
                f"{preview['invalid_lines']}"
            )

        return (
            f"{translate_source('Регионов:')} {preview.get('regions', 0)}\n"
            f"{translate_source('Дорожек актёров:')} {preview.get('tracks', 0)}\n"
            f"{translate_source('Актёры:')} {actor_text}\n"
            f"{translate_source('Видео:')} "
            f"{translate_source('да' if preview.get('video') else 'нет')}"
            f"{warning}\n\n"
            f"{translate_source('Первые регионы:')}\n{details}"
        )
