"""Тесты для global_settings_service.py"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.global_settings_service import (
    GlobalSettingsService,
    SETTINGS_FILE,
)
from config.constants import (
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
)


class TestGlobalSettingsService:
    """Тесты для GlobalSettingsService"""

    @pytest.fixture
    def temp_settings_file(self, tmp_path):
        """Временный файл настроек"""
        settings_file = tmp_path / "global_settings.json"
        with patch('services.global_settings_service.SETTINGS_FILE', settings_file):
            yield settings_file

    @pytest.fixture
    def service(self, temp_settings_file):
        """Сервис с временным файлом"""
        return GlobalSettingsService()

    def test_load_settings_file_not_found(self, service, temp_settings_file):
        """Тест загрузки при отсутствии файла"""
        settings = service.load_settings()
        
        assert settings['export_config'] == DEFAULT_EXPORT_CONFIG
        assert settings['prompter_config'] == DEFAULT_PROMPTER_CONFIG
        assert settings['replica_merge_config'] == DEFAULT_REPLICA_MERGE_CONFIG

    def test_load_settings_with_data(self, service, temp_settings_file):
        """Тест загрузки с данными"""
        test_data = {
            'export_config': {'layout_type': 'Сценарий'},
            'prompter_config': {'f_tc': 30},
            'replica_merge_config': {'merge_gap': 10}
        }
        
        temp_settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_settings_file, 'w') as f:
            json.dump(test_data, f)
        
        settings = service.load_settings()
        
        assert settings['export_config']['layout_type'] == 'Сценарий'
        assert settings['prompter_config']['f_tc'] == 30
        assert settings['replica_merge_config']['merge_gap'] == 10

    def test_load_settings_with_colors(self, service, temp_settings_file):
        """Тест загрузки с цветами"""
        test_data = {
            'prompter_config': {
                'colors': {'bg': '#FFFFFF'}
            }
        }
        
        temp_settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_settings_file, 'w') as f:
            json.dump(test_data, f)
        
        settings = service.load_settings()
        
        assert settings['prompter_config']['colors']['bg'] == '#FFFFFF'

    def test_load_settings_invalid_json(self, service, temp_settings_file):
        """Тест загрузки с невалидным JSON"""
        temp_settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_settings_file, 'w') as f:
            f.write("invalid json {")
        
        settings = service.load_settings()
        
        assert settings['export_config'] == DEFAULT_EXPORT_CONFIG

    def test_save_settings(self, service, temp_settings_file):
        """Тест сохранения настроек"""
        settings = {
            'export_config': {'layout_type': 'Таблица'},
            'prompter_config': {'f_tc': 25},
            'replica_merge_config': {'merge': True},
            'docx_import_config': {
                'mapping': {'character': 0, 'text': 2},
                'time_separators': ['-', '|']
            }
        }
        
        result = service.save_settings(settings)
        
        assert result == True
        assert temp_settings_file.exists()
        
        with open(temp_settings_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['export_config']['layout_type'] == 'Таблица'
        assert saved_data['prompter_config']['f_tc'] == 25
        assert saved_data['docx_import_config']['mapping']['text'] == 2

    def test_save_settings_creates_directory(self, service, tmp_path):
        """Тест создания директории при сохранении"""
        nested_file = tmp_path / "nested" / "dir" / "settings.json"
        
        with patch('services.global_settings_service.SETTINGS_FILE', nested_file):
            new_service = GlobalSettingsService()
            result = new_service.save_settings({})
        
        assert result == True
        assert nested_file.exists()

    def test_save_settings_io_error(self, service, temp_settings_file):
        """Тест сохранения с ошибкой IO"""
        with patch('services.global_settings_service.open', side_effect=IOError("Disk full")):
            result = service.save_settings({})
        
        assert result == False

    def test_get_settings_empty(self, service):
        """Тест получения пустых настроек"""
        service.settings = {}
        
        settings = service.get_settings()
        
        assert settings['export_config'] == DEFAULT_EXPORT_CONFIG

    def test_get_settings_loaded(self, service):
        """Тест получения загруженных настроек"""
        service.settings = {'custom': 'value'}
        
        settings = service.get_settings()
        
        assert settings['custom'] == 'value'

    def test_get_export_config(self, service):
        """Тест получения настроек экспорта"""
        service.settings = {'export_config': {'col_tc': False}}
        
        config = service.get_export_config()
        
        assert config['col_tc'] == False

    def test_get_export_config_default(self, service):
        """Тест получения настроек экспорта по умолчанию"""
        service.settings = {}
        
        config = service.get_export_config()
        
        assert config['col_tc'] == True  # Значение по умолчанию

    def test_get_prompter_config(self, service):
        """Тест получения настроек суфлёра"""
        service.settings = {'prompter_config': {'f_tc': 50}}
        
        config = service.get_prompter_config()
        
        assert config['f_tc'] == 50

    def test_get_prompter_config_default(self, service):
        """Тест получения настроек суфлёра по умолчанию"""
        service.settings = {}
        
        config = service.get_prompter_config()
        
        assert config['f_tc'] == 20  # Значение по умолчанию

    def test_get_replica_merge_config(self, service):
        """Тест получения настроек объединения"""
        service.settings = {'replica_merge_config': {'merge_gap': 100}}
        
        config = service.get_replica_merge_config()
        
        assert config['merge_gap'] == 100

    def test_get_replica_merge_config_default(self, service):
        """Тест получения настроек объединения по умолчанию"""
        service.settings = {}
        
        config = service.get_replica_merge_config()
        
        assert config['merge_gap'] == 120  # Значение по умолчанию из constants.py

    def test_update_export_config(self, service):
        """Тест обновления настроек экспорта"""
        service.settings = {}
        
        service.update_export_config({'col_tc': False, 'col_char': False})
        
        assert service.settings['export_config']['col_tc'] == False
        assert service.settings['export_config']['col_char'] == False

    def test_update_prompter_config(self, service):
        """Тест обновления настроек суфлёра"""
        service.settings = {}
        
        service.update_prompter_config({'f_tc': 100})
        
        assert service.settings['prompter_config']['f_tc'] == 100

    def test_update_replica_merge_config(self, service):
        """Тест обновления настроек объединения"""
        service.settings = {}
        
        service.update_replica_merge_config({'merge': False})
        
        assert service.settings['replica_merge_config']['merge'] == False

    def test_update_docx_import_config(self, service):
        """Тест обновления настроек импорта DOCX"""
        service.settings = {}

        service.update_docx_import_config({
            'mapping': {'character': 0, 'text': 3},
            'time_separators': ['-', '|']
        })

        assert service.settings['docx_import_config']['mapping']['text'] == 3
        assert service.settings['docx_import_config']['time_separators'] == ['-', '|']

    def test_get_settings_file_path_windows(self):
        """Тест пути к файлу на Windows"""
        with patch('services.global_settings_service.sys.platform', 'win32'):
            with patch('services.global_settings_service.os.environ.get', return_value='C:\\Users\\test\\AppData\\Roaming'):
                path_func = None
                # Импортируем функцию заново для теста
                import services.global_settings_service as gss
                path_func = gss._get_settings_file_path
                
                # Путь должен содержать AppData
                assert 'AppData' in str(path_func()) or 'dubbing_manager' in str(path_func())

    def test_get_settings_file_path_macos(self):
        """Тест пути к файлу на macOS"""
        with patch('services.global_settings_service.sys.platform', 'darwin'):
            import services.global_settings_service as gss
            path = gss._get_settings_file_path()
            
            assert 'dubbing_manager' in str(path)

    def test_get_settings_file_path_linux(self):
        """Тест пути к файлу на Linux"""
        with patch('services.global_settings_service.sys.platform', 'linux'):
            import services.global_settings_service as gss
            path = gss._get_settings_file_path()
            
            assert 'dubbing_manager' in str(path)

    def test_partial_settings_load(self, service, temp_settings_file):
        """Тест частичной загрузки настроек"""
        # Только export_config
        test_data = {'export_config': {'layout_type': 'Сценарий'}}
        
        temp_settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_settings_file, 'w') as f:
            json.dump(test_data, f)
        
        settings = service.load_settings()
        
        assert settings['export_config']['layout_type'] == 'Сценарий'
        # Остальные должны быть по умолчанию
        assert settings['prompter_config']['f_tc'] == 20

    def test_settings_file_attribute(self, service, temp_settings_file):
        """Тест атрибута _settings_file"""
        assert service._settings_file == temp_settings_file


class TestGlobalSettingsServiceIntegration:
    """Интеграционные тесты для GlobalSettingsService"""

    def test_full_cycle(self, tmp_path):
        """Тест полного цикла: сохранение и загрузка"""
        settings_file = tmp_path / "settings.json"
        
        with patch('services.global_settings_service.SETTINGS_FILE', settings_file):
            # Создаём и сохраняем
            service1 = GlobalSettingsService()
            original_settings = {
                'export_config': {'layout_type': 'Сценарий', 'use_color': False},
                'prompter_config': {'f_tc': 50, 'f_text': 100},
                'replica_merge_config': {'merge': False, 'merge_gap': 200}
            }
            service1.save_settings(original_settings)
            
            # Загружаем в новом экземпляре
            service2 = GlobalSettingsService()
            loaded_settings = service2.load_settings()
            
            # Проверяем
            assert loaded_settings['export_config']['layout_type'] == 'Сценарий'
            assert loaded_settings['export_config']['use_color'] == False
            assert loaded_settings['prompter_config']['f_tc'] == 50
            assert loaded_settings['prompter_config']['f_text'] == 100
            assert loaded_settings['replica_merge_config']['merge'] == False
            assert loaded_settings['replica_merge_config']['merge_gap'] == 200
