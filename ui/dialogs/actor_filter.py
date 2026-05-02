"""Actor filter dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QWidget, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
from typing import Dict, List, Set, Optional


class ActorFilterDialog(QDialog):
    """Actor Filter Dialog dialog."""

    def __init__(
        self,
        actors_data: Dict[str, Dict],
        selected_ids: Optional[List[str]] = None,
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор подсветки")
        self.resize(300, 400)

        self.actors_data: Dict[str, Dict] = actors_data
        self.selected_ids: Set[str] = set(selected_ids) if selected_ids else set()

        self._checks_layout: QVBoxLayout
        self._checkboxes: Dict[str, QCheckBox]
        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        btn_layout: QHBoxLayout = QHBoxLayout()
        btn_all = QPushButton("Все")
        btn_none = QPushButton("Сбросить")
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        layout.addLayout(btn_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self._checks_layout = QVBoxLayout(content)

        self._checkboxes = {}
        aid: str
        info: Dict
        for aid, info in self.actors_data.items():
            chk: QCheckBox = QCheckBox(info["name"])
            if not self.selected_ids or aid in self.selected_ids:
                chk.setChecked(True)
            self._checkboxes[aid] = chk
            self._checks_layout.addWidget(chk)

        self._checks_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_ok = QPushButton("Применить")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def _select_all(self) -> None:
        chk: QCheckBox
        for chk in self._checkboxes.values():
            chk.setChecked(True)

    def _select_none(self) -> None:
        chk: QCheckBox
        for chk in self._checkboxes.values():
            chk.setChecked(False)

    def get_selected(self) -> List[str]:
        """Return selected."""
        return [aid for aid, chk in self._checkboxes.items() if chk.isChecked()]