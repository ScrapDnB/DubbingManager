"""Тесты для main.py"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestMainLogging:
    """Тесты настройки логирования в main.py"""

    def test_get_log_path_windows(self):
        """Тест пути логов на Windows"""
        with patch('main.sys.platform', 'win32'):
            with patch('main.os.environ.get', return_value='C:\\Users\\test\\AppData\\Local'):
                from main import get_log_path
                path = get_log_path()
                
                assert 'DubbingManager' in str(path)
                assert path.suffix == '.log'

    def test_get_log_path_macos(self):
        """Тест пути логов на macOS"""
        with patch('main.sys.platform', 'darwin'):
            # Импортируем функцию заново
            import importlib
            import main
            importlib.reload(main)
            
            path = main.get_log_path()
            
            assert 'DubbingManager' in str(path)
            assert 'Logs' in str(path) or 'logs' in str(path)

    def test_get_log_path_linux(self):
        """Тест пути логов на Linux"""
        with patch('main.sys.platform', 'linux'):
            import importlib
            import main
            importlib.reload(main)
            
            path = main.get_log_path()
            
            assert 'dubbing-manager' in str(path)

    def test_get_log_path_no_env(self):
        """Тест пути логов без переменных окружения"""
        with patch('main.sys.platform', 'win32'):
            with patch('main.os.environ.get', return_value=None):
                import importlib
                import main
                importlib.reload(main)
                
                path = main.get_log_path()
                
                assert path.exists() or str(path).startswith(str(Path.home()))

    def test_get_log_path_creates_directory(self, tmp_path):
        """Тест создания директории логов"""
        log_dir = tmp_path / "test_logs"
        
        with patch('main.sys.platform', 'darwin'):
            with patch('main.Path.home', return_value=tmp_path):
                import importlib
                import main
                importlib.reload(main)
                
                path = main.get_log_path()
                
                # Директория должна быть создана
                assert path.parent.exists()
