"""Тесты для export_service.py"""

import pytest
from typing import Dict, List, Any

from services.export_service import ExportService
from core.models import ExportConfig, ReplicaMergeConfig


class TestExportService:
    """Тесты для сервиса экспорта"""

    @pytest.fixture
    def sample_project_data(self) -> Dict[str, Any]:
        """Пример данных проекта для тестов"""
        return {
            "project_name": "Test Project",
            "actors": {
                "actor1": {"name": "Actor One", "color": "#FF0000", "roles": []},
                "actor2": {"name": "Actor Two", "color": "#00FF00", "roles": []},
            },
            "global_map": {
                "Character1": "actor1",
                "Character2": "actor2",
            }
        }

    @pytest.fixture
    def sample_lines(self) -> List[Dict[str, Any]]:
        """Пример реплик для тестов"""
        return [
            {
                "id": 1,
                "s": 0.0,
                "e": 2.5,
                "char": "Character1",
                "text": "Hello, world!",
                "s_raw": "0:00:00.00"
            },
            {
                "id": 2,
                "s": 3.0,
                "e": 5.5,
                "char": "Character2",
                "text": "Hi there!",
                "s_raw": "0:00:03.00"
            },
            {
                "id": 3,
                "s": 6.0,
                "e": 8.5,
                "char": "Character1",
                "text": "How are you?",
                "s_raw": "0:00:06.00"
            }
        ]

    @pytest.fixture
    def export_config(self) -> Dict[str, Any]:
        """Конфигурация экспорта по умолчанию"""
        return {
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
            'allow_edit': True
        }

    @pytest.fixture
    def merge_config(self) -> Dict[str, Any]:
        """Конфигурация объединения реплик"""
        return {
            'merge': True,
            'merge_gap': 120,
            'p_short': 0.5,
            'p_long': 2.0,
            'fps': 25.0
        }

    def test_process_merge_logic_no_merge(
        self,
        sample_lines: List[Dict[str, Any]],
        merge_config: Dict[str, Any]
    ) -> None:
        """Тест: объединение реплик отключено"""
        merge_config['merge'] = False
        service = ExportService({})
        result = service.process_merge_logic(sample_lines, merge_config)
        
        # Все реплики должны остаться отдельными
        assert len(result) == len(sample_lines)
        for item in result:
            assert 'parts' in item
            assert len(item['parts']) == 1

    def test_process_merge_logic_same_character(
        self,
        sample_lines: List[Dict[str, Any]],
        merge_config: Dict[str, Any]
    ) -> None:
        """Тест: объединение реплик одного персонажа"""
        # Создаём реплики одного персонажа с маленьким промежутком
        lines = [
            {
                "id": 1,
                "s": 0.0,
                "e": 2.0,
                "char": "Character1",
                "text": "First",
                "s_raw": "0:00:00.00"
            },
            {
                "id": 2,
                "s": 2.2,  # Промежуток 0.2 сек < merge_gap
                "e": 4.0,
                "char": "Character1",
                "text": "Second",
                "s_raw": "0:00:02.00"
            }
        ]
        
        service = ExportService({})
        result = service.process_merge_logic(lines, merge_config)
        
        # Реплики должны объединиться
        assert len(result) == 1
        assert len(result[0]['parts']) == 2
        assert result[0]['text'] == "First /  Second"

    def test_process_merge_logic_different_characters(
        self,
        sample_lines: List[Dict[str, Any]],
        merge_config: Dict[str, Any]
    ) -> None:
        """Тест: реплики разных персонажей не объединяются"""
        service = ExportService({})
        result = service.process_merge_logic(sample_lines, merge_config)
        
        # Реплики разных персонажей не должны объединяться
        assert len(result) == 3

    def test_process_merge_logic_large_gap(
        self,
        merge_config: Dict[str, Any]
    ) -> None:
        """Тест: большой промежуток между репликами"""
        lines = [
            {
                "id": 1,
                "s": 0.0,
                "e": 2.0,
                "char": "Character1",
                "text": "First",
                "s_raw": "0:00:00.00"
            },
            {
                "id": 2,
                "s": 10.0,  # Большой промежуток
                "e": 12.0,
                "char": "Character1",
                "text": "Second",
                "s_raw": "0:00:10.00"
            }
        ]
        
        service = ExportService({})
        result = service.process_merge_logic(lines, merge_config)
        
        # Реплики должны остаться раздельными из-за большого промежутка
        assert len(result) == 2

    def test_generate_html_basic(
        self,
        sample_project_data: Dict[str, Any],
        sample_lines: List[Dict[str, Any]],
        export_config: Dict[str, Any]
    ) -> None:
        """Тест: генерация HTML"""
        service = ExportService(sample_project_data)
        processed = service.process_merge_logic(sample_lines, {'merge': False})
        html = service.generate_html(
            ep="1",
            processed=processed,
            cfg=export_config,
            layout_type="Таблица",
            is_editable=False
        )
        
        assert "<html>" in html
        assert "</html>" in html
        assert "Test Project - Серия 1" in html
        assert "Character1" in html
        assert "Hello, world!" in html

    def test_generate_html_scenario_layout(
        self,
        sample_project_data: Dict[str, Any],
        sample_lines: List[Dict[str, Any]],
        export_config: Dict[str, Any]
    ) -> None:
        """Тест: генерация HTML с layout 'Сценарий'"""
        service = ExportService(sample_project_data)
        processed = service.process_merge_logic(sample_lines, {'merge': False})
        html = service.generate_html(
            ep="1",
            processed=processed,
            cfg=export_config,
            layout_type="Сценарий",
            is_editable=False
        )
        
        assert "line-container" in html
        assert "Character1" in html

    def test_generate_html_with_highlight(
        self,
        sample_project_data: Dict[str, Any],
        sample_lines: List[Dict[str, Any]],
        export_config: Dict[str, Any]
    ) -> None:
        """Тест: генерация HTML с подсветкой актёров"""
        service = ExportService(sample_project_data)
        processed = service.process_merge_logic(sample_lines, {'merge': False})
        
        # Подсветка только actor1
        highlight_ids = ["actor1"]
        html = service.generate_html(
            ep="1",
            processed=processed,
            cfg=export_config,
            highlight_ids=highlight_ids,
            layout_type="Таблица",
            is_editable=False
        )
        
        assert "highlighted-block" in html

    def test_count_words(self) -> None:
        """Тест: подсчёт количества слов"""
        service = ExportService({})
        
        assert service._count_words("Hello world") == 2
        assert service._count_words("One") == 1
        assert service._count_words("") == 0
        assert service._count_words("  Multiple   spaces  ") == 2
        assert service._count_words("New\nlines") == 2

    def test_seconds_to_ass_time(self) -> None:
        """Тест: конвертация секунд в формат ASS"""
        service = ExportService({})
        
        assert service._seconds_to_ass_time(0) == "0:00:00.00"
        assert service._seconds_to_ass_time(60) == "0:01:00.00"
        assert service._seconds_to_ass_time(3661.5) == "1:01:01.50"

    def test_get_colors_with_color_enabled(
        self,
        sample_project_data: Dict[str, Any]
    ) -> None:
        """Тест: получение цветов с включенной опцией"""
        service = ExportService(sample_project_data)
        
        actor = {"name": "Test", "color": "#FF0000"}
        bg_color, border_col = service._get_colors(
            use_color=True,
            is_highlighted=True,
            actor=actor
        )
        
        assert bg_color is not None
        assert border_col == "#FF0000"

    def test_get_colors_with_color_disabled(
        self,
        sample_project_data: Dict[str, Any]
    ) -> None:
        """Тест: получение цветов с отключенной опцией"""
        service = ExportService(sample_project_data)
        
        actor = {"name": "Test", "color": "#FF0000"}
        bg_color, border_col = service._get_colors(
            use_color=False,
            is_highlighted=True,
            actor=actor
        )
        
        assert bg_color == "#ffffff"
        assert border_col == "#eee"


class TestExportServiceExcel:
    """Тесты для Excel экспорта (если openpyxl доступен)"""

    @pytest.fixture
    def sample_project_data(self) -> Dict[str, Any]:
        """Пример данных проекта для тестов"""
        return {
            "project_name": "Test Project",
            "actors": {
                "actor1": {"name": "Actor One", "color": "#FF0000", "roles": []},
            },
            "global_map": {
                "Character1": "actor1",
            }
        }

    def test_create_excel_book_basic(
        self,
        sample_project_data: Dict[str, Any]
    ) -> None:
        """Тест: создание Excel книги"""
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        
        service = ExportService(sample_project_data)
        episodes_data = {
            "1": [
                {
                    "id": 1,
                    "s": 0.0,
                    "e": 2.0,
                    "char": "Character1",
                    "text": "Hello",
                    "s_raw": "0:00:00.00"
                }
            ]
        }
        
        wb = service.create_excel_book(episodes_data)
        
        assert wb is not None
        assert len(wb.sheetnames) >= 1
        assert 'Сводка' in wb.sheetnames or any('серия' in name for name in wb.sheetnames)

    def test_create_excel_book_multiple_episodes(
        self,
        sample_project_data: Dict[str, Any]
    ) -> None:
        """Тест: создание Excel книги с несколькими сериями"""
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        
        service = ExportService(sample_project_data)
        episodes_data = {
            "1": [{"id": 1, "s": 0.0, "e": 2.0, "char": "Character1", "text": "Ep1", "s_raw": "0:00:00.00"}],
            "2": [{"id": 1, "s": 0.0, "e": 2.0, "char": "Character1", "text": "Ep2", "s_raw": "0:00:00.00"}],
            "3": [{"id": 1, "s": 0.0, "e": 2.0, "char": "Character1", "text": "Ep3", "s_raw": "0:00:00.00"}],
        }
        
        wb = service.create_excel_book(episodes_data)
        
        # Должны быть листы для каждой серии + сводка
        assert len(wb.sheetnames) >= 3
