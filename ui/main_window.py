"""Главное окно приложения"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QColorDialog, QComboBox, QLabel, QHeaderView, QInputDialog,
    QFrame, QSpinBox, QLineEdit, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox, QSlider,
    QAbstractItemView, QStackedWidget, QDoubleSpinBox, QRadioButton,
    QGridLayout, QScrollArea, QSplitter, QSizePolicy, QToolBar,
    QDialogButtonBox, QTextEdit, QDialog
)
from PySide6.QtGui import QColor, QFont, QAction, QKeySequence, QPen, QBrush
from PySide6.QtCore import Qt, QUrl, QTimer, Signal, QRectF, QEvent, Slot
from typing import Dict, List, Any, Optional, Set, Tuple
import json
import re
import os
import sys
from datetime import datetime
import logging

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("openpyxl not available - Excel export disabled")

from config.constants import (
    MY_PALETTE,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    MAIN_WINDOW_WIDTH,
    MAIN_WINDOW_HEIGHT,
    ACTOR_PANEL_WIDTH,
    TOOLS_SIDEBAR_WIDTH,
    SEARCH_EDIT_WIDTH,
    EPISODE_COMBO_MIN_WIDTH,
    BTN_RENAME_WIDTH,
    BTN_SAVE_ASS_WIDTH,
    TABLE_ROW_HEIGHT,
    VIDEO_BTN_WIDTH,
    AUTOSAVE_INTERVAL_MS,
)
from utils.helpers import (
    ass_time_to_seconds,
    format_seconds_to_tc,
    hex_to_rgba_string,
    customize_table,
    wrap_widget,
    log_exception
)
from services import (
    ProjectService,
    EpisodeService,
    ActorService,
    ExportService
)
from .dialogs import (
    ActorFilterDialog,
    PrompterColorDialog,
    CustomColorDialog,
    ExportSettingsDialog,
    ReaperExportDialog,
    ActorRolesDialog,
    GlobalSearchDialog,
    SummaryDialog
)
from .teleprompter import TeleprompterWindow
from .preview import HtmlLivePreview
from .video import VideoPreviewWindow

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Главное окно приложения Dubbing Manager"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dubbing Manager")
        self.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        self.setAcceptDrops(True)

        # Сервисы
        self.project_service = ProjectService()
        self.episode_service = EpisodeService()
        self.actor_service = ActorService()

        # Состояние
        self.current_project_path: Optional[str] = None
        self.is_dirty = False
        self.sort_col = 1
        self.sort_desc = True
        self.preview_window: Optional[HtmlLivePreview] = None
        self.teleprompter_window: Optional[TeleprompterWindow] = None

        # Данные проекта
        self.data: Dict[str, Any] = self.project_service.create_new_project("Новый проект")
        
        self.current_ep_stats: List[Dict[str, Any]] = []
        self.character_names_changed: Dict[str, bool] = {}

        self._init_ui()
        self.update_window_title()

        # Автосохранение
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._on_autosave_timer)
        self.autosave_timer.start(AUTOSAVE_INTERVAL_MS)

    def _on_autosave_timer(self) -> None:
        """Обработчик таймера автосохранения"""
        self.project_service.auto_save(self.data)
    
    def _init_ui(self) -> None:
        """Инициализация интерфейса"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # Левая панель - актёры
        self._init_actor_panel(main_layout)
        
        # Правая панель - основной контент
        self._init_main_panel(main_layout)
    
    def _init_actor_panel(self, main_layout) -> None:
        """Инициализация панели актёров"""
        left_panel = QVBoxLayout()
        left_widget = QFrame()
        left_widget.setFixedWidth(ACTOR_PANEL_WIDTH)
        left_widget.setFrameShape(QFrame.StyledPanel)
        left_widget.setLayout(left_panel)

        left_panel.addWidget(QLabel("<b>БАЗА АКТЕРОВ</b>"))

        self.actor_table = QTableWidget(0, 3)
        self.actor_table.setHorizontalHeaderLabels(
            ["Актер", "Роли", "Цвет"]
        )
        customize_table(self.actor_table)
        
        # Настройка ширины колонок
        header = self.actor_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Актер - занимает всё место
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Роли - фиксированная
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # Цвет - фиксированная ширина
        self.actor_table.setColumnWidth(1, 100)
        self.actor_table.setColumnWidth(2, 60)               # Узкая колонка для цвета
        
        self.actor_table.itemChanged.connect(self.on_actor_renamed)
        self.actor_table.cellClicked.connect(self.on_actor_cell_clicked)
        left_panel.addWidget(self.actor_table)
        
        btn_add = QPushButton("+ Актер")
        btn_add.clicked.connect(self.add_actor_dialog)
        left_panel.addWidget(btn_add)
        
        btn_sum = QPushButton("📋 Сводный отчет проекта")
        btn_sum.clicked.connect(self.show_project_summary)
        left_panel.addWidget(btn_sum)
        
        main_layout.addWidget(left_widget)
    
    def _init_main_panel(self, main_layout) -> None:
        """Инициализация основной панели"""
        right_panel = QVBoxLayout()
        
        # Верхняя строка - проект
        self._init_project_bar(right_panel)
        
        # Управление сериями
        self._init_episode_controls(right_panel)
        
        # Центральная область - таблица + инструменты
        self._init_center_area(right_panel)
        
        # Нижняя панель - экспорт
        self._init_bottom_panel(right_panel)
        
        main_layout.addLayout(right_panel)
    
    def _init_project_bar(self, layout) -> None:
        """Инициализация панели проекта"""
        top = QHBoxLayout()
        
        self.proj_edit = QLineEdit()
        self.proj_edit.textChanged.connect(self.on_project_name_changed)
        top.addWidget(QLabel("Проект:"))
        top.addWidget(self.proj_edit)
        
        btn_load = QPushButton("Открыть")
        btn_load.clicked.connect(self.load_project_dialog)
        top.addWidget(btn_load)
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_project)
        top.addWidget(btn_save)
        
        btn_copy = QPushButton("Копия")
        btn_copy.clicked.connect(self.save_project_as)
        top.addWidget(btn_copy)
        
        layout.addLayout(top)
    
    def _init_episode_controls(self, layout) -> None:
        """Инициализация управления сериями"""
        ep_ctrl = QHBoxLayout()

        self.ep_combo = QComboBox()
        self.ep_combo.setMinimumWidth(EPISODE_COMBO_MIN_WIDTH)
        self.ep_combo.currentIndexChanged.connect(self.change_episode)
        ep_ctrl.addWidget(QLabel("Серия:"))
        ep_ctrl.addWidget(self.ep_combo)

        btn_ass = QPushButton("+ .ASS")
        btn_ass.clicked.connect(lambda: self.import_ass())
        ep_ctrl.addWidget(btn_ass)

        btn_ren = QPushButton("✎")
        btn_ren.setFixedWidth(BTN_RENAME_WIDTH)
        btn_ren.clicked.connect(self.rename_episode)
        ep_ctrl.addWidget(btn_ren)

        btn_del = QPushButton("🗑")
        btn_del.setFixedWidth(BTN_RENAME_WIDTH)
        btn_del.clicked.connect(self.delete_episode_dialog)
        ep_ctrl.addWidget(btn_del)

        self.btn_save_ass = QPushButton()
        self.btn_save_ass.setFixedWidth(BTN_SAVE_ASS_WIDTH)
        self.btn_save_ass.clicked.connect(self.save_current_episode_ass)
        self.update_save_ass_button()
        ep_ctrl.addWidget(self.btn_save_ass)
        
        btn_vid = QPushButton("🎬 Видео")
        btn_vid.clicked.connect(self.set_episode_video)
        ep_ctrl.addWidget(btn_vid)
        
        btn_ep_sum = QPushButton("📊 Отчет серии")
        btn_ep_sum.clicked.connect(self.show_episode_summary)
        ep_ctrl.addWidget(btn_ep_sum)
        
        ep_ctrl.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.setFixedWidth(SEARCH_EDIT_WIDTH)
        self.search_edit.textChanged.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.search_edit)
        
        btn_glob_search = QPushButton("🔍 Глобальный поиск")
        btn_glob_search.clicked.connect(self.open_global_search)
        ep_ctrl.addWidget(btn_glob_search)
        
        self.filter_unassigned = QCheckBox("Пустые")
        self.filter_unassigned.toggled.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.filter_unassigned)
        
        layout.addLayout(ep_ctrl)
    
    def _init_center_area(self, layout) -> None:
        """Инициализация центральной области"""
        middle_layout = QHBoxLayout()
        
        # Стек таблиц
        self.table_stack = QStackedWidget()
        
        self.main_table = QTableWidget(0, 6)
        self.main_table.setHorizontalHeaderLabels([
            "Персонаж", "Строчек", "Колец", "Слов", "Актер", "📺"
        ])
        customize_table(self.main_table)
        self.main_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.main_table.horizontalHeader().setSectionsClickable(True)
        self.main_table.horizontalHeader().sectionClicked.connect(
            self.on_header_clicked
        )
        self.main_table.itemChanged.connect(
            self.on_character_name_changed
        )
        
        self.missing_file_widget = QWidget()
        mf_lay = QVBoxLayout(self.missing_file_widget)
        
        self.lbl_missing = QLabel("ФАЙЛ НЕ НАЙДЕН")
        self.lbl_missing.setStyleSheet(
            "color: red; font-weight: bold;"
        )
        self.lbl_missing.setAlignment(Qt.AlignCenter)
        
        btn_relink = QPushButton("Найти...")
        btn_relink.clicked.connect(self.relink_file)
        
        mf_lay.addStretch()
        mf_lay.addWidget(self.lbl_missing)
        mf_lay.addWidget(btn_relink)
        mf_lay.addStretch()
        
        self.table_stack.addWidget(self.main_table)
        self.table_stack.addWidget(self.missing_file_widget)
        
        middle_layout.addWidget(self.table_stack, stretch=1)
        
        # Панель инструментов
        self._init_tools_sidebar(middle_layout)
        
        layout.addLayout(middle_layout)
    
    def _init_tools_sidebar(self, layout) -> None:
        """Инициализация панели инструментов"""
        tools_sidebar_widget = QWidget()
        tools_sidebar_widget.setFixedWidth(TOOLS_SIDEBAR_WIDTH)
        tools_sidebar_layout = QVBoxLayout(tools_sidebar_widget)
        tools_sidebar_layout.setContentsMargins(5, 0, 0, 0)
        
        tools_sidebar_layout.addWidget(QLabel("<b>Инструменты:</b>"))
        
        btn_all_v = QPushButton("📺 Просмотр серии")
        btn_all_v.clicked.connect(lambda: self.open_preview(None))
        tools_sidebar_layout.addWidget(btn_all_v)
        
        btn_live_html = QPushButton("📃 Монтажный лист")
        btn_live_html.clicked.connect(self.open_live_preview)
        tools_sidebar_layout.addWidget(btn_live_html)

        btn_prompter = QPushButton("🎤 Телесуфлёр")
        btn_prompter.clicked.connect(self.open_teleprompter)
        tools_sidebar_layout.addWidget(btn_prompter)

        btn_reaper = QPushButton("🎹 Reaper RPP")
        btn_reaper.clicked.connect(self.export_to_reaper_rpp)
        tools_sidebar_layout.addWidget(btn_reaper)
        
        tools_sidebar_layout.addStretch()
        layout.addWidget(tools_sidebar_widget)
    
    def _init_bottom_panel(self, layout) -> None:
        """Инициализация нижней панели"""
        bottom_panel = QHBoxLayout()
        
        btn_bulk = QPushButton("⚡ Назначить выделенным")
        btn_bulk.clicked.connect(self.bulk_assign_actor)
        bottom_panel.addWidget(btn_bulk)
        
        bottom_panel.addStretch()
        
        exp_group = QGroupBox("Экспорт")
        exp_lay = QHBoxLayout(exp_group)
        exp_lay.setContentsMargins(5, 5, 5, 5)

        btn_cfg = QPushButton("⚙ Настройки")
        btn_cfg.clicked.connect(self.open_export_settings)
        bottom_panel.addWidget(btn_cfg)

        self.chk_exp_html = QCheckBox("Лист")
        self.chk_exp_html.setChecked(True)
        
        self.chk_exp_xls = QCheckBox("Excel")
        
        self.radio_cur = QRadioButton("Текущая")
        self.radio_cur.setChecked(True)
        
        self.radio_all = QRadioButton("Все")
        
        self.btn_run_export = QPushButton("ЭКСПОРТ")
        self.btn_run_export.clicked.connect(self.run_unified_export)
        
        exp_lay.addWidget(self.chk_exp_html)
        exp_lay.addWidget(self.chk_exp_xls)
        exp_lay.addSpacing(10)
        exp_lay.addWidget(self.radio_cur)
        exp_lay.addWidget(self.radio_all)
        exp_lay.addSpacing(10)
        exp_lay.addWidget(self.btn_run_export)
        
        bottom_panel.addWidget(exp_group)
        layout.addLayout(bottom_panel)
    
    # === Методы работы с данными ===

    def set_dirty(self, dirty: bool = True) -> None:
        """Установка флага изменений"""
        self.project_service.set_dirty(dirty)
        self.update_window_title()

    def update_window_title(self) -> None:
        """Обновление заголовка окна"""
        self.setWindowTitle(self.project_service.get_window_title(self.data))
    
    def maybe_save(self) -> bool:
        """Проверка необходимости сохранения"""
        if not self.project_service.is_dirty:
            return True

        reply = QMessageBox.question(
            self,
            "Сохранить?",
            "Сохранить изменения?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )

        if reply == QMessageBox.Save:
            return self.save_project()
        return reply == QMessageBox.Discard

    def on_project_name_changed(self, text: str) -> None:
        """Изменение имени проекта"""
        self.project_service.set_project_name(self.data, text)

    # === Методы работы с персонажами ===
    
    def on_character_name_changed(self, item: QTableWidgetItem) -> None:
        """Обработчик изменения имени персонажа"""
        if item.column() != 0:
            return

        ep = self.ep_combo.currentData()
        if not ep:
            return

        old_name = item.data(Qt.UserRole)
        new_name = item.text().strip()

        if new_name == old_name or not new_name:
            return

        # Обновляем global_map
        if old_name in self.data["global_map"]:
            aid = self.data["global_map"][old_name]
            del self.data["global_map"][old_name]
            self.data["global_map"][new_name] = aid

        # Обновляем загруженные эпизоды
        if ep in self.data.get("loaded_episodes", {}):
            for line in self.data["loaded_episodes"][ep]:
                if line['char'] == old_name:
                    line['char'] = new_name

        # Обновляем статистику эпизода
        for stat in self.current_ep_stats:
            if stat["name"] == old_name:
                stat["name"] = new_name
                break

        # Инвалидируем кэш в episode_service
        self.episode_service.invalidate_episode(ep)

        # Обновляем открытые окна (телесуфлёр, превью)
        self._refresh_open_windows(ep)

        item.setData(Qt.UserRole, new_name)
        self.character_names_changed[ep] = True
        self.update_save_ass_button()
        self.refresh_actor_list()
        self.set_dirty(True)

    def _refresh_open_windows(self, ep: str) -> None:
        """Обновление открытых окон после изменений"""
        # Обновляем превью, если открыто
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.update_preview()

        # Обновляем телесуфлёр, если открыт
        if hasattr(self, 'teleprompter_window') and self.teleprompter_window:
            self.teleprompter_window.refresh_episode_data()
    
    def update_save_ass_button(self) -> None:
        """Обновление кнопки сохранения ASS"""
        ep = self.ep_combo.currentData()
        has_changes = self.character_names_changed.get(ep, False)
        
        if has_changes:
            self.btn_save_ass.setText("💾 Сохранить*")
            self.btn_save_ass.setStyleSheet(
                "font-weight: bold; color: red;"
            )
        else:
            self.btn_save_ass.setText("💾 Сохранить")
            self.btn_save_ass.setStyleSheet("")
    
    def save_current_episode_ass(self) -> None:
        """Сохранение текущей серии в ASS"""
        ep = self.ep_combo.currentData()
        if not ep:
            QMessageBox.warning(self, "Ошибка", "Выберите серию.")
            return
        
        if self.save_episode_to_ass(ep):
            self.character_names_changed[ep] = False
            self.update_save_ass_button()
            QMessageBox.information(
                self, "Успех", f"Серия {ep} сохранена в ASS файл."
            )
    
    # === Методы работы с проектом ===
    
    def save_project(self) -> bool:
        """Сохранение проекта"""
        if self.current_project_path:
            return self.project_service.save_project(self.data)
        return self.save_project_as()

    def save_project_as(self) -> bool:
        """Сохранение проекта как..."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить", "", "*.json"
        )
        if path:
            result = self.project_service.save_project_as(self.data, path)
            self.current_project_path = self.project_service.current_project_path
            self.update_window_title()
            return result
        return False
    
    def load_project_dialog(self) -> None:
        """Диалог загрузки проекта"""
        if self.maybe_save():
            path, _ = QFileDialog.getOpenFileName(
                self, "Открыть", "", "*.json"
            )
            if path:
                self._load_from_path(path)
    
    def _load_from_path(self, path: str) -> None:
        """Загрузка из файла"""
        try:
            self.data = self.project_service.load_project(path)
            self.current_project_path = self.project_service.current_project_path

            # Временно отключаем сигнал, чтобы не устанавливать dirty флаг
            self.proj_edit.blockSignals(True)
            self.proj_edit.setText(self.project_service.get_project_name(self.data))
            self.proj_edit.blockSignals(False)

            self.refresh_actor_list()
            self.update_ep_list()
            logger.info(f"Project loaded from {path}")

        except Exception as e:
            log_exception(logger, "Load failed", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить проект: {e}"
            )
    
    # === Методы работы с сериями ===
    
    def on_header_clicked(self, index: int) -> None:
        """Клик по заголовку таблицы"""
        if index > 3:
            return
        if self.sort_col == index:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = index
            self.sort_desc = True
        self.refresh_main_table()
    
    def add_actor_dialog(self) -> None:
        """Диалог добавления актёра"""
        name, ok = QInputDialog.getText(self, "Новый актер", "Имя:")
        if ok and name:
            dialog = CustomColorDialog(self)
            if dialog.exec():
                actor_id = self.actor_service.add_actor(
                    self.data["actors"],
                    name,
                    dialog.selected_color
                )
                self.refresh_actor_list()
                self.refresh_main_table()
                self.set_dirty()

    def on_actor_cell_clicked(self, row: int, col: int) -> None:
        """Клик по ячейке актёра"""
        if col == 2:  # Колонка "Цвет"
            item = self.actor_table.item(row, 0)
            if item:
                aid = item.data(Qt.UserRole)
                dialog = CustomColorDialog(self)
                if dialog.exec():
                    if dialog.selected_color and aid:
                        self.actor_service.update_actor_color(
                            self.data["actors"], aid, dialog.selected_color
                        )
                        self.refresh_actor_list()
                        self.refresh_main_table()
                        self.set_dirty()

    def on_actor_renamed(self, item: QTableWidgetItem) -> None:
        """Переименование актёра"""
        aid = item.data(Qt.UserRole)
        if aid:
            self.actor_service.rename_actor(
                self.data["actors"], aid, item.text()
            )
            self.refresh_main_table()
            self.set_dirty()

    def bulk_assign_actor(self) -> None:
        """Массовое назначение актёра"""
        selected = self.main_table.selectionModel().selectedRows()
        if not selected:
            return

        names = ["- Удалить -"] + [
            a["name"] for a in self.data["actors"].values()
        ]
        ids = [None] + list(self.data["actors"].keys())

        name, ok = QInputDialog.getItem(
            self, "Назначить", "Актер:", names, 0, False
        )

        if ok:
            aid = ids[names.index(name)]
            characters = [
                self.main_table.item(idx.row(), 0).text()
                for idx in selected
            ]
            self.actor_service.bulk_assign_actors(
                self.data["global_map"], characters, aid
            )
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()
    
    def set_episode_video(self) -> None:
        """Установка видео для серии"""
        ep = self.ep_combo.currentData()
        if ep:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Видео",
                "",
                "Video (*.mp4 *.mkv *.avi *.mov)"
            )
            if path:
                if "video_paths" not in self.data:
                    self.data["video_paths"] = {}
                self.data["video_paths"][ep] = path
                self.set_dirty()
    
    def change_episode(self) -> None:
        """Смена серии"""
        ep = self.ep_combo.currentData()
        if not ep:
            return

        path = self.data["episodes"].get(ep)
        if path and os.path.exists(path):
            self.table_stack.setCurrentIndex(0)
            self._parse_episode(ep, path)
            self.get_episode_lines(ep)
            self.refresh_main_table()
            self.update_save_ass_button()
        else:
            self.table_stack.setCurrentIndex(1)

    def _parse_episode(self, ep: str, path: str) -> None:
        """Парсинг эпизода и получение статистики"""
        stats, _ = self.episode_service.parse_ass_file(path)
        self.current_ep_stats = stats

    def import_ass(self, paths: Optional[List[str]] = None) -> None:
        """Импорт ASS файлов"""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "ASS", "", "*.ass"
            )

        if paths:
            for path in paths:
                numbers = re.findall(r'\d+', os.path.basename(path))
                num = " ".join(numbers) or "1"

                name, ok = QInputDialog.getText(
                    self,
                    "Ep",
                    f"Ep for {os.path.basename(path)}:",
                    text=num
                )

                if ok and name:
                    self.data["episodes"][name] = path
                    self._parse_episode(name, path)
                    self.set_dirty()

            self.update_ep_list()
    
    def relink_file(self) -> None:
        """Перепривязка файла"""
        ep = self.ep_combo.currentData()
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл", "", "*.ass"
        )
        if path:
            self.data["episodes"][ep] = path
            self.change_episode()
            self.set_dirty()

    def update_map(
        self, 
        char_name: str, 
        combo: QComboBox
    ) -> None:
        """Обновление маппинга персонаж-актёр"""
        aid = combo.currentData()
        if aid:
            self.data["global_map"][char_name] = aid
        elif char_name in self.data["global_map"]:
            del self.data["global_map"][char_name]
        
        self.refresh_actor_list()
        self.set_dirty(True)
    
    def refresh_main_table(self) -> None:
        """Обновление главной таблицы"""
        self.main_table.blockSignals(True)
        self.main_table.setRowCount(0)
        
        query = self.search_edit.text().lower()
        only_unassigned = self.filter_unassigned.isChecked()
        
        keys = ["name", "lines", "rings", "words"]
        sorted_stats = sorted(
            self.current_ep_stats,
            key=lambda x: x[keys[self.sort_col]],
            reverse=self.sort_desc
        )
        
        for stat in sorted_stats:
            if query and query not in stat["name"].lower():
                continue
            
            is_assigned = stat["name"] in self.data["global_map"]
            if only_unassigned and is_assigned:
                continue
            
            row = self.main_table.rowCount()
            self.main_table.insertRow(row)
            
            name_item = QTableWidgetItem(stat["name"])
            name_item.setFlags(
                name_item.flags() | Qt.ItemIsEditable
            )
            name_item.setData(Qt.UserRole, stat["name"])
            self.main_table.setItem(row, 0, name_item)
            
            self.main_table.setItem(
                row, 1, QTableWidgetItem(str(stat["lines"]))
            )
            self.main_table.setItem(
                row, 2, QTableWidgetItem(str(stat["rings"]))
            )
            self.main_table.setItem(
                row, 3, QTableWidgetItem(str(stat["words"]))
            )
            
            combo = QComboBox()
            combo.addItem("-", None)
            for aid, info in self.data["actors"].items():
                combo.addItem(info["name"], aid)
            
            if is_assigned:
                combo.setCurrentIndex(
                    combo.findData(
                        self.data["global_map"][stat["name"]]
                    )
                )
            
            combo.currentIndexChanged.connect(
                lambda _, c=stat["name"], b=combo: self.update_map(c, b)
            )
            self.main_table.setCellWidget(row, 4, combo)

            btn = QPushButton("📺")
            btn.setFixedWidth(VIDEO_BTN_WIDTH)
            btn.clicked.connect(
                lambda ch=False, c=stat["name"]: self.open_preview(c)
            )
            self.main_table.setCellWidget(row, 5, wrap_widget(btn))
        
        self.main_table.blockSignals(False)
    
    def refresh_actor_list(self) -> None:
        """Обновление списка актёров"""
        self.actor_table.blockSignals(True)
        self.actor_table.setRowCount(0)

        actor_roles: Dict[str, List[str]] = {
            aid: [] for aid in self.data["actors"]
        }

        for char, aid in self.data["global_map"].items():
            if aid in actor_roles:
                actor_roles[aid].append(char)

        for aid, info in self.data["actors"].items():
            row = self.actor_table.rowCount()
            self.actor_table.insertRow(row)

            # Колонка 0: Актер
            item = QTableWidgetItem(info["name"])
            item.setData(Qt.UserRole, aid)
            self.actor_table.setItem(row, 0, item)

            # Колонка 1: Роли
            btn = QPushButton(f"Роли ({len(actor_roles[aid])})")
            btn.clicked.connect(
                lambda _, a=aid, n=info["name"], r=actor_roles[aid]:
                self.edit_roles(a, n, r)
            )
            self.actor_table.setCellWidget(row, 1, wrap_widget(btn))

            # Колонка 2: Цвет
            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(info["color"]))
            self.actor_table.setItem(row, 2, color_item)

        self.actor_table.blockSignals(False)
    
    def rename_episode(self) -> None:
        """Переименование серии"""
        old = self.ep_combo.currentData()
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=str(old)
        )
        if ok and new_name:
            self.data["episodes"][new_name] = (
                self.data["episodes"].pop(old)
            )
            self.update_ep_list(new_name)
            self.set_dirty()

    def delete_episode_dialog(self) -> None:
        """Диалог удаления серии"""
        ep = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Нет серий для удаления.")
            return

        reply = QMessageBox.question(
            self,
            "Удаление серии",
            f"Вы уверены, что хотите удалить серию {ep}?\n\n"
            f"Это удалит серию из проекта, но не затронет .ass файл.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.delete_episode(ep)

    def delete_episode(self, ep: str) -> None:
        """Удаление серии из проекта"""
        # Удаляем из словаря эпизодов
        self.data["episodes"].pop(ep, None)

        # Удаляем путь к видео
        self.data["video_paths"].pop(ep, None)

        # Удаляем из кэша загруженных эпизодов
        if "loaded_episodes" in self.data:
            self.data["loaded_episodes"].pop(ep, None)

        # Очищаем кэш в episode service
        self.episode_service.invalidate_episode(ep)

        # Обновляем список серий
        self.update_ep_list()

        # Сохраняем изменения
        self.set_dirty()

        QMessageBox.information(
            self, "Готово", f"Серия {ep} удалена из проекта."
        )
    
    def update_ep_list(self, select: Optional[str] = None) -> None:
        """Обновление списка серий"""
        self.ep_combo.blockSignals(True)
        self.ep_combo.clear()
        
        for ep in sorted(
            self.data["episodes"].keys(),
            key=lambda x: int(x) if x.isdigit() else 0
        ):
            self.ep_combo.addItem(f"Серия {ep}", ep)
        
        if select:
            self.ep_combo.setCurrentIndex(
                self.ep_combo.findData(select)
            )
        elif self.ep_combo.count() > 0:
            self.ep_combo.setCurrentIndex(0)
        
        self.ep_combo.blockSignals(False)
        self.change_episode()
    
    # === Экспорт ===
    
    def run_unified_export(self) -> None:
        """Запуск экспорта"""
        do_html = self.chk_exp_html.isChecked()
        do_xls = self.chk_exp_xls.isChecked()
        
        if not (do_html or do_xls):
            return
        
        is_all = self.radio_all.isChecked()
        
        if is_all:
            episodes = self.data["episodes"]
        else:
            ep = self.ep_combo.currentData()
            episodes = {ep: self.data["episodes"].get(ep)}

        if not episodes or None in episodes.values():
            return

        if is_all or (do_html and do_xls):
            dest = QFileDialog.getExistingDirectory(
                self, "Выберите папку"
            )
            if dest:
                self._execute_batch_export(
                    episodes, do_html, do_xls, dest
                )
        else:
            ep = list(episodes.keys())[0]
            if do_html:
                self.export_to_html(ep)
            else:
                self.export_to_excel(ep)

    def _execute_batch_export(
        self,
        episodes: Dict[str, str],
        do_html: bool,
        do_xls: bool,
        folder: str
    ) -> None:
        """Пакетный экспорт через ExportService"""
        export_service = ExportService(self.data)
        success, message = export_service.export_batch(
            episodes=episodes,
            get_lines_callback=self.get_episode_lines,
            do_html=do_html,
            do_xls=do_xls,
            folder=folder
        )

        if success:
            logger.info(message)
        else:
            QMessageBox.critical(self, "Ошибка экспорта", message)

    def _create_excel_book(
        self,
        ep: str,
        processed: List[Dict[str, Any]],
        cfg: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Создание Excel книги (устарело, использовать ExportService)"""
        export_service = ExportService(self.data)
        return export_service.create_excel_book(ep, processed, cfg)

    def export_to_excel(self, ep: str) -> None:
        """Экспорт в Excel"""
        lines = self.get_episode_lines(ep)
        cfg = self.data["export_config"]

        export_service = ExportService(self.data)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", f"Script_{ep}.xlsx", "*.xlsx"
        )

        if path:
            success, message = export_service.export_to_excel(
                ep=ep, lines=lines, cfg=cfg, save_path=path
            )
            if success:
                if sys.platform == 'win32':
                    os.startfile(path)
                else:
                    os.system(f'open "{path}"')
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def export_to_html(self, ep: str) -> None:
        """Экспорт в HTML"""
        cfg = self.data["export_config"]
        lines = self.get_episode_lines(ep)

        export_service = ExportService(self.data)
        processed = export_service.process_merge_logic(lines, cfg)

        html = export_service.generate_html(
            ep,
            processed,
            cfg,
            cfg.get('highlight_ids_export'),
            layout_type=cfg.get('layout_type', 'Таблица'),
            is_editable=cfg.get('allow_edit', True)
        )

        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML", f"Script_{ep}.html", "*.html"
        )

        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)

            if sys.platform == 'darwin':
                os.system(f'open "{path}"')
            else:
                os.startfile(path)

    def save_episode_to_ass(
        self,
        ep_num: str,
        target_path: Optional[str] = None
    ) -> bool:
        """Сохранение серии в ASS"""
        mem_lines = self.get_episode_lines(ep_num)
        if not mem_lines:
            QMessageBox.warning(self, "Ошибка", "Нет данных.")
            return False

        success, message = self.episode_service.save_episode_to_ass(
            ep_num,
            self.data["episodes"],
            mem_lines,
            target_path
        )

        if not success:
            QMessageBox.warning(self, "Ошибка", message)

        return success
    
    
    
    # === Диалоги и окна ===
    
    def open_preview(self, char: Optional[str]) -> None:
        """Открытие предпросмотра видео"""
        ep = self.ep_combo.currentData()
        lines = self.get_episode_lines(ep)
        
        if char:
            lines = [l for l in lines if l['char'] == char]
        
        vp = self.data.get("video_paths", {}).get(ep)
        
        if not vp or not os.path.exists(vp):
            self.set_episode_video()
            vp = self.data.get("video_paths", {}).get(ep)
        
        if vp:
            VideoPreviewWindow(vp, lines, ep, self).exec()
    
    def get_episode_lines(self, ep: str) -> List[Dict[str, Any]]:
        """Получение строк серии"""
        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}

        if ep in self.data["loaded_episodes"]:
            return self.data["loaded_episodes"][ep]

        lines = self.episode_service.load_episode(ep, self.data["episodes"])

        if lines:
            self.data["loaded_episodes"][ep] = lines

        return lines
    
    def show_project_summary(self) -> None:
        """Показать сводку проекта"""
        SummaryDialog(self.data, None, self).exec()
    
    def show_episode_summary(self) -> None:
        """Показать сводку серии"""
        ep = self.ep_combo.currentData()
        if ep:
            SummaryDialog(self.data, ep, self).exec()
    
    def edit_roles(
        self,
        aid: str,
        name: str,
        roles: List[str]
    ) -> None:
        """Редактирование ролей актёра"""
        dialog = ActorRolesDialog(name, roles, self)
        if dialog.exec():
            new_roles = dialog.get_roles()
            self.actor_service.update_actor_roles(
                self.data["global_map"], aid, new_roles
            )
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()
    
    def open_export_settings(self) -> None:
        """Открытие настроек экспорта"""
        dialog = ExportSettingsDialog(
            self.data["export_config"], self
        )
        if dialog.exec():
            self.data["export_config"] = dialog.get_settings()
            self.change_episode()
            self.set_dirty()
    
    def open_global_search(self) -> None:
        """Открытие глобального поиска"""
        GlobalSearchDialog(self.data, self).exec()
    
    def open_live_preview(self) -> None:
        """Открытие живого предпросмотра"""
        ep = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Выберите серию.")
            return
        
        if self.preview_window is not None:
            self.preview_window.close()
        
        self.preview_window = HtmlLivePreview(self, ep)
        self.preview_window.show()
    
    def open_teleprompter(self) -> None:
        """Открытие телесуфлёра"""
        ep = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Выберите серию.")
            return
        
        if self.teleprompter_window is not None:
            self.teleprompter_window.close()
        
        self.teleprompter_window = TeleprompterWindow(self, ep)
        self.teleprompter_window.show()

    def export_to_reaper_rpp(self) -> None:
        """Экспорт в Reaper RPP"""
        ep_num = self.ep_combo.currentData()
        if not ep_num:
            QMessageBox.warning(self, "Ошибка", "Выберите серию.")
            return
        
        video_path = self.data["video_paths"].get(ep_num)
        dialog = ReaperExportDialog(video_path, self)
        
        if dialog.exec() != QDialog.Accepted:
            return
        
        use_video, use_regions = dialog.get_options()
        
        if use_video and video_path:
            video_path = os.path.abspath(video_path)
        
        default_name = (
            f"{self.data.get('project_name', 'Project')} - "
            f"Ep{ep_num}.rpp"
        )
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить RPP", default_name, "Reaper Project (*.rpp)"
        )
        if not save_path:
            return
        
        lines = self.get_episode_lines(ep_num)
        active_actor_ids: Set[str] = set()

        max_time = 600.0
        if lines:
            max_time = max(l['e'] for l in lines) + 600.0
            for line in lines:
                aid = self.data["global_map"].get(line['char'])
                if aid:
                    active_actor_ids.add(aid)

        export_service = ExportService(self.data)
        processed_lines = export_service.process_merge_logic(
            lines, self.data["export_config"]
        )
        
        rpp = []
        rpp.append('<REAPER_PROJECT 0.1 "7.0"')
        
        if use_regions:
            for i, line in enumerate(processed_lines):
                start = float(line['s'])
                end = float(line['e'])
                
                if (end - start) < 0.5:
                    end = start + 2.0
                
                char = line['char']
                safe_text = (
                    line['text']
                    .replace('"', "' ")
                    .replace('\n', ' ')
                    .strip()
                )
                label = f"{char}: {safe_text}"
                
                aid = self.data["global_map"].get(char)
                color_int = 0
                if aid and aid in self.data["actors"]:
                    color_int = int(
                        self.hex_to_reaper_color(
                            self.data["actors"][aid]["color"]
                        )
                    )
                
                rpp.append(
                    f'  MARKER {i+1} {start:.4f} "{label}" '
                    f'1 {color_int} {end:.4f}'
                )
        
        if use_video and video_path:
            rpp.append('   <TRACK')
            rpp.append('    NAME "VIDEO"')
            rpp.append('     <ITEM')
            rpp.append('      POSITION 0.0')
            rpp.append('      LOOP 0')
            rpp.append(f'      LENGTH {max_time:.4f}')
            rpp.append('       <SOURCE VIDEO')
            rpp.append(f'        FILE "{video_path}"')
            rpp.append('       >')
            rpp.append('     >')
            rpp.append('   >')
        
        sorted_actors = []
        for aid in active_actor_ids:
            if aid in self.data["actors"]:
                sorted_actors.append(self.data["actors"][aid])
        sorted_actors.sort(key=lambda x: x['name'])
        
        for actor in sorted_actors:
            color_int = int(
                self.hex_to_reaper_color(actor['color'])
            )
            rpp.append('   <TRACK')
            rpp.append(f'    NAME "{actor["name"]}"')
            rpp.append(f'    PEAKCOL {color_int}')
            rpp.append('    REC 0')
            rpp.append('    SHOWINMIX 1')
            rpp.append('   >')
        
        rpp.append('>')
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(rpp))
            
            reply = QMessageBox.question(
                self,
                "Готово",
                "Проект создан. Открыть в Reaper?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if sys.platform == 'win32':
                    os.startfile(save_path)
                elif sys.platform == 'darwin':
                    os.system(f'open "{save_path}"')
                else:
                    os.system(f'xdg-open "{save_path}"')
        except Exception as e:
            log_exception(logger, "Error saving RPP", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить: {e}"
            )
    
    def hex_to_reaper_color(self, hex_color: str) -> int:
        """Конвертация HEX в BGR Int для Reaper"""
        if not hex_color or not hex_color.startswith('#'):
            return 0
        
        color = QColor(hex_color)
        if not color.isValid():
            return 0
        
        val = 0x01000000 | (
            color.blue() << 16
        ) | (
            color.green() << 8
        ) | color.red()
        
        return val
    
    def switch_to_episode(self, ep_num: str) -> None:
        """Переключение на серию"""
        index = self.ep_combo.findData(ep_num)
        if index >= 0:
            self.ep_combo.setCurrentIndex(index)
    
    # === Drag & Drop ===
    
    def dragEnterEvent(self, event) -> None:
        """Обработка входа перетаскивания"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event) -> None:
        """Обработка сброса файлов"""
        files = [
            url.toLocalFile() 
            for url in event.mimeData().urls()
        ]
        
        ass_files = [f for f in files if f.endswith('.ass')]
        json_files = [f for f in files if f.endswith('.json')]
        
        if json_files and self.maybe_save():
            self._load_from_path(json_files[0])
        elif ass_files:
            self.import_ass(ass_files)
    
    def closeEvent(self, event) -> None:
        """Закрытие приложения"""
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()