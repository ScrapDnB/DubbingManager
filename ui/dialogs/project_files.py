"""Диалог отображения структуры файлов проекта"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog,
    QHeaderView, QDialogButtonBox
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from typing import Dict, List, Any, Optional, Tuple
import os

from services import ProjectFolderService


class ProjectFilesDialog(QDialog):
    """
    Диалог для просмотра структуры файлов проекта.
    
    Отображает:
    - Эпизоды и связанные с ними файлы (ASS, рабочий текст, видео)
    - Статус файлов (найден/не найден)
    - Пути к файлам
    - Возможность перепривязки файлов
    """

    def __init__(
        self,
        data: Dict[str, Any],
        parent=None
    ):
        super().__init__(parent)
        self.data = data
        self.folder_service = ProjectFolderService()
        
        self.setWindowTitle("Файлы проекта")
        self.resize(800, 600)
        
        self._init_ui()
        self._populate_tree()

    def _init_ui(self) -> None:
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header_label = QLabel("Структура файлов проекта")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Дерево файлов
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels([
            "Эпизод", "Файл", "Статус", "Путь"
        ])
        self.file_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.file_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.file_tree.header().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.file_tree.header().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.file_tree.setAlternatingRowColors(True)
        layout.addWidget(self.file_tree)
        
        # Статистика
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #666;")
        layout.addWidget(self.lbl_stats)
        
        # Кнопки действий
        btn_layout = QHBoxLayout()
        
        self.btn_relink = QPushButton("📁 Перепривязать...")
        self.btn_relink.setToolTip("Найти файл вручную")
        self.btn_relink.clicked.connect(self._relink_selected)
        self.btn_relink.setEnabled(False)
        btn_layout.addWidget(self.btn_relink)

        self.btn_regenerate_text = QPushButton("📝 Создать из субтитров...")
        self.btn_regenerate_text.setToolTip("Пересоздать рабочий текст из ASS/SRT")
        self.btn_regenerate_text.clicked.connect(self._regenerate_selected_text)
        self.btn_regenerate_text.setEnabled(False)
        btn_layout.addWidget(self.btn_regenerate_text)
        
        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(self.btn_refresh)
        
        btn_layout.addStretch()
        
        # Кнопка закрытия
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        # Подключение сигнала выбора элемента
        self.file_tree.itemSelectionChanged.connect(
            self._on_selection_changed
        )

    def _get_file_status(
        self,
        path: str
    ) -> Tuple[str, QColor]:
        """
        Получение статуса файла.
        
        Returns:
            Tuple(текст статуса, цвет)
        """
        if not path:
            return "Не указан", QColor("#999999")
        
        if os.path.exists(path):
            return "✓ Найден", QColor("#28a745")
        else:
            return "✗ Не найден", QColor("#dc3545")

    def _is_subtitle_source_path(self, path: Optional[str]) -> bool:
        """Проверить, похож ли путь на исходный файл субтитров."""
        return os.path.splitext(path or "")[1].lower() in {'.ass', '.srt'}

    def _get_working_text_status(
        self,
        ep_num: str,
        text_path: Optional[str],
        source_path: Optional[str]
    ) -> Tuple[str, QColor]:
        """Получить статус рабочего текста серии."""
        if text_path and os.path.exists(text_path):
            return "✓ Используется рабочий текст", QColor("#28a745")

        if text_path:
            return "✗ Рабочий текст потерян", QColor("#dc3545")

        if source_path and os.path.exists(source_path):
            return "○ Рабочий текст не создан", QColor("#e0a800")

        if source_path and self._is_subtitle_source_path(source_path):
            return "⚠ Файл субтитров не найден", QColor("#dc3545")

        return "○ Рабочий текст не указан", QColor("#999999")

    def _get_episode_text_source_status(
        self,
        ep_num: str,
        text_path: Optional[str],
        source_path: Optional[str]
    ) -> Tuple[str, QColor]:
        """Получить сводный статус источника текста серии."""
        if text_path and os.path.exists(text_path):
            return "Текст: рабочий JSON", QColor("#28a745")

        if text_path:
            return "Текст: рабочий JSON потерян", QColor("#dc3545")

        if source_path and os.path.exists(source_path):
            return "Текст: субтитры", QColor("#e0a800")

        if source_path and self._is_subtitle_source_path(source_path):
            return "Текст: источник потерян", QColor("#dc3545")

        return "Текст: не найден", QColor("#999999")

    def _populate_tree(self) -> None:
        """Заполнение дерева файлов"""
        self.file_tree.clear()
        
        episodes = self.data.get("episodes", {})
        episode_texts = self.data.get("episode_texts", {})
        video_paths = self.data.get("video_paths", {})
        project_folder = self.data.get("project_folder")
        
        # Получаем все номера эпизодов
        all_ep_nums = sorted(
            set(episodes.keys()) |
            set(episode_texts.keys()) |
            set(video_paths.keys()),
            key=lambda x: int(x) if x.isdigit() else 0
        )
        
        found_count = 0
        total_count = 0
        
        for ep_num in all_ep_nums:
            # Создаём элемент эпизода
            ep_item = QTreeWidgetItem([
                f"Серия {ep_num}",
                "",
                "",
                ""
            ])
            ep_item.setFont(0, QFont("", -1, QFont.Bold))
            ass_path = episodes.get(ep_num)
            text_path = episode_texts.get(ep_num)
            ep_status_text, ep_status_color = self._get_episode_text_source_status(
                ep_num,
                text_path,
                ass_path
            )
            ep_item.setText(2, ep_status_text)
            ep_item.setForeground(2, ep_status_color)
            
            # ASS файл
            if ass_path:
                total_count += 1
                status_text, status_color = self._get_file_status(ass_path)

                if status_text.startswith("✓"):
                    found_count += 1

                # Определяем тип файла по расширению
                file_ext = ".srt" if ass_path.lower().endswith('.srt') else ".ass"
                file_icon = "📄"
                
                ass_item = QTreeWidgetItem([
                    "",
                    f"{file_icon} Субтитры ({file_ext})",
                    status_text,
                    ass_path or ""
                ])
                ass_item.setForeground(2, status_color)
                ass_item.setData(3, Qt.UserRole, ("ass", ep_num))
                ep_item.addChild(ass_item)

            # Рабочий текст
            if text_path or ass_path:
                total_count += 1
                status_text, status_color = self._get_working_text_status(
                    ep_num,
                    text_path,
                    ass_path
                )

                if text_path and os.path.exists(text_path):
                    found_count += 1

                text_item = QTreeWidgetItem([
                    "",
                    "📝 Рабочий текст",
                    status_text,
                    text_path or ""
                ])
                text_item.setForeground(2, status_color)
                text_item.setData(3, Qt.UserRole, ("text", ep_num))
                ep_item.addChild(text_item)
            
            # Видео файл
            video_path = video_paths.get(ep_num)
            if video_path:
                total_count += 1
                status_text, status_color = self._get_file_status(video_path)
                
                if status_text.startswith("✓"):
                    found_count += 1
                
                video_item = QTreeWidgetItem([
                    "",
                    "🎬 Видео",
                    status_text,
                    video_path or ""
                ])
                video_item.setForeground(2, status_color)
                video_item.setData(3, Qt.UserRole, ("video", ep_num))
                ep_item.addChild(video_item)
            
            self.file_tree.addTopLevelItem(ep_item)
            ep_item.setExpanded(True)
        
        # Обновляем статистику
        missing_count = total_count - found_count
        self.lbl_stats.setText(
            f"Всего файлов: {total_count} | "
            f"✓ Найдено: {found_count} | "
            f"✗ Не найдено: {missing_count}"
        )
        
        # Разворачиваем все элементы
        self.file_tree.expandAll()

    def _on_selection_changed(self) -> None:
        """Обработчик изменения выбора"""
        selected_items = self.file_tree.selectedItems()
        
        # Кнопка перепривязки активна только для файлов
        if selected_items:
            item = selected_items[0]
            file_data = item.data(3, Qt.UserRole)
            has_data = file_data is not None
            self.btn_relink.setEnabled(has_data)
            self.btn_regenerate_text.setEnabled(
                bool(file_data and file_data[0] == "text")
            )
        else:
            self.btn_relink.setEnabled(False)
            self.btn_regenerate_text.setEnabled(False)

    def _relink_selected(self) -> None:
        """Перепривязка выбранного файла"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        file_data = item.data(3, Qt.UserRole)
        
        if not file_data:
            return
        
        file_type, ep_num = file_data
        
        # Определяем текущий путь и фильтр файлов
        if file_type == "ass":
            current_path = self.data.get("episodes", {}).get(ep_num)
            # Определяем расширение текущего файла
            if current_path and current_path.lower().endswith('.srt'):
                file_filter = "Subtitle Files (*.srt *.ass)"
                title = "Выберите файл субтитров"
            else:
                file_filter = "Subtitle Files (*.ass *.srt)"
                title = "Выберите файл субтитров"
        elif file_type == "text":
            current_path = self.data.get("episode_texts", {}).get(ep_num)
            file_filter = "Episode Text Files (*.json)"
            title = "Выберите рабочий текст эпизода"
        else:
            current_path = self.data.get("video_paths", {}).get(ep_num)
            file_filter = "Video Files (*.mp4 *.mkv *.avi *.mov *.m4v *.wmv)"
            title = "Выберите видео файл"
        
        # Открываем диалог
        path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            current_path or "",
            file_filter
        )
        
        if path:
            # Обновляем путь в данных проекта
            if file_type == "ass":
                self.data["episodes"][ep_num] = path
            elif file_type == "text":
                if "episode_texts" not in self.data:
                    self.data["episode_texts"] = {}
                self.data["episode_texts"][ep_num] = path
            else:
                if "video_paths" not in self.data:
                    self.data["video_paths"] = {}
                self.data["video_paths"][ep_num] = path
            
            # Обновляем дерево
            self._populate_tree()
            
            # Сигнал об изменении
            self.parent()._on_files_changed() if hasattr(self.parent(), '_on_files_changed') else None

    def _regenerate_selected_text(self) -> None:
        """Пересоздание рабочего текста из файла субтитров."""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        file_data = item.data(3, Qt.UserRole)
        if not file_data or file_data[0] != "text":
            return

        _, ep_num = file_data
        source_path = self.data.get("episodes", {}).get(ep_num)

        if not source_path or not os.path.exists(source_path):
            source_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите файл субтитров",
                source_path or "",
                "Subtitle Files (*.ass *.srt)"
            )
            if not source_path:
                return
            self.data.setdefault("episodes", {})[ep_num] = source_path

        parent = self.parent()
        if not parent or not hasattr(parent, "regenerate_episode_text"):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось пересоздать рабочий текст из этого окна."
            )
            return

        if parent.regenerate_episode_text(ep_num, source_path):
            self._populate_tree()
            if hasattr(parent, '_on_files_changed'):
                parent._on_files_changed()

    def _refresh(self) -> None:
        """Обновление дерева файлов"""
        self._populate_tree()
