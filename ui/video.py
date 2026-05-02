"""Video preview dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QSlider
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl
from typing import List, Dict, Any, Optional
import os
import logging

from config.constants import (
    VIDEO_WINDOW_WIDTH,
    VIDEO_WINDOW_HEIGHT,
    VIDEO_WIDGET_MIN_HEIGHT,
)
from utils.helpers import format_seconds_to_tc, customize_table

logger = logging.getLogger(__name__)


class VideoPreviewWindow(QDialog):
    """Video Preview Window class."""
    
    def __init__(
        self, 
        video_path: str, 
        lines: List[Dict[str, Any]], 
        ep_num: str, 
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Просмотр: Серия {ep_num}")
        self.resize(VIDEO_WINDOW_WIDTH, VIDEO_WINDOW_HEIGHT)
        self.video_path = video_path
        self.lines = lines
        
        self._init_ui()
        
        if self.video_path and os.path.exists(self.video_path):
            abs_path = os.path.abspath(self.video_path)
            self.media_player.setSource(QUrl.fromLocalFile(abs_path))
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(VIDEO_WIDGET_MIN_HEIGHT)
        layout.addWidget(self.video_widget)
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        
        ctrl_layout = QHBoxLayout()
        btn_play = QPushButton("Play/Pause")
        btn_play.clicked.connect(self.toggle_play)
        
        self.slider = QSlider(Qt.Horizontal)
        self.media_player.positionChanged.connect(self.slider.setValue)
        self.media_player.durationChanged.connect(
            lambda d: self.slider.setRange(0, d)
        )
        self.slider.sliderMoved.connect(self.media_player.setPosition)
        
        ctrl_layout.addWidget(btn_play)
        ctrl_layout.addWidget(self.slider)
        layout.addLayout(ctrl_layout)
        
        self.line_table = QTableWidget(0, 3)
        self.line_table.setHorizontalHeaderLabels([
            "Время", "Персонаж", "Текст"
        ])
        customize_table(self.line_table)
        self.line_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.line_table.cellClicked.connect(self.seek_to_line)
        layout.addWidget(self.line_table)
        
        for line in self.lines:
            row = self.line_table.rowCount()
            self.line_table.insertRow(row)
            self.line_table.setItem(
                row, 0, QTableWidgetItem(format_seconds_to_tc(line['s']))
            )
            self.line_table.setItem(row, 1, QTableWidgetItem(line['char']))
            self.line_table.setItem(row, 2, QTableWidgetItem(line['text']))
            self.line_table.item(row, 0).setData(Qt.UserRole, line['s'])
    
    def toggle_play(self) -> None:
        """Toggle play."""
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
    
    def seek_to_line(self, row: int, col: int) -> None:
        """Seek to line."""
        pos = self.line_table.item(row, 0).data(Qt.UserRole)
        self.media_player.setPosition(int(pos * 1000))
        self.media_player.play()
    
    def closeEvent(self, event) -> None:
        """Closeevent."""
        self.media_player.stop()
        event.accept()