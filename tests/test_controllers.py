"""Тесты для контроллеров UI"""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch, call
from typing import Dict, List, Any

from ui.controllers import (
    EpisodeController,
    ExportController,
    ProjectController,
    ActorController,
)
from services import EpisodeService, ActorService, ProjectService, ExportService


# =============================================================================
# EpisodeController Tests
# =============================================================================

class TestEpisodeController:
    """Тесты для EpisodeController"""

    @pytest.fixture
    def episode_service(self):
        """Мокированный episode_service"""
        service = MagicMock(spec=EpisodeService)
        service.load_episode.return_value = [
            {"id": 1, "s": 0.0, "e": 2.0, "char": "Char1", "text": "Hello", "s_raw": "0:00:00.00"}
        ]
        service.load_srt_episode.return_value = [
            {"id": 1, "s": 0.0, "e": 2.0, "char": "Char1", "text": "Hello", "s_raw": "0:00:00.00"}
        ]
        service.save_episode_to_ass.return_value = (True, "Saved")
        service.save_episode_to_srt.return_value = (True, "Saved")
        service.invalidate_episode = MagicMock()
        return service

    @pytest.fixture
    def data_ref(self) -> Dict[str, Any]:
        """Данные проекта для тестов"""
        return {
            "episodes": {"1": "/path/to/ep1.ass"},
            "loaded_episodes": {},
            "video_paths": {},
        }

    @pytest.fixture
    def controller(self, episode_service, data_ref) -> EpisodeController:
        """Создание контроллера"""
        return EpisodeController(
            episode_service=episode_service,
            data_ref=data_ref,
            on_dirty_callback=lambda: None
        )

    def test_change_episode_ass(self, controller, episode_service, data_ref):
        """Тест смены эпизода ASS"""
        # Мокируем os.path.exists
        with patch('ui.controllers.episode_controller.os.path.exists', return_value=True):
            lines = controller.change_episode("1")
        
        assert len(lines) == 1
        episode_service.load_episode.assert_called_once()
        assert "1" in data_ref["loaded_episodes"]

    def test_change_episode_srt(self, controller, episode_service, data_ref):
        """Тест смены SRT эпизода"""
        data_ref["episodes"]["1"] = "/path/to/ep1.srt"
        
        with patch('ui.controllers.episode_controller.os.path.exists', return_value=True):
            lines = controller.change_episode("1")
        
        assert len(lines) == 1
        episode_service.load_srt_episode.assert_called_once()

    def test_change_episode_not_found(self, controller, data_ref):
        """Тест эпизода без файла"""
        data_ref["episodes"] = {}
        
        lines = controller.change_episode("99")
        
        assert lines == []

    def test_import_ass_with_paths(self, controller, data_ref):
        """Тест импорта ASS файлов"""
        paths = ["/path/to/S01E01.ass", "/path/to/S01E02.ass"]
        
        success, message = controller.import_ass(paths)
        
        assert success == True
        assert "S01E01.ass" in data_ref["episodes"].values() or "1" in data_ref["episodes"]

    def test_import_ass_no_paths(self, controller):
        """Тест импорта ASS без путей (диалог)"""
        with patch('ui.controllers.episode_controller.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = (["/path/to/file.ass"], "")
            
            success, message = controller.import_ass(None, parent_widget=None)
            
            assert success == True
            mock_dialog.assert_called_once()

    def test_import_srt(self, controller, data_ref):
        """Тест импорта SRT"""
        paths = ["/path/to/ep1.srt"]
        
        success, message = controller.import_srt(paths)
        
        assert success == True

    def test_import_docx(self, controller):
        """Тест импорта DOCX"""
        with patch('ui.controllers.episode_controller.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = (["/path/to/file.docx"], "")
            
            success, message = controller.import_docx(None, parent_widget=None)
            
            assert success == True
            assert ".docx" in message

    def test_save_episode_ass(self, controller, episode_service, data_ref):
        """Тест сохранения эпизода ASS"""
        data_ref["loaded_episodes"] = {"1": [{"id": 1, "char": "Test", "text": "Hello", "s": 0, "e": 1}]}
        data_ref["episodes"] = {"1": "/path/to/ep1.ass"}
        
        success, message = controller.save_episode("1")
        
        assert success == True
        episode_service.save_episode_to_ass.assert_called()

    def test_save_episode_working_text_does_not_write_ass(
        self,
        controller,
        episode_service,
        data_ref
    ):
        """Тест: рабочий текст не записывается обратно в ASS"""
        data_ref["loaded_episodes"] = {
            "1": [
                {
                    "id": 0,
                    "char": "Test",
                    "text": "Edited merged line",
                    "s": 0,
                    "e": 1,
                    "_working_text": True
                }
            ]
        }
        data_ref["episodes"] = {"1": "/path/to/ep1.ass"}

        success, message = controller.save_episode("1")

        assert success == True
        assert "Рабочий текст" in message
        episode_service.save_episode_to_ass.assert_not_called()

    def test_save_episode_working_text_copy_is_rejected(
        self,
        controller,
        episode_service,
        data_ref
    ):
        """Тест: рабочий текст нельзя сохранить копией ASS/SRT"""
        data_ref["loaded_episodes"] = {
            "1": [{"id": 0, "char": "Test", "text": "Edited", "_working_text": True}]
        }

        success, message = controller.save_episode("1", "/tmp/copy.ass")

        assert success == False
        assert "нельзя сохранить" in message
        episode_service.save_episode_to_ass.assert_not_called()

    def test_save_episode_srt(self, controller, episode_service, data_ref):
        """Тест сохранения SRT эпизода"""
        data_ref["loaded_episodes"] = {"1": [{"id": 1, "char": "Test", "text": "Hello", "s": 0, "e": 1}]}
        data_ref["episodes"] = {"1": "/path/to/ep1.srt"}
        
        success, message = controller.save_episode("1")
        
        assert success == True
        episode_service.save_episode_to_srt.assert_called()

    def test_save_episode_not_loaded(self, controller):
        """Тест сохранения незагруженного эпизода"""
        success, message = controller.save_episode("99")
        
        assert success == False

    def test_rename_episode(self, controller, data_ref):
        """Тест переименования эпизода"""
        data_ref["episodes"] = {"1": "/path/to/ep1.ass"}
        data_ref["video_paths"] = {"1": "/path/to/video1.mp4"}
        data_ref["loaded_episodes"] = {"1": []}
        
        success = controller.rename_episode("1", "2")
        
        assert success == True
        assert "2" in data_ref["episodes"]
        assert "1" not in data_ref["episodes"]

    def test_rename_episode_same_name(self, controller):
        """Тест переименования с тем же именем"""
        success = controller.rename_episode("1", "1")
        
        assert success == False

    def test_delete_episode(self, controller, data_ref):
        """Тест удаления эпизода"""
        data_ref["episodes"] = {"1": "/path/to/ep1.ass"}
        data_ref["video_paths"] = {"1": "/path/to/video1.mp4"}
        data_ref["loaded_episodes"] = {"1": []}
        
        success = controller.delete_episode("1")
        
        assert success == True
        assert "1" not in data_ref["episodes"]

    def test_delete_episode_not_found(self, controller):
        """Тест удаления несуществующего эпизода"""
        success = controller.delete_episode("99")
        
        assert success == False

    def test_extract_episode_number_patterns(self, controller):
        """Тест извлечения номера эпизода"""
        # S01E01
        assert controller._extract_episode_number("/path/S01E01.ass") == "1"
        # 1x01
        assert controller._extract_episode_number("/path/1x01.ass") == "1"
        # Ep. 5
        assert controller._extract_episode_number("/path/Ep. 5.ass") == "5"
        # Just numbers
        assert controller._extract_episode_number("/path/Episode_10.ass") == "10"

    def test_get_episode_list(self, controller, data_ref):
        """Тест получения списка эпизодов"""
        data_ref["episodes"] = {"3": "ep3.ass", "1": "ep1.ass", "2": "ep2.ass"}
        
        episodes = controller.get_episode_list()
        
        assert episodes == ["1", "2", "3"]

    def test_invalidate_episode_cache(self, controller, episode_service, data_ref):
        """Тест инвалидации кэша"""
        data_ref["loaded_episodes"] = {"1": []}
        
        controller.invalidate_episode_cache("1")
        
        episode_service.invalidate_episode.assert_called_once_with("1")
        assert "1" not in data_ref["loaded_episodes"]


# =============================================================================
# ExportController Tests
# =============================================================================

class TestExportController:
    """Тесты для ExportController"""

    @pytest.fixture
    def data_ref(self, tmp_path) -> Dict[str, Any]:
        """Данные проекта для тестов"""
        text_path = tmp_path / "episode_1.json"
        text_path.write_text(
            """{
                "format_version": "1.0",
                "episode": "1",
                "source": {"type": "ass", "path": "/path/to/ep1.ass"},
                "merge_config": {"merge": false},
                "characters": {
                    "Char1": {"display_name": "Char1"},
                    "Char2": {"display_name": "Char2"}
                },
                "lines": [
                    {
                        "id": "1_0001",
                        "source_ids": [1],
                        "start": 0.0,
                        "end": 2.0,
                        "character": "Char1",
                        "display_character": "Char1",
                        "text": "Hello",
                        "source_texts": ["Hello"]
                    },
                    {
                        "id": "1_0002",
                        "source_ids": [2],
                        "start": 3.0,
                        "end": 4.0,
                        "character": "Char2",
                        "display_character": "Char2",
                        "text": "Hi",
                        "source_texts": ["Hi"]
                    }
                ]
            }""",
            encoding="utf-8"
        )
        return {
            "project_name": "Test Project",
            "actors": {
                "actor1": {"name": "Actor One", "color": "#FF0000"},
                "actor2": {"name": "Actor Two", "color": "#00FF00"},
            },
            "global_map": {"Char1": "actor1", "Char2": "actor2"},
            "export_config": {"layout_type": "Таблица", "use_color": True},
            "replica_merge_config": {"merge": False},
            "loaded_episodes": {
                "1": [
                    {"id": 1, "s": 0.0, "e": 2.0, "char": "Char1", "text": "Hello", "s_raw": "0:00:00.00"},
                    {"id": 2, "s": 3.0, "e": 4.0, "char": "Char2", "text": "Hi", "s_raw": "0:00:03.00"},
                ]
            },
            "episodes": {"1": "/path/to/ep1.ass"},
            "episode_texts": {"1": str(text_path)},
        }

    @pytest.fixture
    def episode_service(self):
        """Мокированный episode_service"""
        return MagicMock(spec=EpisodeService)

    @pytest.fixture
    def controller(self, data_ref, episode_service) -> ExportController:
        """Создание контроллера"""
        return ExportController(
            data_ref=data_ref,
            episode_service=episode_service,
            on_dirty_callback=lambda: None
        )

    def test_export_to_html(self, controller, data_ref):
        """Тест экспорта в HTML"""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name
        
        try:
            success, message = controller.export_to_html("1", path)
            
            assert success == True
            assert os.path.exists(path)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<html>" in content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_html_uses_saved_highlight_filter(self, controller, data_ref):
        """Тест экспорта HTML с выбранными актёрами из настроек"""
        data_ref["export_config"]["highlight_ids_export"] = ["actor1"]

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name

        try:
            success, message = controller.export_to_html("1", path)

            assert success == True
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "rgba(255, 0, 0, 0.22)" in content
            assert "rgba(0, 255, 0, 0.22)" not in content
            assert "Char2" in content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_html_prefers_working_text(self, controller, data_ref, tmp_path):
        """Тест экспорта HTML из рабочего текста эпизода"""
        text_path = tmp_path / "episode_1.json"
        text_path.write_text(
            """{
                "format_version": "1.0",
                "episode": "1",
                "source": {"type": "ass", "path": "/source.ass"},
                "merge_config": {"merge": false},
                "characters": {"Char1": {"display_name": "Renamed"}},
                "lines": [{
                    "id": "1_0001",
                    "source_ids": [0],
                    "start": 1.0,
                    "end": 2.0,
                    "character": "Char1",
                    "display_character": "Renamed",
                    "text": "Text from working json",
                    "source_texts": ["Old text"]
                }]
            }""",
            encoding="utf-8"
        )
        data_ref["episode_texts"] = {"1": str(text_path)}
        data_ref["loaded_episodes"]["1"] = [
            {"id": 0, "s": 1.0, "e": 2.0, "char": "Char1", "text": "Old text", "s_raw": ""}
        ]

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name

        try:
            success, message = controller.export_to_html("1", path)

            assert success == True
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "Text from working json" in content
            assert "Renamed" in content
            assert "Old text" not in content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_html_no_data(self, controller):
        """Тест экспорта HTML без данных"""
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name
        
        try:
            success, message = controller.export_to_html("99", path)
            
            assert success == False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_html_requires_working_text(self, controller, data_ref):
        """Тест: экспорт не берёт текст напрямую из ASS/SRT кэша."""
        data_ref["episode_texts"] = {}
        data_ref["loaded_episodes"]["1"] = [
            {"id": 1, "s": 0.0, "e": 2.0, "char": "Char1", "text": "ASS text"}
        ]

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name

        try:
            success, message = controller.export_to_html("1", path)

            assert success is False
            assert "рабочий текст" in message
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_excel(self, controller, data_ref):
        """Тест экспорта в Excel"""
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        
        try:
            success, message = controller.export_to_excel("1", path)
            
            assert success == True
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_excel_all_episodes(self, controller, data_ref):
        """Тест экспорта Excel всех эпизодов"""
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        
        try:
            success, message = controller.export_to_excel("1", path, all_episodes=True)
            
            assert success == True
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_export_to_reaper_rpp(self, controller, data_ref):
        """Тест экспорта в Reaper RPP"""
        with tempfile.NamedTemporaryFile(suffix='.Rpp', delete=False) as f:
            path = f.name
        
        try:
            success, message = controller.export_to_reaper_rpp("1", path)
            
            assert success == True
            assert os.path.exists(path)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<REAPER_PROJECT" in content
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_export_preview(self, controller, data_ref):
        """Тест получения превью экспорта"""
        preview = controller.get_export_preview("1")
        
        assert "<html>" in preview
        assert "Char1" in preview

    def test_run_unified_export_html(self, controller, data_ref):
        """Тест универсального экспорта HTML"""
        with patch('ui.controllers.export_controller.QFileDialog.getSaveFileName') as mock_save:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                path = f.name

            try:
                mock_save.return_value = (path, "")
                
                success, message = controller.run_unified_export(
                    "1", export_html=True, export_xls=False, parent_widget=None
                )
                
                assert success == True
            finally:
                if os.path.exists(path):
                    os.unlink(path)

    def test_mark_dirty(self, controller):
        """Тест пометки изменений"""
        dirty_called = []
        
        def mark_dirty():
            dirty_called.append(True)
        
        controller.on_dirty_callback = mark_dirty
        controller._mark_dirty()
        
        assert len(dirty_called) == 1


# =============================================================================
# ProjectController Tests
# =============================================================================

class TestProjectController:
    """Тесты для ProjectController"""

    @pytest.fixture
    def project_service(self):
        """Мокированный project_service"""
        service = MagicMock(spec=ProjectService)
        service.is_dirty = False
        service.current_project_path = None
        service.create_new_project.return_value = {"project_name": "Test"}
        service.save_project.return_value = True
        service.save_project_as.return_value = True
        service.load_project.return_value = {"project_name": "Loaded"}
        service.auto_save.return_value = True
        service.get_window_title.return_value = "Test - Dubbing Manager"
        service.get_project_name.return_value = "Test"
        service.get_backup_directory.return_value = "/backups"
        service.list_backups.return_value = []
        service.restore_from_backup.return_value = True
        return service

    @pytest.fixture
    def undo_stack(self):
        """Мокированный undo_stack"""
        stack = MagicMock()
        stack.push = MagicMock()
        return stack

    @pytest.fixture
    def data_ref(self) -> Dict[str, Any]:
        """Данные проекта"""
        return {"project_name": "Test"}

    @pytest.fixture
    def controller(self, project_service, undo_stack, data_ref) -> ProjectController:
        """Создание контроллера"""
        return ProjectController(
            project_service=project_service,
            data_ref=data_ref,
            undo_stack=undo_stack,
            on_dirty_callback=lambda: None
        )

    def test_create_new_project(self, controller, project_service):
        """Тест создания нового проекта"""
        result = controller.create_new_project("New Project")
        
        project_service.create_new_project.assert_called_once_with("New Project")
        assert result == {"project_name": "Test"}

    def test_save_project(self, controller, project_service):
        """Тест сохранения проекта"""
        project_service.current_project_path = "/path/project.json"
        
        success = controller.save_project()
        
        assert success == True
        project_service.save_project.assert_called()

    def test_save_project_as(self, controller, project_service):
        """Тест сохранения проекта как..."""
        success = controller.save_project_as("/path/new.json")
        
        assert success == True
        project_service.save_project_as.assert_called()

    def test_load_project(self, controller, project_service, data_ref):
        """Тест загрузки проекта"""
        result = controller.load_project("/path/project.json")
        
        assert result is not None
        project_service.load_project.assert_called_once_with("/path/project.json")

    def test_maybe_save_not_dirty(self, controller, project_service):
        """Тест проверки сохранения (не грязный)"""
        project_service.is_dirty = False
        
        result = controller.maybe_save(None)
        
        assert result == True

    def test_maybe_save_dirty_save(self, controller, project_service):
        """Тест проверки сохранения (грязный, сохраняем)"""
        project_service.is_dirty = True
        project_service.save_project.return_value = True
        
        mock_parent = MagicMock()
        with patch('ui.controllers.project_controller.QMessageBox.question', return_value=2048):  # Save
            result = controller.maybe_save(mock_parent)
            
            assert result == True
            project_service.save_project.assert_called()

    def test_maybe_save_dirty_discard(self, controller, project_service):
        """Тест проверки сохранения (грязный, отменяем)"""
        project_service.is_dirty = True
        
        mock_parent = MagicMock()
        with patch('ui.controllers.project_controller.QMessageBox.question', return_value=8388608):  # Discard
            result = controller.maybe_save(mock_parent)
            
            assert result == True

    def test_maybe_save_dirty_cancel(self, controller, project_service):
        """Тест проверки сохранения (грязный, отмена)"""
        project_service.is_dirty = True
        
        mock_parent = MagicMock()
        with patch('ui.controllers.project_controller.QMessageBox.question', return_value=4194304):  # Cancel
            result = controller.maybe_save(mock_parent)
            
            assert result == False

    def test_update_project_name(self, controller, undo_stack):
        """Тест обновления названия проекта"""
        controller.update_project_name("New Name")
        
        undo_stack.push.assert_called_once()

    def test_set_project_folder(self, controller, undo_stack):
        """Тест установки папки проекта"""
        controller.set_project_folder("/path/to/folder")
        
        undo_stack.push.assert_called_once()

    def test_auto_save(self, controller, project_service):
        """Тест автосохранения"""
        success = controller.auto_save()
        
        assert success == True
        project_service.auto_save.assert_called()

    def test_get_window_title(self, controller, project_service):
        """Тест получения заголовка окна"""
        title = controller.get_window_title()
        
        assert title == "Test - Dubbing Manager"
        project_service.get_window_title.assert_called()

    def test_get_project_name(self, controller, project_service):
        """Тест получения названия проекта"""
        name = controller.get_project_name()
        
        assert name == "Test"
        project_service.get_project_name.assert_called()

    def test_set_dirty(self, controller, project_service):
        """Тест установки флага изменений"""
        controller.set_dirty(True)
        
        project_service.set_dirty.assert_called_once_with(True)

    def test_get_backup_directory(self, controller, project_service):
        """Тест получения директории бэкапов"""
        path = controller.get_backup_directory()
        
        assert path == "/backups"
        project_service.get_backup_directory.assert_called()

    def test_list_backups(self, controller, project_service):
        """Тест получения списка бэкапов"""
        backups = controller.list_backups()
        
        assert backups == []
        project_service.list_backups.assert_called()

    def test_restore_from_backup(self, controller, project_service):
        """Тест восстановления из бэкапа"""
        success = controller.restore_from_backup("/backup.json", "/target.json")
        
        assert success == True
        project_service.restore_from_backup.assert_called()

    def test_get_current_project_path(self, controller, project_service):
        """Тест получения пути к проекту"""
        project_service.current_project_path = "/path/project.json"
        
        path = controller.get_current_project_path()
        
        assert path == "/path/project.json"

    def test_set_current_project_path(self, controller, project_service):
        """Тест установки пути к проекту"""
        controller.set_current_project_path("/new/path.json")
        
        assert project_service.current_project_path == "/new/path.json"


# =============================================================================
# ActorController Tests
# =============================================================================

@pytest.mark.skip(reason="Requires pytest-qt for actual widget testing")
class TestActorController:
    """Тесты для ActorController"""

    @pytest.fixture
    def actor_service(self):
        """Мокированный actor_service"""
        service = MagicMock(spec=ActorService)
        service.add_actor.return_value = "actor123"
        return service

    @pytest.fixture
    def actor_table(self):
        """Мокированная таблица актёров"""
        table = MagicMock()
        table.rowCount.return_value = 0
        table.columnCount.return_value = 3
        table.selectionModel.return_value.selectedRows.return_value = []
        return table

    @pytest.fixture
    def data_ref(self) -> Dict[str, Any]:
        """Данные проекта"""
        return {
            "actors": {
                "actor1": {"name": "Actor One", "color": "#FF0000", "roles": []},
                "actor2": {"name": "Actor Two", "color": "#00FF00", "roles": []},
            },
            "global_map": {"Char1": "actor1"},
        }

    @pytest.fixture
    def controller(self, actor_table, actor_service, data_ref) -> ActorController:
        """Создание контроллера"""
        return ActorController(
            actor_table=actor_table,
            actor_service=actor_service,
            data_ref=data_ref,
            on_dirty_callback=lambda: None,
            on_edit_roles_callback=lambda a, n, r: None,
            on_color_click_callback=lambda aid: None,
        )

    def test_add_actor(self, controller, actor_service):
        """Тест добавления актёра"""
        actor_id = controller.add_actor("New Actor", "#FFFFFF")
        
        assert actor_id == "actor123"
        actor_service.add_actor.assert_called()

    def test_bulk_assign_actors(self, controller, actor_service, data_ref):
        """Тест массового назначения актёров"""
        controller.bulk_assign_actors(["Char1", "Char2"], "actor1")
        
        actor_service.bulk_assign_actors.assert_called()

    def test_get_actor_roles(self, controller, actor_service, data_ref):
        """Тест получения ролей актёра"""
        roles = controller.get_actor_roles("actor1")
        
        actor_service.get_actor_roles.assert_called()

    def test_get_unassigned_characters(self, controller, actor_service, data_ref):
        """Тест получения неназначенных персонажей"""
        controller.get_unassigned_characters()
        
        actor_service.get_unassigned_characters.assert_called()

    def test_find_actor_row_found(self, controller, actor_table, data_ref):
        """Тест поиска строки актёра (найден)"""
        item = MagicMock()
        item.data.return_value = "actor1"
        actor_table.rowCount.return_value = 2
        actor_table.item.return_value = item
        
        row = controller._find_actor_row("actor1")
        
        assert row is not None

    def test_find_actor_row_not_found(self, controller, actor_table):
        """Тест поиска строки актёра (не найден)"""
        actor_table.rowCount.return_value = 0
        
        row = controller._find_actor_row("actor999")
        
        assert row is None

    def test_get_actor_roles_helper(self, controller, data_ref):
        """Тест вспомогательного метода получения ролей"""
        roles = controller._get_actor_roles()
        
        assert "actor1" in roles
        assert "Char1" in roles["actor1"]

    def test_on_cell_clicked(self, controller, actor_table):
        """Тест клика по ячейке"""
        item = MagicMock()
        item.data.return_value = "actor1"
        actor_table.item.return_value = item
        
        controller._on_cell_clicked(0, 2)
        
        controller.on_color_click_callback.assert_called_once_with("actor1")

    def test_on_cell_clicked_wrong_column(self, controller):
        """Тест клика по неправильной колонке"""
        controller._on_cell_clicked(0, 0)
        
        controller.on_color_click_callback.assert_not_called()

    def test_mark_dirty(self, controller):
        """Тест пометки изменений"""
        dirty_called = []
        
        def mark_dirty():
            dirty_called.append(True)
        
        controller.on_dirty_callback = mark_dirty
        controller._mark_dirty()
        
        assert len(dirty_called) == 1
