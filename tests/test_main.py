"""Tests for shared startup helpers and the QML entry point."""

import os
from unittest.mock import patch
from pathlib import Path


class TestMainLogging:
    """Tests for shared startup logging paths."""

    def test_get_log_path_windows(self):
        """Тест пути логов на Windows"""
        with patch('app_startup.sys.platform', 'win32'):
            with patch('app_startup.os.environ.get', return_value='C:\\Users\\test\\AppData\\Local'):
                from app_startup import get_log_path
                path = get_log_path()
                
                assert 'DubbingManager' in str(path)
                assert path.suffix == '.log'

    def test_get_log_path_macos(self):
        """Тест пути логов на macOS"""
        with patch('app_startup.sys.platform', 'darwin'):
            from app_startup import get_log_path

            path = get_log_path()
            
            assert 'DubbingManager' in str(path)
            assert 'Logs' in str(path) or 'logs' in str(path)

    def test_get_log_path_linux(self):
        """Тест пути логов на Linux"""
        with patch('app_startup.sys.platform', 'linux'):
            from app_startup import get_log_path

            path = get_log_path()
            
            assert 'dubbing-manager' in str(path)

    def test_get_log_path_no_env(self):
        """Тест пути логов без переменных окружения"""
        with patch('app_startup.sys.platform', 'win32'):
            with patch('app_startup.os.environ.get', return_value=None):
                from app_startup import get_log_path

                path = get_log_path()
                
                assert path.exists() or str(path).startswith(str(Path.home()))

    def test_get_log_path_creates_directory(self, tmp_path):
        """Тест создания директории логов"""
        log_dir = tmp_path / "test_logs"
        
        with patch('app_startup.sys.platform', 'darwin'):
            with patch('app_startup.Path.home', return_value=tmp_path):
                from app_startup import get_log_path

                path = get_log_path()
                
                # Директория должна быть создана
                assert path.parent.exists()


class TestProjectFileArguments:
    """Tests for project file path detection."""

    def test_is_project_file_accepts_projects_backups_and_legacy_json(self):
        from app_startup import is_project_file

        assert is_project_file("/tmp/project.dub")
        assert is_project_file("/tmp/project.DUB")
        assert is_project_file("/tmp/project.dub_backup")
        assert is_project_file("/tmp/project.DUB_BACKUP")
        assert is_project_file("/tmp/project.json")
        assert not is_project_file("/tmp/project.txt")

    def test_initial_project_path_returns_first_existing_project(self, tmp_path):
        from app_startup import initial_project_path

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

    def test_windows_dpi_awareness_is_configured_before_qt_import(self):
        source = Path("qml_main.py").read_text(encoding="utf-8")

        assert source.index("configure_windows_dpi_awareness()") < source.index(
            "from PySide6.QtCore"
        )
        assert "SetProcessDpiAwarenessContext" in source
        assert "DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2" in source

    def test_windows_ui_scale_is_configured_before_qt_import(self):
        source = Path("qml_main.py").read_text(encoding="utf-8")

        assert source.index("configure_windows_ui_scale()") < source.index(
            "from PySide6.QtCore"
        )

    def test_windows_ui_scale_compacts_qt_without_overriding_explicit_value(
        self, monkeypatch
    ):
        from qml_main import configure_windows_ui_scale

        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        configure_windows_ui_scale("win32")
        assert os.environ["QT_SCALE_FACTOR"] == "0.75"

        monkeypatch.setenv("QT_SCALE_FACTOR", "1.0")
        configure_windows_ui_scale("win32")
        assert os.environ["QT_SCALE_FACTOR"] == "1.0"

    def test_windows_ui_scale_does_not_affect_other_platforms(self, monkeypatch):
        from qml_main import configure_windows_ui_scale

        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        configure_windows_ui_scale("darwin")

        assert "QT_SCALE_FACTOR" not in os.environ

    def test_windows_ui_scale_uses_saved_preference(self, monkeypatch):
        from qml_main import configure_windows_ui_scale

        monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
        monkeypatch.setattr("qml_main._windows_ui_scale_percent", lambda: 125)

        configure_windows_ui_scale("win32")

        assert os.environ["QT_SCALE_FACTOR"] == "1.25"

    def test_windows_webengine_disables_vulkan_without_losing_other_flags(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")
        configure_platform_graphics("win32")

        flags = os.environ["QTWEBENGINE_CHROMIUM_FLAGS"].split()
        assert "--disable-gpu-sandbox" in flags
        assert "--disable-vulkan" in flags
        assert os.environ["QSG_RHI_BACKEND"] == "d3d11"

    def test_windows_keeps_an_explicit_qt_quick_backend(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QSG_RHI_BACKEND", "opengl")
        configure_platform_graphics("win32")

        assert os.environ["QSG_RHI_BACKEND"] == "opengl"

    def test_macos_disables_experimental_skia_graphite(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")
        configure_platform_graphics("darwin")

        flags = os.environ["QTWEBENGINE_CHROMIUM_FLAGS"].split()
        assert "--disable-gpu-sandbox" in flags
        assert "--disable-skia-graphite" in flags

    def test_other_platform_webengine_flags_remain_unchanged(self, monkeypatch):
        from qml_main import configure_platform_graphics

        monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu-sandbox")
        configure_platform_graphics("linux")

        assert os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == "--disable-gpu-sandbox"

    def test_windows_qml_controls_use_fluent_style_unless_overridden(self, monkeypatch):
        from qml_main import configure_qml_controls_style

        monkeypatch.delenv("QT_QUICK_CONTROLS_STYLE", raising=False)
        monkeypatch.setattr("qml_main.sys.platform", "win32")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "FluentWinUI3"

        monkeypatch.setenv("QT_QUICK_CONTROLS_STYLE", "Fusion")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "Fusion"

    def test_macos_qml_controls_use_native_style(self, monkeypatch):
        from qml_main import configure_qml_controls_style

        monkeypatch.delenv("QT_QUICK_CONTROLS_STYLE", raising=False)
        monkeypatch.setattr("qml_main.sys.platform", "darwin")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "macOS"

        monkeypatch.setenv("QT_QUICK_CONTROLS_STYLE", "Basic")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "macOS"

        monkeypatch.setenv("QT_QUICK_CONTROLS_STYLE", "FluentWinUI3")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "macOS"

        monkeypatch.setenv("QT_QUICK_CONTROLS_STYLE", "Fusion")
        configure_qml_controls_style()
        assert os.environ["QT_QUICK_CONTROLS_STYLE"] == "macOS"

    def test_macos_reveals_qml_only_after_configuring_native_chrome(self):
        source = Path("qml_main.py").read_text(encoding="utf-8")

        assert 'root_window.setProperty("startupChromeReady", True)' in source
