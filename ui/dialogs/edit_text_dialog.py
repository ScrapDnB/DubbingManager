"""ui/dialogs/edit_text_dialog.py"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
from PySide6.QtCore import Qt


class EditTextDialog(QDialog):
    """Диалог редактирования текста реплики"""
    
    def __init__(self, parent=None, initial_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Редактирование реплики")
        # Используем константы из config.constants
        from config.constants import EDIT_TEXT_DIALOG_WIDTH, EDIT_TEXT_DIALOG_HEIGHT
        self.resize(EDIT_TEXT_DIALOG_WIDTH, EDIT_TEXT_DIALOG_HEIGHT)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setFocus()
        layout.addWidget(self.text_edit)
        
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        # Ok по умолчанию
        btn_box.button(QDialogButtonBox.Ok).setDefault(True)
        layout.addWidget(btn_box)
    
    def get_text(self) -> str:
        """Получить отредактированный текст"""
        return self.text_edit.toPlainText()