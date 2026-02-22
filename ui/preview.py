"""Окно живого предпросмотра HTML"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Slot, QObject
from PySide6.QtWebChannel import QWebChannel
from typing import Dict, List, Any, Optional, Set
import logging
import os
import sys

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    from PySide6.QtWidgets import QTextBrowser as QWebEngineView
    WEB_ENGINE_AVAILABLE = False

from config.constants import (
    PREVIEW_WINDOW_WIDTH,
    PREVIEW_WINDOW_HEIGHT,
    PREVIEW_SETTINGS_PANEL_WIDTH,
)
from utils.helpers import hex_to_rgba_string
from services.hotkey_manager import GlobalHotkeyManager, PYNPUT_AVAILABLE
from .dialogs.actor_filter import ActorFilterDialog

logger = logging.getLogger(__name__)


class WebBridge(QObject):
    """Мост между JS и Python для редактирования текста"""
    
    def __init__(self, main_app: Any, parent=None):
        super().__init__(parent)
        self.main_app = main_app
    
    @Slot(int, int)
    def sync_scroll_index(self, index: int, total: int) -> None:
        """Обновляет счетчик в окне предпросмотра при прокрутке"""
        if self.main_app and hasattr(self.main_app, 'preview_window'):
            self.main_app.preview_window.update_counter_label(index, total)
    
    @Slot(str, str)
    def update_text(self, line_id: str, new_text: str) -> None:
        """Принимает ID строки и новый текст из HTML"""
        try:
            lid = int(line_id)
            ep = self.main_app.ep_combo.currentData()
            
            loaded = self.main_app.data.get("loaded_episodes", {})
            ep_key = None
            if ep in loaded:
                ep_key = ep
            elif str(ep) in loaded:
                ep_key = str(ep)
            
            updated = False
            if ep_key is not None:
                lines = loaded[ep_key]
                target = next(
                    (l for l in lines if int(l.get('id', -1)) == lid), 
                    None
                )
                if target and target.get('text') != new_text:
                    target['text'] = new_text
                    updated = True
            
            if not updated:
                try:
                    lines = self.main_app.get_episode_lines(ep)
                    target = next(
                        (l for l in lines if int(l.get('id', -1)) == lid), 
                        None
                    )
                    if target and target.get('text') != new_text:
                        target['text'] = new_text
                        if 'loaded_episodes' not in self.main_app.data:
                            self.main_app.data['loaded_episodes'] = {}
                        self.main_app.data['loaded_episodes'][str(ep)] = lines
                        updated = True
                except Exception as e:
                    logger.warning(f"Error getting episode lines: {e}")
            
            if updated:
                try:
                    self.main_app.set_dirty(True)
                except Exception as e:
                    logger.warning(f"Error setting dirty: {e}")
                
                if (
                    hasattr(self.main_app, 'preview_window') and 
                    self.main_app.preview_window
                ):
                    self.main_app.preview_window._has_text_changes = True
                    try:
                        self.main_app.preview_window.update_preview()
                    except Exception as e:
                        logger.warning(f"Error updating preview: {e}")
                    
                    logger.debug(f"Updated line {lid}: {new_text}")
        except Exception as e:
            logger.error(f"Error updating text: {e}")


class HtmlLivePreview(QDialog):
    """Окно живого предпросмотра монтажного листа"""
    
    def __init__(self, main_app: Any, ep_num: str):
        super().__init__(None)
        self.main_app = main_app
        self.ep_num = ep_num
        self.setWindowTitle(f"Предпросмотр монтажного листа: Серия {ep_num}")
        self.resize(PREVIEW_WINDOW_WIDTH, PREVIEW_WINDOW_HEIGHT)
        
        self.highlight_ids: Optional[List[str]] = None
        self.current_h_index = -1
        self._has_text_changes = False
        
        self._init_ui()
        
        self.browser.loadFinished.connect(self.on_page_loaded)
        self.main_app.preview_window = self
        
        if WEB_ENGINE_AVAILABLE:
            self.channel = QWebChannel()
            self.bridge = WebBridge(self.main_app)
            self.channel.registerObject("backend", self.bridge)
            self.browser.page().setWebChannel(self.channel)
        
        self.setup_global_hotkeys()
        self.update_preview()
    
    def _init_ui(self) -> None:
        """Инициализация интерфейса"""
        self.root_layout = QVBoxLayout(self)
        
        # Панель навигации
        self.nav_panel = QHBoxLayout()
        
        self.btn_toggle_sidebar = QPushButton("⬅ Скрыть настройки")
        self.btn_toggle_sidebar.setCheckable(True)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        self.btn_prev_h = QPushButton("⏮ Пред. реплика (Alt+←)")
        self.btn_prev_h.setShortcut("Alt+Left")
        self.btn_prev_h.clicked.connect(
            lambda: self.scroll_to_highlight("prev")
        )
        
        self.lbl_h_count = QLabel("0 / 0")
        self.lbl_h_count.setStyleSheet(
            "font-weight: bold; margin: 0 10px;"
        )
        
        self.btn_next_h = QPushButton("След. реплика (Alt+→) ⏭")
        self.btn_next_h.setShortcut("Alt+Right")
        self.btn_next_h.clicked.connect(
            lambda: self.scroll_to_highlight("next")
        )
        
        self.nav_panel.addWidget(self.btn_toggle_sidebar)
        self.nav_panel.addSpacing(20)
        self.nav_panel.addWidget(self.btn_prev_h)
        self.nav_panel.addWidget(self.lbl_h_count)
        self.nav_panel.addWidget(self.btn_next_h)
        self.nav_panel.addStretch()
        
        self.root_layout.addLayout(self.nav_panel)
        
        # Контент
        self.content_layout = QHBoxLayout()
        self.root_layout.addLayout(self.content_layout)

        # Панель настроек
        self.settings_panel = QFrame()
        self.settings_panel.setFixedWidth(PREVIEW_SETTINGS_PANEL_WIDTH)
        self.settings_panel.setFrameShape(QFrame.StyledPanel)
        sp_layout = QVBoxLayout(self.settings_panel)
        
        sp_layout.addWidget(QLabel("<b>Настройки вида</b>"))
        
        self.combo_layout = QComboBox()
        self.combo_layout.addItems(["Таблица", "Сценарий"])
        current_type = self.main_app.data["export_config"].get(
            "layout_type", "Таблица"
        )
        self.combo_layout.setCurrentText(current_type)
        self.combo_layout.currentIndexChanged.connect(self.update_preview)
        sp_layout.addWidget(QLabel("Формат:"))
        sp_layout.addWidget(self.combo_layout)
        sp_layout.addSpacing(10)
        
        # Шрифты
        font_group = QGroupBox("Размеры шрифтов")
        fg_layout = QFormLayout(font_group)
        
        self.s_time = QSpinBox()
        self.s_time.setRange(6, 48)
        self.s_time.setValue(
            self.main_app.data["export_config"].get("f_time", 12)
        )
        self.s_time.valueChanged.connect(self.on_setting_change)
        
        self.s_char = QSpinBox()
        self.s_char.setRange(6, 48)
        self.s_char.setValue(
            self.main_app.data["export_config"].get("f_char", 14)
        )
        self.s_char.valueChanged.connect(self.on_setting_change)
        
        self.s_actor = QSpinBox()
        self.s_actor.setRange(6, 48)
        self.s_actor.setValue(
            self.main_app.data["export_config"].get("f_actor", 14)
        )
        self.s_actor.valueChanged.connect(self.on_setting_change)
        
        self.s_text = QSpinBox()
        self.s_text.setRange(6, 48)
        self.s_text.setValue(
            self.main_app.data["export_config"].get("f_text", 16)
        )
        self.s_text.valueChanged.connect(self.on_setting_change)
        
        fg_layout.addRow("Таймкод:", self.s_time)
        fg_layout.addRow("Персонаж:", self.s_char)
        fg_layout.addRow("Актер:", self.s_actor)
        fg_layout.addRow("Текст:", self.s_text)
        sp_layout.addWidget(font_group)
        
        # Подсветка
        filter_group = QGroupBox("Подсветка")
        f_lay = QVBoxLayout(filter_group)
        btn_filter = QPushButton("Выбрать актеров...")
        btn_filter.clicked.connect(self.open_actor_filter)
        f_lay.addWidget(btn_filter)
        sp_layout.addWidget(filter_group)
        sp_layout.addStretch()
        
        # Сохранение
        save_group = QGroupBox("Сохранение")
        sg_layout = QVBoxLayout(save_group)
        
        btn_save_ass = QPushButton("💾 Сохранить в .ASS")
        btn_save_ass.clicked.connect(self.save_to_original_ass)
        
        btn_save_copy = QPushButton("Сохранить копию...")
        btn_save_copy.clicked.connect(self.save_ass_copy)
        
        sg_layout.addWidget(btn_save_ass)
        sg_layout.addWidget(btn_save_copy)
        sp_layout.addWidget(save_group)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        sp_layout.addWidget(btn_close)
        
        self.content_layout.addWidget(self.settings_panel)
        
        # Браузер
        self.browser = QWebEngineView()
        if not WEB_ENGINE_AVAILABLE:
            self.browser.setOpenExternalLinks(False)
        self.content_layout.addWidget(self.browser)
    
    @Slot()
    def on_page_loaded(self, ok: bool) -> None:
        """Обработка загрузки страницы"""
        if ok:
            QTimer.singleShot(
                100, 
                lambda: self.browser.page().runJavaScript(
                    "window.updateScrollStatus();"
                )
            )
    
    def update_counter_label(self, index: int, total: int) -> None:
        """Обновление счетчика реплик"""
        self.current_h_index = index
        if total > 0:
            self.lbl_h_count.setText(f"{index + 1} / {total}")
        else:
            self.lbl_h_count.setText("0 / 0")
    
    def setup_global_hotkeys(self) -> None:
        """Настройка глобальных горячих клавиш"""
        if not PYNPUT_AVAILABLE:
            logger.info("pynput недоступен, только локальные хоткеи")
            return
        
        try:
            if self.main_app.global_hotkey_manager is None:
                self.main_app.global_hotkey_manager = GlobalHotkeyManager(
                    self.main_app
                )
            
            prev_key_str = "alt+left"
            next_key_str = "alt+right"
            
            self.main_app.global_hotkey_manager.clear_hotkeys()
            self.main_app.global_hotkey_manager.register_hotkey(
                "prev", prev_key_str, self.go_prev_hotkey
            )
            self.main_app.global_hotkey_manager.register_hotkey(
                "next", next_key_str, self.go_next_hotkey
            )
            
            if not self.main_app.global_hotkey_manager._running:
                QTimer.singleShot(
                    100, self.main_app.global_hotkey_manager.start
                )
        except Exception as e:
            logger.error(f"Error setting up hotkeys: {e}")
    
    def go_prev_hotkey(self) -> None:
        """Хоткей назад"""
        QTimer.singleShot(
            0, lambda: self.scroll_to_highlight("prev")
        )
    
    def go_next_hotkey(self) -> None:
        """Хоткей вперёд"""
        QTimer.singleShot(
            0, lambda: self.scroll_to_highlight("next")
        )
    
    def scroll_to_highlight(self, direction: str) -> None:
        """Прокрутка к подсвеченной реплике"""
        js_get_total = (
            "document.querySelectorAll('.highlighted-block').length"
        )
        
        def navigate(total: Any) -> None:
            if not total or int(total) == 0:
                return
            total = int(total)
            
            if direction == "next":
                target_index = self.current_h_index + 1
                if target_index >= total:
                    target_index = 0
            else:
                target_index = self.current_h_index - 1
                if target_index < 0:
                    target_index = total - 1
            
            js_jump = f"""
            (function() {{
                var blocks = document.querySelectorAll('.highlighted-block');
                var target = blocks[{target_index}];
                if (target) {{
                    blocks.forEach(b => b.classList.remove('active-replica'));
                    target.classList.add('active-replica');
                    target.scrollIntoView({{ 
                        behavior: 'smooth', 
                        block: 'center' 
                    }});
                }}
            }})();
            """
            self.browser.page().runJavaScript(js_jump)
            self.current_h_index = target_index
            self.lbl_h_count.setText(f"{target_index + 1} / {total}")
        
        self.browser.page().runJavaScript(js_get_total, navigate)
    
    def update_preview(self) -> None:
        """Обновление предпросмотра"""
        lines = self.main_app.get_episode_lines(self.ep_num)
        if not lines:
            self.browser.setHtml("<h3>Нет данных в серии</h3>")
            return
        
        try:
            self.browser.loadFinished.disconnect(self.on_page_loaded)
        except Exception:
            pass
        
        self.browser.loadFinished.connect(self.on_page_loaded)
        
        cfg = self.main_app.data["export_config"]
        local_layout = self.combo_layout.currentText()
        processed = self.main_app.process_merge_logic(lines, cfg)
        html = self.main_app.generate_html_body(
            self.ep_num, 
            processed, 
            cfg, 
            self.highlight_ids, 
            override_layout=local_layout
        )
        self.browser.setHtml(html)
    
    def toggle_sidebar(self) -> None:
        """Показать/скрыть панель настроек"""
        is_hidden = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_hidden)
        
        if is_hidden:
            self.btn_toggle_sidebar.setText("➡ Показать настройки")
        else:
            self.btn_toggle_sidebar.setText("⬅ Скрыть настройки")
    
    def on_setting_change(self) -> None:
        """Изменение настроек шрифтов"""
        cfg = self.main_app.data["export_config"]
        cfg["f_time"] = self.s_time.value()
        cfg["f_char"] = self.s_char.value()
        cfg["f_actor"] = self.s_actor.value()
        cfg["f_text"] = self.s_text.value()
        self.update_preview()
    
    def open_actor_filter(self) -> None:
        """Открытие фильтра актёров"""
        all_aids = list(self.main_app.data["actors"].keys())
        current_selection = (
            self.highlight_ids 
            if self.highlight_ids is not None 
            else all_aids
        )
        
        dialog = ActorFilterDialog(
            self.main_app.data["actors"], 
            current_selection, 
            self
        )
        
        if dialog.exec():
            selected = dialog.get_selected()
            if len(selected) == len(all_aids) or len(selected) == 0:
                self.highlight_ids = None
            else:
                self.highlight_ids = selected
            self.update_preview()
    
    def save_to_original_ass(self) -> None:
        """Сохранение в оригинальный ASS"""
        if QMessageBox.question(
            self, 
            "Подтверждение",
            "Это перезапишет исходный файл .ass на диске.\nПродолжить?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            if self.main_app.save_episode_to_ass(self.ep_num):
                self._has_text_changes = False
                QMessageBox.information(
                    self, "Успех", "Файл успешно сохранен!"
                )
    
    def save_ass_copy(self) -> None:
        """Сохранение копии ASS"""
        fn, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить копию", 
            f"Episode_{self.ep_num}_edit.ass", 
            "ASS Files (*.ass)"
        )
        if fn:
            if self.main_app.save_episode_to_ass(self.ep_num, fn):
                QMessageBox.information(
                    self, "Успех", f"Копия сохранена:\n{fn}"
                )
    
    def keyPressEvent(self, event) -> None:
        """Обработка клавиш"""
        modifiers = event.modifiers()
        is_alt = modifiers & Qt.AltModifier
        
        if event.key() == Qt.Key_Left or (
            event.key() == Qt.Key_Left and is_alt
        ):
            self.scroll_to_highlight("prev")
        elif event.key() == Qt.Key_Right or (
            event.key() == Qt.Key_Right and is_alt
        ):
            self.scroll_to_highlight("next")
        elif event.key() == Qt.Key_Up and is_alt:
            self.scroll_to_highlight("prev")
        elif event.key() == Qt.Key_Down and is_alt:
            self.scroll_to_highlight("next")
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event) -> None:
        """Закрытие окна"""
        if self._has_text_changes:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "У вас есть несохраненные изменения в тексте.\n"
                "Хотите сохранить их в .ASS перед выходом?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                if self.main_app.save_episode_to_ass(self.ep_num):
                    self._has_text_changes = False
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()