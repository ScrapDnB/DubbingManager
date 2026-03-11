"""Тесты для сохранения DOCX импорта"""

import pytest
import os
import tempfile
from services.episode_service import EpisodeService

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class TestDocxSave:
    """Тесты для сохранения импортированных из DOCX данных"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.service = EpisodeService(merge_gap=5, fps=25.0)

    def test_save_episode_to_ass_new(self):
        """Тест сохранения нового ASS файла (для DOCX импорта)"""
        memory_lines = [
            {'s': 1.0, 'e': 3.0, 'char': 'Иван', 'text': 'Привет!'},
            {'s': 4.0, 'e': 6.0, 'char': 'Мария', 'text': 'Как дела?'},
            {'s': 7.5, 'e': 9.0, 'char': 'Иван', 'text': 'Нормально.'}
        ]

        temp_file = tempfile.NamedTemporaryFile(
            suffix='.ass', delete=False, mode='w'
        )
        temp_path = temp_file.name
        temp_file.close()

        try:
            success, message = self.service.save_episode_to_ass_new(
                "1", memory_lines, temp_path
            )

            assert success == True
            assert os.path.exists(temp_path)

            # Проверяем содержимое
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert '[Script Info]' in content
            assert '[Events]' in content
            assert 'Dialogue: 0,0:00:01.00,0:00:03.00,,Иван' in content
            assert 'Привет!' in content
            assert 'Мария' in content
            assert 'Как дела?' in content

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_seconds_to_ass_time(self):
        """Тест конвертации секунд в ASS формат"""
        test_cases = [
            (0.0, "0:00:00.00"),
            (1.0, "0:00:01.00"),
            (3.5, "0:00:03.50"),
            (60.0, "0:01:00.00"),
            (3661.5, "1:01:01.50"),
        ]

        for seconds, expected in test_cases:
            result = self.service._seconds_to_ass_time(seconds)
            assert result == expected, f"Failed for {seconds}: got {result}, expected {expected}"

    def test_save_with_empty_lines(self):
        """Тест сохранения с пустыми данными"""
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.ass', delete=False, mode='w'
        )
        temp_path = temp_file.name
        temp_file.close()

        try:
            success, message = self.service.save_episode_to_ass_new(
                "1", [], temp_path
            )

            assert success == False
            assert "Нет данных" in message

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_episode_to_ass_with_docx_path(self):
        """Тест save_episode_to_ass с DOCX путём"""
        memory_lines = [
            {'s': 1.0, 'e': 3.0, 'char': 'Иван', 'text': 'Привет!'}
        ]

        episodes = {"1": "/path/to/file.docx"}

        temp_file = tempfile.NamedTemporaryFile(
            suffix='.ass', delete=False, mode='w'
        )
        temp_path = temp_file.name
        temp_file.close()

        try:
            # DOCX файл не существует, должен создаться новый ASS
            success, message = self.service.save_episode_to_ass(
                "1", episodes, memory_lines, temp_path
            )

            assert success == True
            assert os.path.exists(temp_path)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
