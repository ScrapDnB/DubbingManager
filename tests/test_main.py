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
        with patch('app_startup.sys.platform', 'win32'):
            with patch('app_startup.os.environ.get', return_value='C:\\Users\\test\\AppData\\Local'):
                from main import get_log_path
                path = get_log_path()
                
                assert 'DubbingManager' in str(path)
                assert path.suffix == '.log'

    def test_get_log_path_macos(self):
        """Тест пути логов на macOS"""
        with patch('app_startup.sys.platform', 'darwin'):
            # Импортируем функцию заново
            import importlib
            import main
            importlib.reload(main)
            
            path = main.get_log_path()
            
            assert 'DubbingManager' in str(path)
            assert 'Logs' in str(path) or 'logs' in str(path)

    def test_get_log_path_linux(self):
        """Тест пути логов на Linux"""
        with patch('app_startup.sys.platform', 'linux'):
            import importlib
            import main
            importlib.reload(main)
            
            path = main.get_log_path()
            
            assert 'dubbing-manager' in str(path)

    def test_get_log_path_no_env(self):
        """Тест пути логов без переменных окружения"""
        with patch('app_startup.sys.platform', 'win32'):
            with patch('app_startup.os.environ.get', return_value=None):
                import importlib
                import main
                importlib.reload(main)
                
                path = main.get_log_path()
                
                assert path.exists() or str(path).startswith(str(Path.home()))

    def test_get_log_path_creates_directory(self, tmp_path):
        """Тест создания директории логов"""
        log_dir = tmp_path / "test_logs"
        
        with patch('app_startup.sys.platform', 'darwin'):
            with patch('app_startup.Path.home', return_value=tmp_path):
                import importlib
                import main
                importlib.reload(main)
                
                path = main.get_log_path()
                
                # Директория должна быть создана
                assert path.parent.exists()


class TestProjectFileArguments:
    """Tests for project file path detection."""

    def test_is_project_file_accepts_projects_backups_and_legacy_json(self):
        from main import is_project_file

        assert is_project_file("/tmp/project.dub")
        assert is_project_file("/tmp/project.DUB")
        assert is_project_file("/tmp/project.dub_backup")
        assert is_project_file("/tmp/project.DUB_BACKUP")
        assert is_project_file("/tmp/project.json")
        assert not is_project_file("/tmp/project.txt")

    def test_initial_project_path_returns_first_existing_project(self, tmp_path):
        from main import initial_project_path

        txt = tmp_path / "notes.txt"
        dub = tmp_path / "show.dub"
        legacy = tmp_path / "old.json"
        txt.write_text("notes", encoding="utf-8")
        dub.write_text("{}", encoding="utf-8")
        legacy.write_text("{}", encoding="utf-8")

        assert initial_project_path([
            "DubbingManager",
            str(txt),
            str(dub),
            str(legacy),
        ]) == str(dub)


class TestQmlStartup:
    """Tests for platform-specific QML startup configuration."""

    def test_windows_webengine_disables_vulkan_without_losing_other_flags(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")
        configure_platform_graphics("win32")

        flags = os.environ["QTWEBENGINE_CHROMIUM_FLAGS"].split()
        assert "--disable-gpu-sandbox" in flags
        assert "--disable-vulkan" in flags

    def test_non_windows_webengine_flags_remain_unchanged(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")
        configure_platform_graphics("darwin")

        assert os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--disable-gpu-sandbox"
