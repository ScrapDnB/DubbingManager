"""Main UI class for Dubbing Manager"""

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
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Slot

# Импорты для Мультимедиа
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

# Импорт WebEngine
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    from PySide6.QtWidgets import QTextBrowser as QWebEngineView
    WEB_ENGINE_AVAILABLE = False

# Попытка импорта openpyxl
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from src.utils import *
from src.dialogs import *
from src.workers import *
from src.models import *

class WebBridge(QObject):
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.main_app = main_app

    @Slot(str)
    def handle_js_message(self, message):
        print(f"JS Message received: {message}")
        # Здесь можно обрабатывать сообщения из JavaScript

    @Slot(result=str)
    def get_current_data(self):
        # Возвращаем текущие данные в формате JSON
        return json.dumps({
            "project_name": self.main_app.current_project_name,
            "episodes": list(self.main_app.episodes.keys()) if self.main_app.episodes else []
        })

class DubbingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dubbing Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize project data
        self.current_project_path = ""
        self.current_project_name = "Новый проект"
        self.actors = {}
        self.episodes = {}
        self.video_paths = {}
        self.export_config = {}
        self.prompter_config = {}
        
        # Initialize main components
        self.init_ui()
        self.init_timers()
        self.init_workers()
        
    def init_ui(self):
        """Initialize the main UI components"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Left panel - Actors
        self.create_left_panel()
        
        # Center panel - Episodes and Scripts
        self.create_center_panel()
        
        # Right panel - Video Player
        self.create_right_panel()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Готов")
        
    def create_left_panel(self):
        """Create the left panel for actors management"""
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # Project info
        project_group = QGroupBox("Проект:")
        project_layout = QHBoxLayout(project_group)
        self.project_name_edit = QLineEdit(self.current_project_name)
        project_layout.addWidget(self.project_name_edit)
        left_layout.addWidget(project_group)
        
        # Actors management
        actors_group = QGroupBox("Актеры")
        actors_layout = QVBoxLayout(actors_group)
        
        # Add actor button
        add_actor_btn = QPushButton("+ Актер")
        add_actor_btn.clicked.connect(self.add_actor)
        actors_layout.addWidget(add_actor_btn)
        
        # Actors list
        self.actors_table = QTableWidget()
        self.actors_table.setColumnCount(3)
        self.actors_table.setHorizontalHeaderLabels(["Имя", "Цвет", "Роли"])
        customize_table(self.actors_table)
        actors_layout.addWidget(self.actors_table)
        
        left_layout.addWidget(actors_group)
        left_layout.addStretch()
        
        self.main_splitter.addWidget(left_panel)
        
    def create_center_panel(self):
        """Create the center panel for episodes and scripts"""
        center_panel = QWidget()
        center_panel.setMinimumWidth(600)
        center_layout = QVBoxLayout(center_panel)
        
        # Episodes management
        episodes_group = QGroupBox("Эпизоды")
        episodes_layout = QVBoxLayout(episodes_group)
        
        # Episode controls
        episode_controls = QHBoxLayout()
        self.episode_combo = QComboBox()
        episode_controls.addWidget(QLabel("Эпизод:"))
        episode_controls.addWidget(self.episode_combo)
        
        add_episode_btn = QPushButton("+ Эпизод")
        add_episode_btn.clicked.connect(self.add_episode)
        episode_controls.addWidget(add_episode_btn)
        
        add_ass_btn = QPushButton("+ .ASS")
        add_ass_btn.clicked.connect(self.import_ass_file)
        episode_controls.addWidget(add_ass_btn)
        
        episodes_layout.addLayout(episode_controls)
        
        # Script table
        self.script_table = QTableWidget()
        self.script_table.setColumnCount(6)
        self.script_table.setHorizontalHeaderLabels(["ТК", "Персонаж", "Актер", "Текст", "Импорт", "Экспорт"])
        customize_table(self.script_table)
        episodes_layout.addWidget(self.script_table)
        
        center_layout.addWidget(episodes_group)
        
        self.main_splitter.addWidget(center_panel)
        
    def create_right_panel(self):
        """Create the right panel for video player"""
        right_panel = QWidget()
        right_panel.setMaximumWidth(500)
        right_layout = QVBoxLayout(right_panel)
        
        # Video player group
        video_group = QGroupBox("Видео")
        video_layout = QVBoxLayout(video_group)
        
        # Create video player
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        video_layout.addWidget(self.video_widget)
        
        # Video controls
        video_controls = QHBoxLayout()
        
        self.play_button = QPushButton("▶")
        self.play_button.clicked.connect(self.play_video)
        video_controls.addWidget(self.play_button)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderPressed.connect(self.seek_position)
        self.position_slider.sliderMoved.connect(self.set_position)
        video_controls.addWidget(self.position_slider)
        
        video_layout.addLayout(video_controls)
        
        right_layout.addWidget(video_group)
        
        self.main_splitter.addWidget(right_panel)
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('Файл')
        
        new_action = QAction('Новый', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('Открыть', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction('Сохранить', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        # Export menu
        export_menu = menubar.addMenu('Экспорт')
        
        html_export_action = QAction('HTML', self)
        html_export_action.triggered.connect(self.export_html)
        export_menu.addAction(html_export_action)
        
        excel_export_action = QAction('Excel', self)
        excel_export_action.triggered.connect(self.export_excel)
        export_menu.addAction(excel_export_action)
        
        reaper_export_action = QAction('Reaper', self)
        reaper_export_action.triggered.connect(self.export_reaper)
        export_menu.addAction(reaper_export_action)
        
    def init_timers(self):
        """Initialize timers for auto-save and other periodic tasks"""
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.autosave_project)
        self.autosave_timer.start(300000)  # 5 minutes in milliseconds
        
    def init_workers(self):
        """Initialize worker threads"""
        self.osc_worker = OscWorker()
        self.osc_worker.time_changed.connect(self.on_osc_time_changed)
        self.osc_worker.navigation_requested.connect(self.on_osc_navigation)
        
    def add_actor(self):
        """Add a new actor to the project"""
        name, ok = QInputDialog.getText(self, "Новый актер", "Имя актера:")
        if ok and name:
            # Generate a unique ID for the actor
            actor_id = f"actor_{len(self.actors) + 1}"
            
            # Get color for the actor
            color = QColorDialog.getColor()
            if color.isValid():
                color_hex = color.name()
                
                # Add to actors dictionary
                self.actors[actor_id] = {
                    "name": name,
                    "color": color_hex,
                    "roles": []
                }
                
                # Update the actors table
                self.update_actors_table()
                
    def update_actors_table(self):
        """Update the actors table display"""
        self.actors_table.setRowCount(len(self.actors))
        for row, (actor_id, actor_data) in enumerate(self.actors.items()):
            # Name
            name_item = QTableWidgetItem(actor_data["name"])
            self.actors_table.setItem(row, 0, name_item)
            
            # Color
            color_widget = QWidget()
            color_layout = QHBoxLayout(color_widget)
            color_label = QLabel()
            color_label.setStyleSheet(f"background-color: {actor_data['color']}; border: 1px solid black; min-width: 20px; min-height: 20px;")
            color_layout.addWidget(color_label)
            color_layout.setAlignment(Qt.AlignCenter)
            color_layout.setContentsMargins(4, 4, 4, 4)
            self.actors_table.setCellWidget(row, 1, color_widget)
            
            # Roles
            roles_item = QTableWidgetItem(", ".join(actor_data["roles"]))
            self.actors_table.setItem(row, 2, roles_item)
    
    def add_episode(self):
        """Add a new episode to the project"""
        name, ok = QInputDialog.getText(self, "Новый эпизод", "Название эпизода:")
        if ok and name:
            # Generate a unique number for the episode
            ep_num = len(self.episodes) + 1
            
            # Add to episodes dictionary
            self.episodes[ep_num] = {
                "name": name,
                "lines": []
            }
            
            # Update the episode combo box
            self.episode_combo.addItem(f"{ep_num}: {name}", ep_num)
            
    def import_ass_file(self):
        """Import an ASS subtitle file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть ASS файл", "", "ASS Files (*.ass)"
        )
        if file_path:
            # Process the ASS file here
            # This is a simplified implementation
            # In a real application, you would parse the ASS file
            # and populate the script table with the subtitles
            QMessageBox.information(self, "Импорт", f"Файл {file_path} выбран для импорта")
    
    def play_video(self):
        """Play or pause the video"""
        if self.media_player.isPlaying():
            self.media_player.pause()
            self.play_button.setText("▶")
        else:
            self.media_player.play()
            self.play_button.setText("⏸")
    
    def seek_position(self):
        """Seek to position when slider is pressed"""
        self.media_player.setPosition(self.position_slider.value())
    
    def set_position(self, position):
        """Set position when slider is moved"""
        self.media_player.setPosition(position)
    
    def new_project(self):
        """Create a new project"""
        self.current_project_path = ""
        self.current_project_name = "Новый проект"
        self.project_name_edit.setText(self.current_project_name)
        self.actors = {}
        self.episodes = {}
        self.video_paths = {}
        self.update_actors_table()
        self.episode_combo.clear()
        self.script_table.setRowCount(0)
        self.statusBar().showMessage("Создан новый проект")
    
    def open_project(self):
        """Open an existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                self.current_project_path = file_path
                self.current_project_name = project_data.get("project_name", "Новый проект")
                self.project_name_edit.setText(self.current_project_name)
                self.actors = project_data.get("actors", {})
                self.episodes = project_data.get("episodes", {})
                self.video_paths = project_data.get("video_paths", {})
                self.export_config = project_data.get("export_config", {})
                self.prompter_config = project_data.get("prompter_config", {})
                
                self.update_actors_table()
                self.update_episodes_combo()
                
                self.statusBar().showMessage(f"Проект открыт: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть проект: {str(e)}")
    
    def save_project(self):
        """Save the current project"""
        if not self.current_project_path:
            self.current_project_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить проект", "", "JSON Files (*.json)"
            )
            if not self.current_project_path:
                return
        
        try:
            project_data = {
                "project_name": self.current_project_name,
                "actors": self.actors,
                "episodes": self.episodes,
                "video_paths": self.video_paths,
                "export_config": self.export_config,
                "prompter_config": self.prompter_config,
                "created_at": getattr(self, 'created_at', datetime.now().isoformat()),
                "last_modified": datetime.now().isoformat()
            }
            
            with open(self.current_project_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            self.statusBar().showMessage(f"Проект сохранен: {self.current_project_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить проект: {str(e)}")
    
    def autosave_project(self):
        """Auto-save the project if it has been modified"""
        if self.current_project_path:
            self.save_project()
            print("Проект автосохранен")
    
    def export_html(self):
        """Export project to HTML"""
        # Implementation for HTML export
        QMessageBox.information(self, "Экспорт", "Экспорт в HTML заглушка")
    
    def export_excel(self):
        """Export project to Excel"""
        if not EXCEL_AVAILABLE:
            QMessageBox.warning(self, "Ошибка", "Модуль openpyxl не установлен")
            return
        
        # Implementation for Excel export
        QMessageBox.information(self, "Экспорт", "Экспорт в Excel заглушка")
    
    def export_reaper(self):
        """Export project to Reaper format"""
        dialog = ReaperExportDialog("", self)
        if dialog.exec() == QDialog.Accepted:
            video_enabled, regions_enabled = dialog.get_options()
            # Implementation for Reaper export
            QMessageBox.information(
                self, 
                "Экспорт", 
                f"Экспорт в Reaper:\nВидео: {video_enabled}\nРегионы: {regions_enabled}"
            )
    
    def update_episodes_combo(self):
        """Update the episodes combo box"""
        self.episode_combo.clear()
        for ep_num, ep_data in self.episodes.items():
            self.episode_combo.addItem(f"{ep_num}: {ep_data['name']}", ep_num)
    
    def on_osc_time_changed(self, time_value):
        """Handle OSC time change event"""
        # Update video position based on OSC time
        self.media_player.setPosition(int(time_value * 1000))  # Convert to milliseconds
    
    def on_osc_navigation(self, direction):
        """Handle OSC navigation event"""
        if direction == "next":
            # Move to next line in script
            current_row = self.script_table.currentRow()
            if current_row < self.script_table.rowCount() - 1:
                self.script_table.setCurrentCell(current_row + 1, 0)
        elif direction == "prev":
            # Move to previous line in script
            current_row = self.script_table.currentRow()
            if current_row > 0:
                self.script_table.setCurrentCell(current_row - 1, 0)