"""
Дополнительные тесты для повышения покрытия

Запуск:
    pytest tests/test_additional.py -v
"""

import pytest
import json
import tempfile
from pathlib import Path

from services.project_service import ProjectService, ProjectValidationError
from services.episode_service import EpisodeService
from services.actor_service import ActorService
from services.export_service import ExportService


# =============================================================================
# ProjectService Additional Tests
# =============================================================================

class TestProjectServiceAdditional:
    """Дополнительные тесты ProjectService"""

    def test_create_project_with_unicode_name(self):
        """Создание проекта с Unicode названием"""
        service = ProjectService()
        project = service.create_new_project("Проект 🎬 项目")
        
        assert project["project_name"] == "Проект 🎬 项目"

    def test_project_with_very_long_name(self):
        """Проект с очень длинным названием"""
        service = ProjectService()
        long_name = "A" * 1000  # 1k символов
        
        project = service.create_new_project(long_name)
        
        assert len(project["project_name"]) == 1000

    def test_save_load_special_characters(self, tmp_path):
        """Сохранение/загрузка со спецсимволами"""
        service = ProjectService()
        project = service.create_new_project("Test")
        
        # Добавляем актёра со спецсимволами
        project["actors"]["actor1"] = {
            "name": "Actor <>&\"",
            "color": "#FF0000"
        }
        
        # Сохраняем
        test_file = tmp_path / "special.json"
        service.current_project_path = str(test_file)
        service.save_project(project)
        
        # Загружаем
        loaded = service.load_project(str(test_file))
        
        assert loaded["actors"]["actor1"]["name"] == "Actor <>&\""

    def test_validate_missing_required_fields(self):
        """Валидация без обязательных полей"""
        service = ProjectService()
        
        invalid_data = {"project_name": "Test"}  # Нет actors и episodes
        
        with pytest.raises(ProjectValidationError):
            service._validate_project_structure(invalid_data)

    def test_validate_wrong_types(self):
        """Валидация с неправильными типами"""
        service = ProjectService()
        
        # project_name должно быть строкой
        invalid_data = {
            "project_name": 123,
            "actors": {},
            "episodes": {},
        }
        
        with pytest.raises(ProjectValidationError):
            service._validate_project_structure(invalid_data)


# =============================================================================
# EpisodeService Additional Tests
# =============================================================================

class TestEpisodeServiceAdditional:
    """Дополнительные тесты EpisodeService"""

    def test_parse_nonexistent_file(self):
        """Парсинг несуществующего файла"""
        service = EpisodeService()
        
        stats, lines = service.parse_ass_file("/nonexistent/file.ass")
        
        assert stats == []
        assert lines == []

    def test_parse_empty_file(self, tmp_path):
        """Парсинг пустого файла"""
        service = EpisodeService()
        
        empty_file = tmp_path / "empty.ass"
        empty_file.write_text("")
        
        stats, lines = service.parse_ass_file(str(empty_file))
        
        assert stats == []
        assert lines == []

    def test_load_nonexistent_episode(self):
        """Загрузка несуществующего эпизода"""
        service = EpisodeService()
        episodes = {"1": "/nonexistent/file.ass"}
        
        lines = service.load_episode("1", episodes)
        
        assert lines == []

    def test_parse_unicode_text(self, tmp_path):
        """Парсинг Unicode текста"""
        service = EpisodeService()
        
        ass_content = """[Script Info]
Title: Test

[Events]
Format: Layer, Start, End, Style, Name, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,Char,0,0,0,,Привет 你好
"""
        
        ass_file = tmp_path / "unicode.ass"
        ass_file.write_text(ass_content, encoding='utf-8')
        
        stats, lines = service.parse_ass_file(str(ass_file))
        
        assert len(lines) == 1
        assert "Привет 你好" in lines[0]['text']


# =============================================================================
# ActorService Additional Tests
# =============================================================================

class TestActorServiceAdditional:
    """Дополнительные тесты ActorService"""

    def test_add_actor_with_unicode_name(self):
        """Добавление актёра с Unicode именем"""
        service = ActorService()
        actors = {}
        
        actor_id = service.add_actor(actors, "イワン・イワノフ 🎭")
        
        assert actors[actor_id]["name"] == "イワン・イワノフ 🎭"

    def test_update_nonexistent_actor_color(self):
        """Обновление цвета несуществующего актёра"""
        service = ActorService()
        actors = {}
        
        result = service.update_actor_color(actors, "nonexistent", "#FF0000")
        
        assert result == False

    def test_rename_nonexistent_actor(self):
        """Переименование несуществующего актёра"""
        service = ActorService()
        actors = {}
        
        result = service.rename_actor(actors, "nonexistent", "New Name")
        
        assert result == False

    def test_delete_nonexistent_actor(self):
        """Удаление несуществующего актёра"""
        service = ActorService()
        actors = {}
        
        result = service.delete_actor(actors, "nonexistent")
        
        assert result == False

    def test_assign_100_characters(self):
        """Назначение актёра на 100 персонажей"""
        service = ActorService()
        global_map = {}
        
        characters = [f"Character {i}" for i in range(100)]
        count = service.bulk_assign_actors(global_map, characters, "actor1")
        
        assert count == 100
        assert len(global_map) == 100


# =============================================================================
# ExportService Additional Tests
# =============================================================================

class TestExportServiceAdditional:
    """Дополнительные тесты ExportService"""

    def test_process_merge_empty_lines(self, sample_project_data):
        """Слияние пустых реплик"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        
        processed = service.process_merge_logic([], cfg)
        
        assert processed == []

    def test_export_with_no_actors_assigned(self, sample_project_data):
        """Экспорт без назначенных актёров"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        
        # Очищаем global_map
        sample_project_data["global_map"] = {}
        
        lines = [
            {'id': 0, 's': 0.0, 'e': 1.0, 'char': 'Char', 'text': 'Text', 's_raw': '0:00:00.00'},
        ]
        
        processed = service.process_merge_logic(lines, cfg)
        html = service.generate_html("1", processed, cfg)
        
        assert "<html" in html

    def test_scenario_layout(self, sample_project_data, sample_lines):
        """Экспорт в формате сценария"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        
        processed = service.process_merge_logic(sample_lines, cfg)
        html = service.generate_html("1", processed, cfg, layout_type='Сценарий')
        
        assert 'line-container' in html
        assert "<table" not in html

    def test_export_100_replicas(self, sample_project_data):
        """Экспорт 100 реплик"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        
        # Создаём 100 реплик
        lines = []
        for i in range(100):
            lines.append({
                'id': i,
                's': float(i),
                'e': float(i) + 0.5,
                'char': 'Char',
                'text': f'Text {i}',
                's_raw': f'0:00:{i:02d}.00'
            })
        
        processed = service.process_merge_logic(lines, cfg)
        html = service.generate_html("1", processed, cfg)
        
        assert len(html) > 0
        assert "Text 0" in html
        assert "Text 99" in html


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_project_data():
    """Пример данных проекта"""
    return {
        "project_name": "Тестовый проект",
        "actors": {
            "actor1": {"name": "Иван Иванов", "color": "#FF0000"},
            "actor2": {"name": "Пётр Петров", "color": "#00FF00"},
        },
        "global_map": {
            "Персонаж 1": "actor1",
            "Персонаж 2": "actor2",
        },
        "episodes": {"1": "/path/to/episode1.ass"},
        "video_paths": {"1": "/path/to/video1.mp4"},
        "export_config": {
            'layout_type': 'Таблица',
            'merge': True,
            'merge_gap': 5,
            'p_short': 0.5,
            'p_long': 2.0,
            'use_color': True,
        },
        "prompter_config": {}
    }


@pytest.fixture
def sample_lines():
    """Пример реплик"""
    return [
        {'id': 0, 's': 0.0, 'e': 2.5, 'char': 'Персонаж 1', 'text': 'Привет', 's_raw': '0:00:00.00'},
        {'id': 1, 's': 3.0, 'e': 5.5, 'char': 'Персонаж 2', 'text': 'Пока', 's_raw': '0:00:03.00'},
    ]


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
