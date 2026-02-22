"""Диалог управления ролями актёра"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QInputDialog
)
from typing import List


class ActorRolesDialog(QDialog):
    """Диалог редактирования ролей актёра"""
    
    def __init__(
        self, 
        actor_name: str, 
        current_roles: List[str], 
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Роли: {actor_name}")
        
        self._init_ui(current_roles)
    
    def _init_ui(self, current_roles: List[str]) -> None:
        layout = QVBoxLayout(self)
        
        self._list_widget = QListWidget()
        self._list_widget.addItems(current_roles)
        layout.addWidget(self._list_widget)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Добавить")
        btn_del = QPushButton("Удалить")
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)
        
        btn_add.clicked.connect(self._add_role)
        btn_del.clicked.connect(self._del_role)
        
        btn_ok = QPushButton("Готово")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)
    
    def _add_role(self) -> None:
        role_name, ok = QInputDialog.getText(
            self, "Новая роль", "Имя:"
        )
        if ok and role_name:
            self._list_widget.addItem(role_name)
    
    def _del_role(self) -> None:
        for item in self._list_widget.selectedItems():
            self._list_widget.takeItem(self._list_widget.row(item))
    
    def get_roles(self) -> List[str]:
        """Возвращает список ролей"""
        return [
            self._list_widget.item(i).text() 
            for i in range(self._list_widget.count())
        ]