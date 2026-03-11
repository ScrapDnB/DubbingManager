"""
Тесты для сервисов Dubbing Manager

Запуск:
    pytest tests/ -v
    
Запуск с покрытием:
    pytest tests/ -v --cov=services --cov-report=html
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

# Импорты сервисов
from services.project_service import ProjectService, MAX_BACKUPS
from services.episode_service import EpisodeService
from services.actor_service import ActorService
from services.export_service import ExportService, EXCEL_AVAILABLE


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_project_data():
    """Пример данных проекта для тестов"""
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
        "episodes": {
            "1": "/path/to/episode1.ass",
        },
        "video_paths": {
            "1": "/path/to/video1.mp4",
        },
        "export_config": {
            'layout_type': 'Таблица',
            'col_tc': True,
            'col_char': True,
            'col_actor': True,
            'col_text': True,
            'f_time': 21,
            'f_char': 20,
            'f_actor': 14,
            'f_text': 30,
            'use_color': True,
            'open_auto': True,
            'round_time': False,
            'allow_edit': True,
        },
        "replica_merge_config": {
            'merge': True,
            'merge_gap': 5,
            'p_short': 0.5,
            'p_long': 2.0,
        },
        "prompter_config": {
            "f_tc": 20,
            "f_char": 24,
            "f_actor": 18,
            "f_text": 36,
            "focus_ratio": 0.5,
        }
    }


@pytest.fixture
def sample_lines():
    """Пример реплик для тестов"""
    return [
        {
            'id': 0,
            's': 0.0,
            'e': 2.5,
            'char': 'Персонаж 1',
            'text': 'Привет, как дела?',
            's_raw': '0:00:00.00'
        },
        {
            'id': 1,
            's': 3.0,
            'e': 5.5,
            'char': 'Персонаж 2',
            'text': 'Всё отлично, спасибо!',
            's_raw': '0:00:03.00'
        },
        {
            'id': 2,
            's': 6.0,
            'e': 8.0,
            'char': 'Персонаж 1',
            'text': 'Рад слышать!',
            's_raw': '0:00:06.00'
        },
    ]


@pytest.fixture
def temp_json_file(sample_project_data):
    """Временный JSON файл с данными проекта"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_project_data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_ass_file():
    """Временный ASS файл с субтитрами"""
    ass_content = """[Script Info]
Title: Test Episode
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.50,Default,Персонаж 1,0,0,0,,Привет, как дела?
Dialogue: 0,0:00:03.00,0:00:05.50,Default,Персонаж 2,0,0,0,,Всё отлично, спасибо!
Dialogue: 0,0:00:06.00,0:00:08.00,Default,Персонаж 1,0,0,0,,Рад слышать!
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
        f.write(ass_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# =============================================================================
# ProjectService Tests
# =============================================================================

class TestProjectService:
    """Тесты для ProjectService"""

    def test_create_new_project(self):
        """Создание нового проекта"""
        service = ProjectService()
        project = service.create_new_project("Новый проект")
        
        assert project["project_name"] == "Новый проект"
        assert "metadata" in project
        assert project["metadata"]["format_version"] == "1.0"
        assert "created_at" in project["metadata"]
        assert "actors" in project
        assert "episodes" in project
        assert "export_config" in project
        assert "prompter_config" in project

    def test_load_project(self, temp_json_file):
        """Загрузка проекта из файла"""
        service = ProjectService()
        data = service.load_project(temp_json_file)
        
        assert data is not None
        assert data["project_name"] == "Тестовый проект"
        assert len(data["actors"]) == 2
        assert service.current_project_path == temp_json_file
        assert service.is_dirty == False

    def test_save_project(self, sample_project_data):
        """Сохранение проекта с атомарностью"""
        service = ProjectService()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            service.current_project_path = temp_path
            result = service.save_project(sample_project_data)
            
            assert result == True
            assert service.is_dirty == False
            
            # Проверка сохранённых данных
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            assert saved_data["project_name"] == "Тестовый проект"
            assert "metadata" in saved_data
            assert "modified_at" in saved_data["metadata"]
            
            # Проверка, что временный файл удалён
            assert not os.path.exists(temp_path + ".tmp")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_set_dirty(self):
        """Установка флага изменений"""
        service = ProjectService()
        
        assert service.is_dirty == False
        service.set_dirty(True)
        assert service.is_dirty == True
        service.set_dirty(False)
        assert service.is_dirty == False

    def test_get_window_title(self, sample_project_data):
        """Формирование заголовка окна"""
        service = ProjectService()
        service.current_project_path = "/path/to/project.json"
        
        title = service.get_window_title(sample_project_data)
        assert "Dubbing Manager" in title
        assert "project.json" in title
        
        # С флагом dirty
        service.set_dirty(True)
        title = service.get_window_title(sample_project_data)
        assert "*" in title

    def test_validate_project_structure(self):
        """Валидация структуры проекта"""
        from services.project_service import ProjectValidationError
        
        service = ProjectService()
        
        # Валидный проект
        valid_data = {
            "project_name": "Test",
            "actors": {},
            "episodes": {},
        }
        service._validate_project_structure(valid_data)  # Не должно вызвать исключение
        
        # Missing поля
        invalid_data = {"project_name": "Test"}
        with pytest.raises(ProjectValidationError):
            service._validate_project_structure(invalid_data)
        
        # Неправильный тип
        invalid_type = {
            "project_name": 123,  # Должно быть строкой
            "actors": {},
            "episodes": {},
        }
        with pytest.raises(ProjectValidationError):
            service._validate_project_structure(invalid_type)

    def test_rotate_backups(self, tmp_path):
        """Ротация бэкапов"""
        service = ProjectService()
        
        # Создаём тестовые бэкапы
        backup_dir = tmp_path / ".backups"
        backup_dir.mkdir()
        
        for i in range(15):  # Создаём 15 бэкапов
            backup_file = backup_dir / f"backup_{i}.json"
            backup_file.write_text("{}")
        
        # Ротация
        service._rotate_backups(backup_dir)
        
        # Должно остаться только MAX_BACKUPS
        remaining = list(backup_dir.glob("*.json"))
        assert len(remaining) == MAX_BACKUPS

    def test_auto_save_with_backup(self, sample_project_data, tmp_path):
        """Автосохранение с бэкапом"""
        service = ProjectService()
        service.current_project_path = str(tmp_path / "project.json")
        service.is_dirty = True
        
        # Автосохранение
        result = service.auto_save(sample_project_data)
        
        assert result == True
        
        # Проверка, что бэкап создан
        backup_dir = tmp_path / ".backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.json"))
        assert len(backups) >= 1

    def test_list_backups(self, sample_project_data, tmp_path):
        """Получение списка бэкапов"""
        service = ProjectService()
        service.current_project_path = str(tmp_path / "project.json")
        
        # Создаём бэкапы
        backup_dir = tmp_path / ".backups"
        backup_dir.mkdir()
        
        for i in range(3):
            backup_file = backup_dir / f"backup_{i}.json"
            backup_file.write_text("{}")
        
        backups = service.list_backups()
        assert len(backups) == 3
        # Отсортированы по времени (новые первые)
        assert backups[0].name == "backup_2.json"

    def test_restore_from_backup(self, sample_project_data, tmp_path):
        """Восстановление из бэкапа"""
        service = ProjectService()
        
        # Создаём бэкап
        backup_dir = tmp_path / ".backups"
        backup_dir.mkdir()
        backup_file = backup_dir / "backup.json"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(sample_project_data, f)
        
        # Восстановление
        target_path = tmp_path / "restored.json"
        result = service.restore_from_backup(str(backup_file), str(target_path))
        
        assert result == True
        assert target_path.exists()
        
        # Проверка данных
        with open(target_path, 'r', encoding='utf-8') as f:
            restored_data = json.load(f)
        
        assert restored_data["project_name"] == "Тестовый проект"

    def test_load_old_project_format(self, tmp_path):
        """Загрузка старого формата проекта (без metadata)"""
        service = ProjectService()
        
        # Создаём старый формат (без metadata)
        old_format = {
            "project_name": "Старый проект",
            "actors": {"actor1": {"name": "Актёр 1", "color": "#FF0000"}},
            "episodes": {"1": "/path/to/episode.ass"},
            # Нет metadata, video_paths, export_config, etc.
        }
        
        old_file = tmp_path / "old_project.json"
        with open(old_file, 'w', encoding='utf-8') as f:
            json.dump(old_format, f)
        
        # Загрузка должна работать
        data = service.load_project(str(old_file))
        
        # Проверка, что данные загрузились
        assert data["project_name"] == "Старый проект"
        assert len(data["actors"]) == 1
        
        # Проверка, что добавлены缺失ствующие поля
        assert "metadata" in data
        assert data["metadata"]["format_version"] == "0.9"
        assert "video_paths" in data
        assert "export_config" in data
        assert "prompter_config" in data
        assert "global_map" in data

    def test_save_old_project_adds_metadata(self, tmp_path):
        """Сохранение старого проекта добавляет metadata"""
        service = ProjectService()
        
        # Старый формат
        old_format = {
            "project_name": "Старый проект",
            "actors": {},
            "episodes": {},
        }
        
        # Загружаем (с совместимостью)
        old_file = tmp_path / "old.json"
        with open(old_file, 'w', encoding='utf-8') as f:
            json.dump(old_format, f)
        
        data = service.load_project(str(old_file))
        
        # Сохраняем
        new_file = tmp_path / "new.json"
        service.current_project_path = str(new_file)
        service.save_project(data)
        
        # Проверка
        with open(new_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "metadata" in saved_data
        assert saved_data["metadata"]["format_version"] == "1.0"
        assert "modified_at" in saved_data["metadata"]


# =============================================================================
# EpisodeService Tests
# =============================================================================

class TestEpisodeService:
    """Тесты для EpisodeService"""

    def test_parse_ass_file(self, temp_ass_file):
        """Парсинг ASS файла"""
        service = EpisodeService()
        stats, lines = service.parse_ass_file(temp_ass_file)
        
        assert len(lines) == 3
        assert len(stats) == 2  # Два персонажа
        
        # Проверка статистики
        char1_stats = next(s for s in stats if s["name"] == "Персонаж 1")
        assert char1_stats["lines"] == 2
        
        char2_stats = next(s for s in stats if s["name"] == "Персонаж 2")
        assert char2_stats["lines"] == 1

    def test_load_episode(self, temp_ass_file):
        """Загрузка эпизода"""
        service = EpisodeService()
        episodes = {"1": temp_ass_file}
        
        lines = service.load_episode("1", episodes)
        
        assert len(lines) == 3
        assert lines[0]["char"] == "Персонаж 1"
        assert lines[0]["text"] == "Привет, как дела?"

    def test_episode_caching(self, temp_ass_file):
        """Кэширование загруженных эпизодов"""
        service = EpisodeService()
        episodes = {"1": temp_ass_file}
        
        # Первая загрузка
        lines1 = service.load_episode("1", episodes)
        
        # Вторая загрузка (из кэша)
        lines2 = service.load_episode("1", episodes)
        
        assert lines1 is lines2  # Один и тот же объект

    def test_invalidate_episode(self, temp_ass_file):
        """Инвалидация кэша эпизода"""
        service = EpisodeService()
        episodes = {"1": temp_ass_file}
        
        # Загрузка
        service.load_episode("1", episodes)
        
        # Инвалидация
        service.invalidate_episode("1")
        
        # Проверка, что кэш очищен
        assert "1" not in service._loaded_episodes

    def test_save_episode_to_ass(self, temp_ass_file):
        """Сохранение эпизода в ASS"""
        service = EpisodeService()
        episodes = {"1": temp_ass_file}
        
        # Изменённые реплики
        mem_lines = [
            {
                'id': 0,
                's': 0.0,
                'e': 2.5,
                'char': 'Новый Персонаж',
                'text': 'Новый текст',
                's_raw': '0:00:00.00'
            },
        ]
        
        success, message = service.save_episode_to_ass("1", episodes, mem_lines)
        
        assert success == True
        
        # Проверка сохранённых данных
        with open(temp_ass_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'Новый Персонаж' in content
        assert 'Новый текст' in content


# =============================================================================
# ActorService Tests
# =============================================================================

class TestActorService:
    """Тесты для ActorService"""

    def test_add_actor(self, sample_project_data):
        """Добавление актёра"""
        service = ActorService()
        actors = sample_project_data["actors"]
        
        initial_count = len(actors)
        actor_id = service.add_actor(actors, "Новый Актёр", "#0000FF")
        
        assert len(actors) == initial_count + 1
        assert actor_id in actors
        assert actors[actor_id]["name"] == "Новый Актёр"
        assert actors[actor_id]["color"] == "#0000FF"

    def test_update_actor_color(self, sample_project_data):
        """Обновление цвета актёра"""
        service = ActorService()
        actors = sample_project_data["actors"]
        
        service.update_actor_color(actors, "actor1", "#FFFF00")
        
        assert actors["actor1"]["color"] == "#FFFF00"

    def test_rename_actor(self, sample_project_data):
        """Переименование актёра"""
        service = ActorService()
        actors = sample_project_data["actors"]
        
        service.rename_actor(actors, "actor1", "Иван Иванович Иванов")
        
        assert actors["actor1"]["name"] == "Иван Иванович Иванов"

    def test_delete_actor(self, sample_project_data):
        """Удаление актёра"""
        service = ActorService()
        actors = sample_project_data["actors"]
        
        initial_count = len(actors)
        result = service.delete_actor(actors, "actor1")
        
        assert result == True
        assert len(actors) == initial_count - 1
        assert "actor1" not in actors

    def test_assign_actor_to_character(self, sample_project_data):
        """Назначение актёра на персонажа"""
        service = ActorService()
        global_map = sample_project_data["global_map"]
        
        service.assign_actor_to_character(global_map, "Новый Персонаж", "actor1")
        
        assert global_map["Новый Персонаж"] == "actor1"
        
        # Удаление назначения
        service.assign_actor_to_character(global_map, "Новый Персонаж", None)
        assert "Новый Персонаж" not in global_map

    def test_bulk_assign_actors(self, sample_project_data):
        """Массовое назначение актёра"""
        service = ActorService()
        global_map = sample_project_data["global_map"]
        
        characters = ["Персонаж 3", "Персонаж 4", "Персонаж 5"]
        count = service.bulk_assign_actors(global_map, characters, "actor1")
        
        assert count == 3
        assert all(global_map.get(char) == "actor1" for char in characters)

    def test_get_actor_roles(self, sample_project_data):
        """Получение списка ролей актёра"""
        service = ActorService()
        global_map = sample_project_data["global_map"]
        
        roles = service.get_actor_roles(global_map, "actor1")
        
        assert "Персонаж 1" in roles
        assert len(roles) >= 1

    def test_update_actor_roles(self, sample_project_data):
        """Обновление ролей актёра"""
        service = ActorService()
        global_map = sample_project_data["global_map"]
        
        new_roles = ["Роль 1", "Роль 2", "Роль 3"]
        service.update_actor_roles(global_map, "actor1", new_roles)
        
        # Старые роли удалены
        assert "Персонаж 1" not in global_map or global_map.get("Персонаж 1") != "actor1"
        
        # Новые роли добавлены
        assert global_map.get("Роль 1") == "actor1"
        assert global_map.get("Роль 2") == "actor1"


# =============================================================================
# ExportService Tests
# =============================================================================

class TestExportService:
    """Тесты для ExportService"""

    def test_process_merge_logic(self, sample_project_data, sample_lines):
        """Логика слияния реплик"""
        service = ExportService(sample_project_data)
        merge_cfg = sample_project_data["replica_merge_config"]

        processed = service.process_merge_logic(sample_lines, merge_cfg)

        assert len(processed) > 0
        assert 'parts' in processed[0]
        assert 'source_ids' in processed[0]

    def test_process_merge_logic_merged(self, sample_project_data):
        """Слияние реплик одного персонажа"""
        service = ExportService(sample_project_data)
        merge_cfg = sample_project_data["replica_merge_config"].copy()
        merge_cfg['merge'] = True
        # 125 кадров = 5 секунд (25 кадров/сек)
        merge_cfg['merge_gap'] = 125

        # Реплики с маленьким интервалом (2.5 секунды)
        lines = [
            {'id': 0, 's': 0.0, 'e': 2.0, 'char': 'Персонаж 1', 'text': 'Реплика 1', 's_raw': '0:00:00.00'},
            {'id': 1, 's': 2.5, 'e': 4.0, 'char': 'Персонаж 1', 'text': 'Реплика 2', 's_raw': '0:00:02.50'},
        ]

        processed = service.process_merge_logic(lines, merge_cfg)

        # Реплики должны быть объединены
        assert len(processed) == 1
        assert 'Реплика 1' in processed[0]['text']
        assert 'Реплика 2' in processed[0]['text']

    def test_process_merge_logic_not_merged(self, sample_project_data):
        """Раздельные реплики"""
        service = ExportService(sample_project_data)
        merge_cfg = sample_project_data["replica_merge_config"].copy()
        merge_cfg['merge'] = False

        lines = [
            {'id': 0, 's': 0.0, 'e': 2.0, 'char': 'Персонаж 1', 'text': 'Реплика 1', 's_raw': '0:00:00.00'},
            {'id': 1, 's': 2.5, 'e': 4.0, 'char': 'Персонаж 1', 'text': 'Реплика 2', 's_raw': '0:00:02.50'},
        ]

        processed = service.process_merge_logic(lines, merge_cfg)

        # Реплики должны быть разделены
        assert len(processed) == 2

    def test_generate_html(self, sample_project_data, sample_lines):
        """Генерация HTML"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        merge_cfg = sample_project_data["replica_merge_config"]

        processed = service.process_merge_logic(sample_lines, merge_cfg)
        html = service.generate_html("1", processed, cfg)

        assert "<html" in html
        assert "</html>" in html
        assert "Тестовый проект" in html
        assert "Серия 1" in html

    def test_generate_html_table_layout(self, sample_project_data, sample_lines):
        """Генерация HTML с табличным макетом"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        merge_cfg = sample_project_data["replica_merge_config"]
        merge_cfg['layout_type'] = 'Таблица'

        processed = service.process_merge_logic(sample_lines, merge_cfg)
        html = service.generate_html("1", processed, cfg, layout_type='Таблица')

        assert "<table" in html
        assert "</table>" in html

    def test_generate_html_scenario_layout(self, sample_project_data, sample_lines):
        """Генерация HTML с макетом сценария"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        merge_cfg = sample_project_data["replica_merge_config"]

        processed = service.process_merge_logic(sample_lines, merge_cfg)
        html = service.generate_html("1", processed, cfg, layout_type='Сценарий')

        assert 'line-container' in html
        assert "<table" not in html

    @pytest.mark.skipif(not EXCEL_AVAILABLE, reason="openpyxl not installed")
    def test_create_excel_book(self, sample_project_data, sample_lines):
        """Создание Excel книги"""
        service = ExportService(sample_project_data)
        cfg = sample_project_data["export_config"]
        merge_cfg = sample_project_data["replica_merge_config"]

        processed = service.process_merge_logic(sample_lines, merge_cfg)
        # Новый API: create_excel_book принимает episodes_data dict
        wb = service.create_excel_book({"1": processed}, cfg)

        assert wb is not None
        # Проверяем что есть листы
        assert len(wb.sheetnames) >= 1

        # Проверяем что данные записаны
        ws = wb["Сводка"] if "Сводка" in wb.sheetnames else wb.active
        assert ws.max_row >= 2  # Заголовок + данные

    @pytest.mark.skipif(not EXCEL_AVAILABLE, reason="openpyxl not installed")
    def test_export_to_excel(self, sample_project_data, sample_lines):
        """Экспорт в Excel файл"""
        service = ExportService(sample_project_data)
        merge_cfg = sample_project_data["replica_merge_config"]

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            success, message = service.export_to_excel("1", sample_lines, merge_cfg, temp_path)

            assert success == True
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_batch(self, sample_project_data, temp_ass_file):
        """Пакетный экспорт"""
        service = ExportService(sample_project_data)

        episodes = {"1": temp_ass_file}

        def get_lines(ep):
            return [
                {'id': 0, 's': 0.0, 'e': 2.0, 'char': 'Персонаж 1', 'text': 'Тест', 's_raw': '0:00:00.00'},
            ]

        with tempfile.TemporaryDirectory() as temp_dir:
            success, message = service.export_batch(
                episodes=episodes,
                get_lines_callback=get_lines,
                do_html=True,
                do_xls=False,
                folder=temp_dir
            )

            assert success == True
            assert os.path.exists(os.path.join(temp_dir, "Тестовый проект - Ep1.html"))


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Интеграционные тесты"""

    def test_full_workflow(self, temp_json_file, temp_ass_file):
        """Полный рабочий процесс"""
        # Загрузка проекта
        project_service = ProjectService()
        data = project_service.load_project(temp_json_file)

        # Обновление пути к эпизоду
        data["episodes"]["1"] = temp_ass_file

        # Загрузка эпизода
        episode_service = EpisodeService()
        lines = episode_service.load_episode("1", data["episodes"])

        assert len(lines) == 3

        # Экспорт
        export_service = ExportService(data)
        merge_cfg = data.get("replica_merge_config", {})
        processed = export_service.process_merge_logic(lines, merge_cfg)
        html = export_service.generate_html("1", processed, data["export_config"])

        assert len(html) > 0
        assert "Тестовый проект" in html


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
