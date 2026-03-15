"""Тесты для web_bridge.py"""

import pytest
from unittest.mock import MagicMock, patch

from utils.web_bridge import WebBridge


class TestWebBridge:
    """Тесты для WebBridge"""

    @pytest.fixture
    def main_app(self):
        """Мокированное главное приложение"""
        app = MagicMock()
        app.ep_combo.currentData.return_value = "1"
        app.data = {
            "loaded_episodes": {
                "1": [
                    {"id": 1, "text": "Original text"},
                    {"id": 2, "text": "Another text"},
                ]
            }
        }
        app.set_dirty = MagicMock()
        app.get_episode_lines = MagicMock(return_value=[])
        app.preview_window = None
        app.text_changes = {}
        app.update_save_ass_button = MagicMock()
        return app

    @pytest.fixture
    def bridge(self, main_app):
        """Мост с мокированным приложением"""
        return WebBridge(main_app)

    def test_init(self, main_app):
        """Тест инициализации"""
        bridge = WebBridge(main_app)
        
        assert bridge.main_app == main_app

    def test_update_text_success(self, bridge, main_app):
        """Тест успешного обновления текста"""
        bridge.update_text("1", "New text")
        
        assert main_app.data["loaded_episodes"]["1"][0]["text"] == "New text"
        main_app.set_dirty.assert_called_once()

    def test_update_text_same_text(self, bridge, main_app):
        """Тест обновления тем же текстом"""
        bridge.update_text("1", "Original text")
        
        main_app.set_dirty.assert_not_called()

    def test_update_text_line_not_found(self, bridge, main_app):
        """Тест когда строка не найдена"""
        bridge.update_text("999", "New text")
        
        # Должен попробовать загрузить эпизод
        main_app.get_episode_lines.assert_called()

    def test_update_text_with_preview_window(self, bridge, main_app):
        """Тест обновления с окном превью"""
        preview = MagicMock()
        main_app.preview_window = preview
        
        bridge.update_text("1", "New text")
        
        preview.update_preview.assert_called()

    def test_update_text_preview_error(self, bridge, main_app):
        """Тест ошибки обновления превью"""
        preview = MagicMock()
        preview.update_preview.side_effect = Exception("Error")
        main_app.preview_window = preview
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")

    def test_update_text_set_dirty_error(self, bridge, main_app):
        """Тест ошибки установки dirty"""
        main_app.set_dirty.side_effect = Exception("Error")
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")

    def test_update_text_update_button_error(self, bridge, main_app):
        """Тест ошибки обновления кнопки"""
        main_app.update_save_ass_button.side_effect = Exception("Error")
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")

    def test_update_text_invalid_id(self, bridge, main_app):
        """Тест невалидного ID"""
        # Не должно вызывать исключение
        bridge.update_text("invalid", "New text")

    def test_update_text_string_episode_key(self, bridge, main_app):
        """Тест строкового ключа эпизода"""
        main_app.ep_combo.currentData.return_value = 1  # int
        main_app.data = {
            "loaded_episodes": {
                "1": [{"id": 1, "text": "Original"}]  # str key
            }
        }
        
        bridge.update_text("1", "New text")
        
        assert main_app.data["loaded_episodes"]["1"][0]["text"] == "New text"

    def test_update_text_no_loaded_episodes(self, bridge, main_app):
        """Тест без загруженных эпизодов"""
        main_app.data = {"loaded_episodes": {}}
        main_app.get_episode_lines.return_value = [{"id": 1, "text": "Original"}]
        
        bridge.update_text("1", "New text")
        
        # Должен добавить в loaded_episodes
        assert "1" in main_app.data["loaded_episodes"]

    def test_update_text_no_text_changes_attr(self, bridge, main_app):
        """Тест без атрибута text_changes"""
        delattr(main_app, 'text_changes')
        
        bridge.update_text("1", "New text")
        
        assert hasattr(main_app, 'text_changes')
        assert main_app.text_changes["1"] == True

    def test_update_text_no_update_save_ass_button(self, bridge, main_app):
        """Тест без метода update_save_ass_button"""
        delattr(main_app, 'update_save_ass_button')
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")

    def test_update_text_no_preview_window_attr(self, bridge, main_app):
        """Тест без атрибута preview_window"""
        delattr(main_app, 'preview_window')
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")

    def test_update_text_general_error(self, bridge, main_app):
        """Тест общей ошибки"""
        # Симулируем ошибку в начале метода
        main_app.ep_combo = None
        
        # Не должно вызывать исключение
        bridge.update_text("1", "New text")
