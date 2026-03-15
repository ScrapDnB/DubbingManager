"""Контроллер управления актёрами"""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QPushButton, QWidget, QHBoxLayout
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from typing import Dict, List, Any, Optional, Callable

from services import ActorService
from utils.helpers import wrap_widget


class ActorController:
    """
    Контроллер для управления панелью актёров.
    
    Отвечает за:
    - Отображение списка актёров в таблице
    - Добавление/удаление/редактирование актёров
    - Назначение ролей актёрам
    - Цветовое кодирование актёров
    """

    def __init__(
        self,
        actor_table: QTableWidget,
        actor_service: ActorService,
        data_ref: Dict[str, Any],
        on_dirty_callback: Optional[Callable] = None,
        on_edit_roles_callback: Optional[Callable] = None,
        on_color_click_callback: Optional[Callable] = None
    ) -> None:
        self.actor_table: QTableWidget = actor_table
        self.actor_service: ActorService = actor_service
        self.data_ref: Dict[str, Any] = data_ref  # Ссылка на данные
        self.on_dirty_callback = on_dirty_callback
        self.on_edit_roles_callback = on_edit_roles_callback
        self.on_color_click_callback = on_color_click_callback
        
        self._setup_table()

    def _setup_table(self) -> None:
        """Настройка таблицы актёров"""
        self.actor_table.setHorizontalHeaderLabels(
            ["Актер", "Роли", "Цвет"]
        )
        self.actor_table.setShowGrid(False)
        self.actor_table.setAlternatingRowColors(True)
        self.actor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.actor_table.setFrameShape(QFrame.NoFrame)
        self.actor_table.verticalHeader().setVisible(False)
        self.actor_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.actor_table.setColumnWidth(1, 100)
        self.actor_table.setColumnWidth(2, 60)
        
        # Подключаем обработчик клика по ячейке (для цвета)
        self.actor_table.cellClicked.connect(self._on_cell_clicked)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Обработчик клика по ячейке"""
        if col == 2 and self.on_color_click_callback:  # Колонка "Цвет"
            item: Optional[QTableWidgetItem] = self.actor_table.item(row, 0)
            if item:
                aid: Optional[str] = item.data(Qt.UserRole)
                if aid:
                    self.on_color_click_callback(aid)

    def _find_actor_row(self, actor_id: str) -> Optional[int]:
        """Поиск строки актёра по ID"""
        for row in range(self.actor_table.rowCount()):
            item = self.actor_table.item(row, 0)
            if item and item.data(Qt.UserRole) == actor_id:
                return row
        return None

    def _get_actor_roles(self) -> Dict[str, List[str]]:
        """Получение списка ролей для всех актёров"""
        actor_roles: Dict[str, List[str]] = {
            aid: [] for aid in self.data_ref["actors"]
        }
        for char, aid in self.data_ref["global_map"].items():
            if aid in actor_roles:
                actor_roles[aid].append(char)
        return actor_roles

    def refresh(self) -> None:
        """Обновление списка актёров в таблице"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"ActorController.refresh: actors={len(self.data_ref.get('actors', {}))}, table={self.actor_table}")

        self.actor_table.blockSignals(True)
        self.actor_table.setRowCount(0)

        actor_roles = self._get_actor_roles()

        aid: str
        info: Dict[str, Any]
        for aid, info in self.data_ref["actors"].items():
            row: int = self.actor_table.rowCount()
            self.actor_table.insertRow(row)

            # Колонка 0: Актер
            item: QTableWidgetItem = QTableWidgetItem(info["name"])
            item.setData(Qt.UserRole, aid)
            self.actor_table.setItem(row, 0, item)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

            # Колонка 1: Роли (кнопка)
            btn: QPushButton = QPushButton(f"Роли ({len(actor_roles[aid])})")
            if self.on_edit_roles_callback:
                btn.clicked.connect(
                    lambda checked=False, a=aid, n=info["name"], r=actor_roles[aid]:
                    self.on_edit_roles_callback(a, n, r)
                )
            self.actor_table.setCellWidget(row, 1, wrap_widget(btn))

            # Колонка 2: Цвет
            color_item: QTableWidgetItem = QTableWidgetItem()
            color_item.setBackground(QColor(info["color"]))
            self.actor_table.setItem(row, 2, color_item)

        self.actor_table.blockSignals(False)
        logger.info(f"ActorController.refresh: loaded {self.actor_table.rowCount()} actors")

    def update_actor_color(self, actor_id: str, color: str) -> None:
        """Обновление цвета актёра (оптимизировано - обновляет только ячейку цвета)"""
        self.actor_service.update_actor_color(
            self.data_ref["actors"], actor_id, color
        )
        
        # Обновляем только ячейку цвета вместо полной перерисовки
        row = self._find_actor_row(actor_id)
        if row is not None:
            color_item = self.actor_table.item(row, 2)
            if color_item:
                color_item.setBackground(QColor(color))
            else:
                # Если ячейки нет, создаём её
                color_item = QTableWidgetItem()
                color_item.setBackground(QColor(color))
                self.actor_table.setItem(row, 2, color_item)
        
        self._mark_dirty()

    def rename_actor(self, actor_id: str, new_name: str) -> None:
        """Переименование актёра (оптимизировано - обновляет только ячейку имени)"""
        self.actor_service.rename_actor(
            self.data_ref["actors"], actor_id, new_name
        )
        
        # Обновляем только ячейку имени вместо полной перерисовки
        row = self._find_actor_row(actor_id)
        if row is not None:
            item = self.actor_table.item(row, 0)
            if item:
                item.setText(new_name)
        
        self._mark_dirty()

    def update_actor_roles(
        self,
        actor_id: str,
        new_roles: List[str]
    ) -> None:
        """Обновление ролей актёра (оптимизировано - обновляет только кнопку ролей)"""
        self.actor_service.update_actor_roles(
            self.data_ref["global_map"], actor_id, new_roles
        )
        
        # Обновляем только кнопку ролей вместо полной перерисовки
        row = self._find_actor_row(actor_id)
        if row is not None:
            btn_widget = self.actor_table.cellWidget(row, 1)
            if btn_widget:
                btn = btn_widget.findChild(QPushButton)
                if btn:
                    btn.setText(f"Роли ({len(new_roles)})")
        
        self._mark_dirty()

    def bulk_assign_actors(
        self,
        characters: List[str],
        actor_id: Optional[str]
    ) -> None:
        """Массовое назначение актёра на персонажей"""
        self.actor_service.bulk_assign_actors(
            self.data_ref["global_map"], characters, actor_id
        )
        self.refresh()
        self._mark_dirty()

    def get_actor_roles(self, actor_id: str) -> List[str]:
        """Получение списка ролей актёра"""
        return self.actor_service.get_actor_roles(
            self.data_ref["global_map"], actor_id
        )

    def get_unassigned_characters(self) -> List[str]:
        """Получение списка неназначенных персонажей"""
        return self.actor_service.get_unassigned_characters(
            self.data_ref["global_map"], []
        )

    def _mark_dirty(self) -> None:
        """Пометка проекта как изменённого"""
        if self.on_dirty_callback:
            self.on_dirty_callback()
