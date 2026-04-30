"""Диалог импорта DOCX файлов с гибкой настройкой колонок"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox,
    QHeaderView, QWidget, QFrame, QLineEdit
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from typing import Dict, List, Any, Optional
import logging

from config.constants import (
    DOCX_IMPORT_DIALOG_HEIGHT,
    DOCX_IMPORT_DIALOG_WIDTH,
)
from services.docx_import_service import (
    DocxImportService, COLUMN_TYPES, DEFAULT_COLUMN_MAPPING, DEFAULT_TIME_SEPARATORS
)
from services.global_settings_service import GlobalSettingsService
from utils.helpers import customize_table

logger = logging.getLogger(__name__)


class DocxImportDialog(QDialog):
    """Диалог импорта DOCX файлов с настройкой маппинга колонок"""

    def __init__(self, parent=None, file_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Импорт DOCX - Настройка колонок")
        self.setMinimumSize(DOCX_IMPORT_DIALOG_WIDTH, DOCX_IMPORT_DIALOG_HEIGHT)

        self.docx_service = DocxImportService()
        self.global_settings_service = GlobalSettingsService()
        self.global_settings = self._load_global_settings(parent)
        self.saved_config = self.global_settings.get("docx_import_config", {})
        self.current_tables: List[List[List[str]]] = []  # Все таблицы
        self.current_table_idx: int = 0  # Индекс текущей таблицы
        self.current_rows: List[List[str]] = []  # Текущая таблица
        self.current_mapping: Dict[str, Optional[int]] = DEFAULT_COLUMN_MAPPING.copy()
        self.available_columns: List[int] = []
        self.time_separators: List[str] = self.saved_config.get(
            "time_separators",
            DEFAULT_TIME_SEPARATORS.copy()
        )
        self.file_path: Optional[str] = file_path

        self._init_ui()
        
        # Если передан файл, загружаем его
        if file_path:
            self._load_file(file_path)

    def _load_global_settings(self, parent) -> Dict[str, Any]:
        """Получить глобальные настройки из родителя или файла."""
        if parent is not None and hasattr(parent, "global_settings"):
            return parent.global_settings
        return self.global_settings_service.load_settings()

    def _init_ui(self) -> None:
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Верхняя панель с выбором файла
        top_panel = self._create_top_panel()
        layout.addLayout(top_panel)

        # Панель маппинга колонок
        mapping_widget = self._create_mapping_panel()
        layout.addWidget(mapping_widget)

        # Панель предпросмотра (внизу)
        preview_widget = self._create_preview_panel()
        layout.addWidget(preview_widget)

        # Нижняя панель с кнопками
        bottom_panel = self._create_bottom_panel()
        layout.addLayout(bottom_panel)

    def _create_top_panel(self) -> QVBoxLayout:
        """Создание верхней панели с выбором файла"""
        layout = QHBoxLayout()

        # Метка файла
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.file_label)

        layout.addStretch()

        # Переключатель таблиц (скрыт по умолчанию)
        self.table_selector_label = QLabel("Таблица:")
        self.table_selector_label.setVisible(False)
        layout.addWidget(self.table_selector_label)

        self.table_selector = QComboBox()
        self.table_selector.setMinimumWidth(200)
        self.table_selector.currentIndexChanged.connect(self._on_table_changed)
        self.table_selector.setVisible(False)
        layout.addWidget(self.table_selector)

        # Кнопка выбора файла
        self.select_btn = QPushButton("📁 Выбрать DOCX")
        self.select_btn.clicked.connect(self._select_file)
        layout.addWidget(self.select_btn)

        # Кнопка автоопределения
        self.auto_detect_btn = QPushButton("🔍 Автоопределение")
        self.auto_detect_btn.clicked.connect(self._auto_detect_columns)
        layout.addWidget(self.auto_detect_btn)

        return layout

    def _create_mapping_panel(self) -> QWidget:
        """Создание панели маппинга колонок"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        title = QLabel("📋 Настройка колонок")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        self.mapping_hint = QLabel(
            "Используются последние сохранённые настройки. "
            "Если структура таблицы другая, нажмите «Автоопределение» или поправьте колонки вручную."
        )
        self.mapping_hint.setWordWrap(True)
        self.mapping_hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.mapping_hint)

        # Настройка разделителей
        separator_widget = self._create_separator_widget()
        layout.addWidget(separator_widget)

        # Сетка маппинга
        self.mapping_grid = QGridLayout()
        self.mapping_grid.setSpacing(8)

        # Заголовки колонок
        self.mapping_grid.addWidget(QLabel("Поле"), 0, 0)
        self.mapping_grid.addWidget(QLabel("Колонка"), 0, 1)

        # Комбобоксы для каждого типа
        self.mapping_combos: Dict[str, QComboBox] = {}
        row = 1

        for col_type, col_name in COLUMN_TYPES.items():
            label = QLabel(col_name)
            combo = QComboBox()
            combo.addItem("Не использовать", None)
            combo.currentIndexChanged.connect(self._on_mapping_changed)
            self.mapping_combos[col_type] = combo

            self.mapping_grid.addWidget(label, row, 0)
            self.mapping_grid.addWidget(combo, row, 1)
            row += 1

        layout.addLayout(self.mapping_grid)
        layout.addStretch()

        return widget

    def _create_separator_widget(self) -> QWidget:
        """Создание виджета настройки разделителей тайминга"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)

        layout.addWidget(QLabel("⚙️ Разделители тайминга:"))

        # Поле ввода разделителей
        self.separator_edit = QLineEdit()
        self.separator_edit.setPlaceholderText("- | – — / \\t")
        self.separator_edit.setText(" ".join(self.time_separators))
        self.separator_edit.setFixedWidth(200)
        self.separator_edit.textChanged.connect(self._on_separators_changed)
        layout.addWidget(self.separator_edit)

        info_label = QLabel("Пример: 00:00:01,000 - 00:00:03,000")
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info_label)

        layout.addStretch()

        return widget

    def _create_preview_panel(self) -> QWidget:
        """Создание панели предпросмотра"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        title = QLabel("👁️ Предпросмотр")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        info_label = QLabel(
            "Данные будут импортированы в следующем виде:"
        )
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)

        # Таблица предпросмотра
        self.preview_table = QTableWidget()
        customize_table(self.preview_table)
        self.preview_table.setColumnCount(6)
        self.preview_table.setHorizontalHeaderLabels([
            "Персонаж", "Тайминг (начало)", "Тайминг (конец)",
            "Тайминг (вместе)", "Текст", "Статус"
        ])
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.preview_table.setMinimumHeight(200)

        layout.addWidget(self.preview_table)

        # Статистика
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.stats_label)

        return widget

    def _create_bottom_panel(self) -> QHBoxLayout:
        """Создание нижней панели с кнопками"""
        layout = QHBoxLayout()
        layout.addStretch()

        # Кнопка импорта всех таблиц (видна только если таблиц > 1)
        self.import_all_btn = QPushButton("✅ Импортировать все таблицы")
        self.import_all_btn.clicked.connect(self._import_all_tables)
        self.import_all_btn.setVisible(False)
        layout.addWidget(self.import_all_btn)

        # Кнопка импорта текущей таблицы
        self.import_btn = QPushButton("✅ Импортировать")
        self.import_btn.clicked.connect(self._import_data)
        self.import_btn.setEnabled(False)
        layout.addWidget(self.import_btn)

        # Кнопка отмены
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        return layout

    @Slot()
    def _select_file(self) -> None:
        """Выбор DOCX файла"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите DOCX файл", "", "DOCX Files (*.docx)"
        )

        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        """Загрузка DOCX файла"""
        try:
            self.current_tables = self.docx_service.extract_tables_from_docx(path)

            if not self.current_tables:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не удалось извлечь таблицу из файла.\n"
                    "Убедитесь, что файл содержит таблицу."
                )
                return

            self.current_table_idx = 0
            self.current_rows = self.current_tables[0]

            self.file_label.setText(f"📄 {path.split('/')[-1]}")
            self.import_btn.setEnabled(True)

            # Обновляем доступные колонки
            self.available_columns = self.docx_service.get_available_columns(self.current_rows)

            # Заполняем комбобоксы
            self._update_mapping_combos()

            self._apply_saved_mapping_or_auto_detect()

            # Если таблиц больше одной, показываем переключатель
            if len(self.current_tables) > 1:
                self._show_table_selector()

        except Exception as e:
            logger.error(f"Error loading DOCX: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка загрузки файла: {e}"
            )

    def _show_table_selector(self) -> None:
        """Показать переключатель таблиц"""
        self.table_selector.blockSignals(True)
        self.table_selector.clear()
        
        for i in range(len(self.current_tables)):
            # Пытаемся определить название таблицы по первой ячейке или заголовку
            table_name = f"Таблица {i + 1}"
            if self.current_tables[i] and self.current_tables[i][0]:
                # Используем первую ячейку заголовка как название
                first_cell = self.current_tables[i][0][0] if self.current_tables[i][0] else ""
                if first_cell:
                    table_name = f"{i + 1}. {first_cell[:30]}..."
            self.table_selector.addItem(table_name, i)
        
        self.table_selector.setCurrentIndex(0)
        self.table_selector_label.setVisible(True)
        self.table_selector.setVisible(True)
        self.import_all_btn.setVisible(True)  # Показываем кнопку импорта всех таблиц
        self.table_selector.blockSignals(False)

    @Slot()
    def _on_table_changed(self) -> None:
        """Обработчик переключения таблицы"""
        idx = self.table_selector.currentData()
        if idx is not None and 0 <= idx < len(self.current_tables):
            self.current_table_idx = idx
            self.current_rows = self.current_tables[idx]
            
            # Обновляем доступные колонки
            self.available_columns = self.docx_service.get_available_columns(self.current_rows)
            
            # Заполняем комбобоксы
            self._update_mapping_combos()
            
            self._apply_saved_mapping_or_auto_detect()

    def _update_mapping_combos(self) -> None:
        """Обновление комбобоксов маппинга"""
        for combo in self.mapping_combos.values():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Не использовать", None)

            for col_idx in self.available_columns:
                # Показываем заголовок колонки если есть
                header = ""
                if self.current_rows and col_idx < len(self.current_rows[0]):
                    header = self.current_rows[0][col_idx]

                if header:
                    combo.addItem(f"Колонка {col_idx}: {header}", col_idx)
                else:
                    combo.addItem(f"Колонка {col_idx}", col_idx)

            combo.blockSignals(False)

    def _apply_saved_mapping_or_auto_detect(self) -> None:
        """Применить сохранённый маппинг, если он подходит к таблице."""
        saved_mapping = self.saved_config.get("mapping", {})
        if self._mapping_is_usable(saved_mapping):
            self.current_mapping = DEFAULT_COLUMN_MAPPING.copy()
            self.current_mapping.update(saved_mapping)
            self._apply_mapping_to_combos(self.current_mapping)
            self.mapping_hint.setText(
                "Применены последние сохранённые настройки колонок."
            )
            self._update_preview()
            return

        self._auto_detect_columns()

    def _mapping_is_usable(self, mapping: Dict[str, Optional[int]]) -> bool:
        """Проверить, можно ли применить маппинг к текущей таблице."""
        if not mapping or mapping.get("text") is None:
            return False

        available = set(self.available_columns)
        for col_idx in mapping.values():
            if col_idx is not None and col_idx not in available:
                return False
        return True

    def _apply_mapping_to_combos(
        self,
        mapping: Dict[str, Optional[int]]
    ) -> None:
        """Показать маппинг в комбобоксах."""
        for col_type, combo in self.mapping_combos.items():
            combo.blockSignals(True)
            col_idx = mapping.get(col_type)
            if col_idx is not None:
                for i in range(combo.count()):
                    if combo.itemData(i) == col_idx:
                        combo.setCurrentIndex(i)
                        break
                else:
                    combo.setCurrentIndex(0)
            else:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)

    @Slot()
    def _auto_detect_columns(self) -> None:
        """Автоопределение колонок"""
        if not self.current_rows:
            return

        detected = self.docx_service.detect_columns(self.current_rows)
        self.current_mapping = detected

        self._apply_mapping_to_combos(detected)
        self.mapping_hint.setText("Колонки определены автоматически.")

        # Обновляем предпросмотр
        self._update_preview()

    @Slot()
    def _on_mapping_changed(self) -> None:
        """Обработчик изменения маппинга"""
        # Сохраняем текущий маппинг
        for col_type, combo in self.mapping_combos.items():
            self.current_mapping[col_type] = combo.currentData()

        # Обновляем предпросмотр
        self._update_preview()

    @Slot()
    def _on_separators_changed(self) -> None:
        """Обработчик изменения разделителей"""
        text = self.separator_edit.text().strip()
        if text:
            # Разделяем по пробелам и фильтруем пустые
            separators = [s.strip() for s in text.split() if s.strip()]
            if separators:
                self.time_separators = separators
                self.docx_service.set_time_separators(self.time_separators)
                # Обновляем предпросмотр
                self._update_preview()

    def _update_preview(self) -> None:
        """Обновление таблицы предпросмотра"""
        if not self.current_rows:
            return

        self.preview_table.setRowCount(0)

        # Получаем данные для предпросмотра
        preview_data = self.docx_service.get_preview_data(
            self.current_rows, self.current_mapping, limit=20
        )

        valid_count = 0
        invalid_count = 0

        for row_data in preview_data:
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)

            mapped = row_data.get('mapped', {})
            raw = row_data.get('raw', [])

            # Персонаж
            char = mapped.get('character', '')
            char_item = QTableWidgetItem(char or '—')
            if not char:
                char_item.setBackground(Qt.lightGray)
            self.preview_table.setItem(row, 0, char_item)

            # Тайминг начало
            time_start = mapped.get('time_start', '')
            time_start_parsed = row_data.get('time_start_parsed')
            if time_start_parsed is not None:
                time_start_item = QTableWidgetItem(f"{time_start} ({time_start_parsed:.2f}s)")
            else:
                time_start_item = QTableWidgetItem(time_start or '—')
                if not time_start:
                    time_start_item.setBackground(Qt.lightGray)
            self.preview_table.setItem(row, 1, time_start_item)

            # Тайминг конец
            time_end = mapped.get('time_end', '')
            time_end_parsed = row_data.get('time_end_parsed')
            if time_end_parsed is not None:
                time_end_item = QTableWidgetItem(f"{time_end} ({time_end_parsed:.2f}s)")
            else:
                time_end_item = QTableWidgetItem(time_end or '—')
                if not time_end:
                    time_end_item.setBackground(Qt.lightGray)
            self.preview_table.setItem(row, 2, time_end_item)

            # Тайминг вместе (split)
            time_split = mapped.get('time_split', '')
            time_split_start = row_data.get('time_split_start_parsed')
            time_split_end = row_data.get('time_split_end_parsed')
            if time_split_start is not None and time_split_end is not None:
                time_split_item = QTableWidgetItem(f"{time_split} ({time_split_start:.2f}s - {time_split_end:.2f}s)")
            else:
                time_split_item = QTableWidgetItem(time_split or '—')
                if not time_split:
                    time_split_item.setBackground(Qt.lightGray)
            self.preview_table.setItem(row, 3, time_split_item)

            # Текст
            text = mapped.get('text', '')
            text_item = QTableWidgetItem(text or '—')
            if not text:
                text_item.setBackground(Qt.lightGray)
                invalid_count += 1
            else:
                valid_count += 1
            self.preview_table.setItem(row, 4, text_item)

            # Статус
            status = "✓" if text else "⚠ Нет текста"
            status_item = QTableWidgetItem(status)
            if not text:
                status_item.setBackground(Qt.yellow)
            self.preview_table.setItem(row, 5, status_item)

        # Обновляем статистику
        total = len(preview_data)
        self.stats_label.setText(
            f"Показано: {total} | Корректных: {valid_count} | Проблемных: {invalid_count}"
        )

    @Slot()
    def _import_data(self) -> None:
        """Импорт данных текущей таблицы"""
        if not self.current_rows:
            return

        # Финальная проверка маппинга
        if self.current_mapping.get('text') is None:
            QMessageBox.warning(
                self, "Ошибка",
                "Необходимо указать колонку с текстом фразы."
            )
            return

        try:
            # Парсим данные
            stats, lines = self.docx_service.parse_with_mapping(
                self.current_rows, self.current_mapping
            )

            if not lines:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не удалось извлечь данные из файла."
                )
                return

            self._save_current_import_settings()

            # Возвращаем результат для одной таблицы
            self.result_data = {
                'stats': stats,
                'lines': lines,
                'source_path': self.file_path,
                'mapping': self.current_mapping,
                'tables_count': 1
            }
            self.accept()

        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка парсинга данных: {e}"
            )

    @Slot()
    def _import_all_tables(self) -> None:
        """Импорт всех таблиц"""
        if not self.current_tables:
            return

        # Финальная проверка маппинга
        if self.current_mapping.get('text') is None:
            QMessageBox.warning(
                self, "Ошибка",
                "Необходимо указать колонку с текстом фразы."
            )
            return

        try:
            # Парсим все таблицы
            all_lines = []
            all_stats = []

            for table_idx, table_rows in enumerate(self.current_tables):
                stats, lines = self.docx_service.parse_with_mapping(
                    table_rows, self.current_mapping
                )
                all_lines.extend(lines)
                all_stats.extend(stats)
                logger.info(f"Table {table_idx + 1}: {len(lines)} lines")

            if not all_lines:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не удалось извлечь данные из файла."
                )
                return

            self._save_current_import_settings()

            # Возвращаем результат для всех таблиц
            self.result_data = {
                'stats': all_stats,
                'lines': all_lines,
                'source_path': self.file_path,
                'mapping': self.current_mapping,
                'tables_count': len(self.current_tables)
            }
            self.accept()

        except Exception as e:
            logger.error(f"Error parsing DOCX tables: {e}")
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка парсинга данных: {e}"
            )

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Получение результата импорта"""
        return getattr(self, 'result_data', None)

    def _save_current_import_settings(self) -> None:
        """Сохранить маппинг DOCX для следующих импортов."""
        config = {
            "mapping": self.current_mapping.copy(),
            "time_separators": self.time_separators.copy(),
        }

        parent = self.parent()
        if parent is not None and hasattr(parent, "global_settings_service"):
            parent.global_settings.setdefault("docx_import_config", {}).update(config)
            parent.global_settings_service.update_docx_import_config(config)
            parent.global_settings_service.save_settings(parent.global_settings)
            return

        self.global_settings.setdefault("docx_import_config", {}).update(config)
        self.global_settings_service.update_docx_import_config(config)
        self.global_settings_service.save_settings(self.global_settings)
