"""Dialog classes for Dubbing Manager"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QColorDialog, QComboBox, QLabel,
    QHeaderView, QInputDialog, QFrame, QSpinBox, QLineEdit,
    QDialog, QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QSlider, QAbstractItemView, QStackedWidget,
    QDoubleSpinBox, QRadioButton, QGridLayout, QScrollArea,
    QGraphicsView, QGraphicsScene, QGraphicsTextItem,
    QSplitter, QSizePolicy, QToolBar, QKeySequenceEdit, QDialogButtonBox, QTextEdit
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QAction, QKeySequence, QPen, QBrush
)
from PySide6.QtCore import (
    Qt, QUrl, QTimer, QThread, Signal, QRectF, QEvent, Slot, QObject
)
import os

class ReaperExportDialog(QDialog):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки проекта Reaper")
        self.resize(350, 150)
        
        layout = QVBoxLayout(self)
        
        # Группировка опций
        layout.addWidget(QLabel("Выберите компоненты для экспорта:"))
        
        self.chk_video = QCheckBox("Добавить дорожку с видео")
        self.chk_regions = QCheckBox("Создать регионы (реплики с текстом)")
        
        # Настройка состояния чекбокса видео
        has_video = video_path and os.path.exists(video_path)
        if has_video:
            self.chk_video.setChecked(True)
            self.chk_video.setText(f"Добавить видео ({os.path.basename(video_path)})")
        else:
            self.chk_video.setChecked(False)
            self.chk_video.setEnabled(False)
            self.chk_video.setText("Видео не найдено (опция недоступна)")
            
        self.chk_regions.setChecked(True) # Регионы включены по умолчанию
        
        layout.addWidget(self.chk_video)
        layout.addWidget(self.chk_regions)
        
        # Кнопки ОК / Отмена
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_options(self):
        return self.chk_video.isChecked(), self.chk_regions.isChecked()