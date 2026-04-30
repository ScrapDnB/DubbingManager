"""Тесты для проверки целостности файла проекта"""

import pytest
import json
import os
import tempfile
import shutil
from datetime import datetime
from services import ProjectService
from config.constants import PROJECT_VERSION


class TestProjectFileStructure:
    """Тесты для проверки структуры файла проекта"""

    def setup_method(self):
        """Создание временной директории для тестов"""
        self.test_dir = tempfile.mkdtemp()
        self.project_service = ProjectService()

    def teardown_method(self):
        """Очистка временной директории"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_new_project_structure(self):
        """Проверка структуры нового проекта"""
        data = self.project_service.create_new_project("Test Project")
        
        # Проверка обязательных полей
        assert "metadata" in data
        assert "project_name" in data
        assert "actors" in data
        assert "global_map" in data
        assert "episodes" in data
        assert "video_paths" in data
        assert "episode_texts" in data
        assert "episode_actor_map" in data
        assert "export_config" in data
        assert "prompter_config" in data
        assert "replica_merge_config" in data
        assert "project_folder" in data
        
        # Проверка metadata
        assert "format_version" in data["metadata"]
        assert "app_version" in data["metadata"]
        assert "created_at" in data["metadata"]
        assert "modified_at" in data["metadata"]
        
        # Проверка типа полей
        assert isinstance(data["actors"], dict)
        assert isinstance(data["global_map"], dict)
        assert isinstance(data["episodes"], dict)
        assert isinstance(data["video_paths"], dict)
        assert isinstance(data["episode_texts"], dict)
        assert isinstance(data["episode_actor_map"], dict)

    def test_save_and_load_project(self):
        """Проверка сохранения и загрузки проекта"""
        # Создаём проект
        data = self.project_service.create_new_project("Test Project")
        
        # Добавляем данные
        data["actors"]["actor1"] = {
            "name": "Actor 1",
            "color": "#FFFFFF",
            "roles": []
        }
        data["global_map"]["Character1"] = "actor1"
        data["episodes"]["1"] = "/path/to/episode1.ass"
        data["video_paths"]["1"] = "/path/to/video1.mp4"
        data["episode_texts"]["1"] = "/path/to/episode_1.json"
        data["project_folder"] = self.test_dir
        
        # Сохраняем
        project_path = os.path.join(self.test_dir, "test_project.json")
        result = self.project_service.save_project(data, project_path)
        assert result is True
        
        # Загружаем
        loaded_data = self.project_service.load_project(project_path)
        
        # Проверяем целостность
        assert loaded_data["project_name"] == "Test Project"
        assert len(loaded_data["actors"]) == 1
        assert loaded_data["actors"]["actor1"]["name"] == "Actor 1"
        assert loaded_data["global_map"]["Character1"] == "actor1"
        assert loaded_data["episodes"]["1"] == "/path/to/episode1.ass"
        assert loaded_data["video_paths"]["1"] == "/path/to/video1.mp4"
        assert loaded_data["episode_texts"]["1"] == "/path/to/episode_1.json"
        assert loaded_data["project_folder"] == self.test_dir

    def test_json_valid_format(self):
        """Проверка валидности JSON"""
        data = self.project_service.create_new_project("Test Project")
        project_path = os.path.join(self.test_dir, "test_project.json")
        
        # Сохраняем
        self.project_service.save_project(data, project_path)
        
        # Читаем как JSON
        with open(project_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Проверяем валидность
        assert json_data is not None
        assert isinstance(json_data, dict)

    def test_unicode_characters_in_project(self):
        """Проверка поддержки Unicode символов"""
        data = self.project_service.create_new_project("Тестовый Проект 🎬")
        
        data["actors"]["actor1"] = {
            "name": "Актёр Ёжик",
            "color": "#FFFFFF",
            "roles": ["Персонаж №1"]
        }
        data["global_map"]["Персонаж Ёжик"] = "actor1"
        
        project_path = os.path.join(self.test_dir, "unicode_project.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        assert loaded_data["project_name"] == "Тестовый Проект 🎬"
        assert loaded_data["actors"]["actor1"]["name"] == "Актёр Ёжик"
        assert loaded_data["global_map"]["Персонаж Ёжик"] == "actor1"

    def test_special_characters_in_paths(self):
        """Проверка путей с специальными символами"""
        data = self.project_service.create_new_project("Test Project")
        
        special_path = "/path/with spaces/and-特殊字符/episode.ass"
        data["episodes"]["1"] = special_path
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        assert loaded_data["episodes"]["1"] == special_path

    def test_large_project_file(self):
        """Проверка большого файла проекта"""
        data = self.project_service.create_new_project("Large Project")
        
        # Добавляем 100 актёров
        for i in range(100):
            data["actors"][f"actor{i}"] = {
                "name": f"Actor {i}",
                "color": "#FFFFFF",
                "roles": []
            }
        
        # Добавляем 100 персонажей
        for i in range(100):
            data["global_map"][f"Character{i}"] = f"actor{i}"
        
        # Добавляем 50 серий
        for i in range(1, 51):
            data["episodes"][str(i)] = f"/path/episode{i}.ass"
            data["video_paths"][str(i)] = f"/path/video{i}.mp4"
        
        project_path = os.path.join(self.test_dir, "large_project.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        assert len(loaded_data["actors"]) == 100
        assert len(loaded_data["global_map"]) == 100
        assert len(loaded_data["episodes"]) == 50
        assert len(loaded_data["video_paths"]) == 50

    def test_config_preservation(self):
        """Проверка сохранения конфигураций"""
        data = self.project_service.create_new_project("Test Project")
        
        # Изменяем конфигурации
        data["export_config"]["layout_type"] = "Сценарий"
        data["export_config"]["use_color"] = False
        data["prompter_config"]["f_tc"] = 30
        data["prompter_config"]["is_mirrored"] = True
        data["replica_merge_config"]["merge"] = False
        data["replica_merge_config"]["merge_gap"] = 10
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        assert loaded_data["export_config"]["layout_type"] == "Сценарий"
        assert loaded_data["export_config"]["use_color"] is False
        assert loaded_data["prompter_config"]["f_tc"] == 30
        assert loaded_data["prompter_config"]["is_mirrored"] is True
        assert loaded_data["replica_merge_config"]["merge"] is False
        assert loaded_data["replica_merge_config"]["merge_gap"] == 10

    def test_metadata_update_on_save(self):
        """Проверка обновления metadata при сохранении"""
        data = self.project_service.create_new_project("Test Project")
        original_modified = data["metadata"]["modified_at"]
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        # modified_at должен обновиться
        assert loaded_data["metadata"]["modified_at"] >= original_modified
        assert loaded_data["metadata"]["format_version"] == PROJECT_VERSION

    def test_project_folder_in_file(self):
        """Проверка сохранения project_folder"""
        data = self.project_service.create_new_project("Test Project")
        data["project_folder"] = self.test_dir
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        # Проверяем файл напрямую
        with open(project_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        assert "project_folder" in json_data
        assert json_data["project_folder"] == self.test_dir
        
        # Проверяем через load_project
        loaded_data = self.project_service.load_project(project_path)
        assert loaded_data["project_folder"] == self.test_dir

    def test_empty_project_folder_field(self):
        """Проверка пустого project_folder"""
        data = self.project_service.create_new_project("Test Project")
        data["project_folder"] = None
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        assert loaded_data["project_folder"] is None

    def test_loaded_episodes_preservation(self):
        """Проверка сохранения загруженных эпизодов"""
        data = self.project_service.create_new_project("Test Project")
        data["loaded_episodes"] = {
            "1": [
                {"id": 0, "s": 10.0, "e": 20.0, "char": "Char1", "text": "Text1"}
            ]
        }
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        assert "loaded_episodes" in loaded_data
        assert len(loaded_data["loaded_episodes"]["1"]) == 1


class TestBackwardCompatibility:
    """Тесты для проверки обратной совместимости"""

    def setup_method(self):
        """Создание временной директории"""
        self.test_dir = tempfile.mkdtemp()
        self.project_service = ProjectService()

    def teardown_method(self):
        """Очистка"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_old_project_without_project_folder(self):
        """Загрузка старого проекта без project_folder"""
        old_data = {
            "project_name": "Old Project",
            "actors": {},
            "global_map": {},
            "episodes": {},
            "video_paths": {},
            "metadata": {
                "format_version": "0.9",
                "app_version": "pre-1.0"
            }
        }
        
        # Сохраняем старый формат
        project_path = os.path.join(self.test_dir, "old.json")
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)
        
        # Загружаем
        loaded_data = self.project_service.load_project(project_path)
        
        # project_folder должен добавиться
        assert "project_folder" in loaded_data
        assert loaded_data["project_folder"] is None

    def test_load_old_project_without_configs(self):
        """Загрузка старого проекта без конфигураций"""
        old_data = {
            "project_name": "Old Project",
            "actors": {},
            "global_map": {},
            "episodes": {}
        }
        
        project_path = os.path.join(self.test_dir, "old.json")
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)
        
        loaded_data = self.project_service.load_project(project_path)
        
        # Конфигурации должны добавиться
        assert "export_config" in loaded_data
        assert "prompter_config" in loaded_data
        assert "replica_merge_config" in loaded_data
        assert "video_paths" in loaded_data
        assert "episode_texts" in loaded_data
        assert "global_map" in loaded_data

    def test_load_old_project_with_export_merge_config(self):
        """Загрузка проекта со старым merge_config в export_config"""
        old_data = {
            "project_name": "Old Project",
            "actors": {},
            "global_map": {},
            "episodes": {},
            "export_config": {
                "merge": True,
                "merge_gap": 7,
                "p_short": 0.3,
                "p_long": 1.5
            }
        }
        
        project_path = os.path.join(self.test_dir, "old.json")
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)
        
        loaded_data = self.project_service.load_project(project_path)
        
        # replica_merge_config должен создаться из export_config
        assert "replica_merge_config" in loaded_data
        assert loaded_data["replica_merge_config"]["merge"] is True
        assert loaded_data["replica_merge_config"]["merge_gap"] == 7

    def test_save_adds_metadata_to_old_project(self):
        """Сохранение добавляет metadata в старый проект"""
        old_data = {
            "project_name": "Old Project",
            "actors": {},
            "global_map": {},
            "episodes": {}
        }
        
        project_path = os.path.join(self.test_dir, "old.json")
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)
        
        loaded_data = self.project_service.load_project(project_path)
        self.project_service.save_project(loaded_data, project_path)
        
        # Проверяем файл
        with open(project_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "metadata" in saved_data
        assert "format_version" in saved_data["metadata"]


class TestDataIntegrity:
    """Тесты для проверки целостности данных"""

    def setup_method(self):
        """Создание временной директории"""
        self.test_dir = tempfile.mkdtemp()
        self.project_service = ProjectService()

    def teardown_method(self):
        """Очистка"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_multiple_save_load_cycles(self):
        """Проверка множественных циклов сохранения/загрузки"""
        data = self.project_service.create_new_project("Test Project")
        data["actors"]["actor1"] = {
            "name": "Actor 1",
            "color": "#FFFFFF",
            "roles": []
        }
        
        project_path = os.path.join(self.test_dir, "test.json")
        
        # 10 циклов сохранения/загрузки
        for i in range(10):
            self.project_service.save_project(data, project_path)
            data = self.project_service.load_project(project_path)
            
            # Проверяем целостность
            assert len(data["actors"]) == 1
            assert data["actors"]["actor1"]["name"] == "Actor 1"

    def test_concurrent_field_updates(self):
        """Проверка обновления нескольких полей одновременно"""
        data = self.project_service.create_new_project("Test Project")
        
        # Обновляем все поля
        data["project_name"] = "Updated Name"
        data["actors"]["a1"] = {"name": "A1", "color": "#FFF", "roles": []}
        data["global_map"]["C1"] = "a1"
        data["episodes"]["1"] = "/path.ass"
        data["video_paths"]["1"] = "/path.mp4"
        data["project_folder"] = self.test_dir
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        # Проверяем все поля
        assert loaded_data["project_name"] == "Updated Name"
        assert len(loaded_data["actors"]) == 1
        assert len(loaded_data["global_map"]) == 1
        assert len(loaded_data["episodes"]) == 1
        assert len(loaded_data["video_paths"]) == 1
        assert loaded_data["project_folder"] == self.test_dir

    def test_nested_data_structures(self):
        """Проверка вложенных структур данных"""
        data = self.project_service.create_new_project("Test Project")
        
        # Создаём сложную вложенную структуру
        data["actors"]["actor1"] = {
            "name": "Actor 1",
            "color": "#FFFFFF",
            "roles": ["Role1", "Role2", "Role3"]
        }
        
        data["prompter_config"]["colors"] = {
            "bg": "#000000",
            "active_text": "#FFFFFF",
            "inactive_text": "#444444"
        }
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        loaded_data = self.project_service.load_project(project_path)
        
        assert len(loaded_data["actors"]["actor1"]["roles"]) == 3
        assert loaded_data["prompter_config"]["colors"]["bg"] == "#000000"

    def test_file_size_reasonable(self):
        """Проверка разумного размера файла"""
        data = self.project_service.create_new_project("Test Project")
        
        # Добавляем умеренное количество данных
        for i in range(50):
            data["actors"][f"actor{i}"] = {
                "name": f"Actor {i}",
                "color": "#FFFFFF",
                "roles": []
            }
        
        for i in range(20):
            data["episodes"][str(i)] = f"/path/episode{i}.ass"
        
        project_path = os.path.join(self.test_dir, "test.json")
        self.project_service.save_project(data, project_path)
        
        # Проверяем размер файла
        file_size = os.path.getsize(project_path)
        assert file_size < 1024 * 1024  # Менее 1MB

    def test_atomic_save(self):
        """Проверка атомарности сохранения"""
        data = self.project_service.create_new_project("Test Project")
        project_path = os.path.join(self.test_dir, "test.json")
        
        # Сохраняем
        self.project_service.save_project(data, project_path)
        
        # Проверяем, что временный файл удалён
        temp_path = project_path + ".tmp"
        assert not os.path.exists(temp_path)
        
        # Проверяем, что основной файл существует
        assert os.path.exists(project_path)
