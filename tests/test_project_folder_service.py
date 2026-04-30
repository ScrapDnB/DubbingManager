"""Тесты для ProjectFolderService"""

import pytest
import os
import tempfile
import shutil
from services import ProjectFolderService


class TestProjectFolderService:
    """Тесты для ProjectFolderService"""

    def setup_method(self):
        """Создание временной папки для тестов"""
        self.test_dir = tempfile.mkdtemp()
        self.service = ProjectFolderService()

    def teardown_method(self):
        """Очистка временной папки"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_set_project_folder(self):
        """Установка папки проекта"""
        data = {}
        result = self.service.set_project_folder(data, self.test_dir)
        
        assert result is True
        assert data["project_folder"] == os.path.abspath(self.test_dir)

    def test_set_nonexistent_folder(self):
        """Установка несуществующей папки"""
        data = {}
        result = self.service.set_project_folder(data, "/nonexistent/path")
        
        assert result is False
        assert "project_folder" not in data

    def test_clear_project_folder(self):
        """Очистка папки проекта"""
        data = {"project_folder": self.test_dir}
        self.service.clear_project_folder(data)
        
        assert "project_folder" not in data

    def test_get_project_folder(self):
        """Получение папки проекта"""
        data = {"project_folder": self.test_dir}
        folder = self.service.get_project_folder(data)
        
        assert folder == self.test_dir

    def test_extract_episode_number_various_formats(self):
        """Извлечение номера серии из различных форматов"""
        test_cases = [
            ("Series_01.ass", "1"),
            ("EP01.mkv", "1"),
            ("Ep01.ass", "1"),
            ("Episode 01.mkv", "1"),
            ("S01E01.ass", "1 1"),
            ("S1E1.mkv", "1 1"),
            ("[Subs] Series - 01.ass", "1"),
            ("01.ass", "1"),
            ("1.ass", "1"),
            ("Series - 10.mkv", "10"),
        ]

        for filename, expected in test_cases:
            result = self.service._extract_episode_number(filename)
            assert result == expected, f"Failed for {filename}"

    def test_find_ass_files(self):
        """Поиск ASS файлов"""
        # Создаём тестовые файлы
        ass_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        found = self.service.find_all_media_files(self.test_dir)
        
        assert "1" in found["ass"]
        assert found["ass"]["1"] == ass_path

    def test_find_video_files(self):
        """Поиск видео файлов"""
        # Создаём тестовые файлы
        video_path = os.path.join(self.test_dir, "Episode_01.mp4")
        with open(video_path, "w") as f:
            f.write("test")

        found = self.service.find_all_media_files(self.test_dir)
        
        assert "1" in found["video"]
        assert found["video"]["1"] == video_path

    def test_find_episode_text_files(self):
        """Поиск рабочих текстов эпизодов"""
        text_path = os.path.join(self.test_dir, "episode_01.json")
        with open(text_path, "w") as f:
            f.write("{}")

        project_path = os.path.join(self.test_dir, "project_01.json")
        with open(project_path, "w") as f:
            f.write("{}")

        found = self.service.find_all_media_files(self.test_dir)

        assert "1" in found["text"]
        assert found["text"]["1"] == text_path
        assert found["text"]["1"] != project_path

    def test_find_files_in_subfolders(self):
        """Поиск файлов в подпапках"""
        # Создаём подпапку
        subdir = os.path.join(self.test_dir, "subfolder")
        os.makedirs(subdir)
        
        # Создаём файл в подпапке
        ass_path = os.path.join(subdir, "Episode_02.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        found = self.service.find_all_media_files(self.test_dir)
        
        assert "2" in found["ass"]
        assert found["ass"]["2"] == ass_path

    def test_scan_and_link_files_does_not_create_episodes(self):
        """Сканирование не создаёт новые эпизоды"""
        # Создаём тестовые файлы
        ass_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        data = {"episodes": {}, "video_paths": {}}
        ass_count, video_count, text_count = self.service.scan_and_link_files(data, self.test_dir)
        
        assert ass_count == 0
        assert video_count == 0
        assert text_count == 0
        assert data["episodes"] == {}

    def test_skip_hidden_files(self):
        """Пропуск скрытых файлов"""
        # Создаём скрытый файл
        hidden_path = os.path.join(self.test_dir, ".hidden.ass")
        with open(hidden_path, "w") as f:
            f.write("test")

        found = self.service.find_all_media_files(self.test_dir)
        
        assert len(found["ass"]) == 0

    def test_skip_hidden_folders(self):
        """Пропуск скрытых папок"""
        # Создаём скрытую папку
        hidden_dir = os.path.join(self.test_dir, ".hidden")
        os.makedirs(hidden_dir)
        
        # Создаём файл в скрытой папке
        ass_path = os.path.join(hidden_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        found = self.service.find_all_media_files(self.test_dir)
        
        assert len(found["ass"]) == 0

    def test_get_folder_stats(self):
        """Получение статистики папки"""
        # Создаём тестовые файлы
        for i in range(1, 4):
            ass_path = os.path.join(self.test_dir, f"Episode_{i:02d}.ass")
            with open(ass_path, "w") as f:
                f.write("test")

        stats = self.service.get_folder_stats(self.test_dir)
        
        assert stats["ass_count"] == 3
        assert stats["video_count"] == 0
        assert stats["episodes"] == ["1", "2", "3"]

    def test_invalidate_cache(self):
        """Инвалидация кэша"""
        # Создаём файл
        ass_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        # Заполняем кэш
        self.service.find_all_media_files(self.test_dir)
        
        # Инвалидируем
        self.service.invalidate_cache(self.test_dir)
        
        # Проверяем, что кэш очищен для этой папки
        assert self.test_dir not in self.service._found_files_cache

    def test_invalidate_all_cache(self):
        """Полная очистка кэша"""
        # Создаём несколько папок
        dir1 = tempfile.mkdtemp()
        dir2 = tempfile.mkdtemp()
        
        try:
            # Заполняем кэш
            self.service.find_all_media_files(dir1)
            self.service.find_all_media_files(dir2)
            
            # Очищаем весь кэш
            self.service.invalidate_cache()
            
            assert len(self.service._found_files_cache) == 0
        finally:
            shutil.rmtree(dir1, ignore_errors=True)
            shutil.rmtree(dir2, ignore_errors=True)

    def test_suggest_video_for_episode(self):
        """Поиск видео для серии"""
        # Создаём видео файл
        video_path = os.path.join(self.test_dir, "Episode_01.mp4")
        with open(video_path, "w") as f:
            f.write("test")

        data = {"project_folder": self.test_dir}
        result = self.service.suggest_video_for_episode(data, "1")
        
        assert result == video_path

    def test_batch_import_from_folder(self):
        """Массовый импорт из папки"""
        # Создаём файлы
        for i in range(1, 4):
            ass_path = os.path.join(self.test_dir, f"Episode_{i:02d}.ass")
            with open(ass_path, "w") as f:
                f.write("test")
            
            video_path = os.path.join(self.test_dir, f"Episode_{i:02d}.mp4")
            with open(video_path, "w") as f:
                f.write("test")

        data = {"episodes": {}, "video_paths": {}}
        ass_count, video_count = self.service.batch_import_from_folder(data, self.test_dir)
        
        assert ass_count == 3
        assert video_count == 3
        assert len(data["episodes"]) == 3
        assert len(data["video_paths"]) == 3

    def test_find_missing_files(self):
        """Поиск отсутствующих файлов"""
        # Создаём только один файл
        ass_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        data = {
            "project_folder": self.test_dir,
            "episodes": {"1": ass_path, "2": "/missing/path.ass"}
        }
        
        missing = self.service.find_missing_files(data)
        
        assert "2" in missing["ass"]
        assert "1" not in missing["ass"]

    def test_update_path_if_file_moved(self):
        """Обновление пути при перемещении файла"""
        # Создаём файл
        ass_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(ass_path, "w") as f:
            f.write("test")

        # Добавляем в проект с неправильным путём
        data = {
            "project_folder": self.test_dir,
            "episodes": {"1": "/wrong/path.ass"}
        }
        
        # Сканируем
        self.service.scan_and_link_files(data)
        
        # Путь должен обновиться
        assert data["episodes"]["1"] == ass_path

    def test_update_video_path_if_file_moved(self):
        """Обновление пути видео при перемещении файла"""
        video_path = os.path.join(self.test_dir, "Episode_01.mp4")
        with open(video_path, "w") as f:
            f.write("test")

        data = {
            "project_folder": self.test_dir,
            "episodes": {},
            "video_paths": {"1": "/wrong/video.mp4"}
        }

        ass_count, video_count, text_count = self.service.scan_and_link_files(data)

        assert ass_count == 0
        assert video_count == 1
        assert text_count == 0
        assert data["video_paths"]["1"] == video_path

    def test_update_episode_text_path_if_file_moved(self):
        """Обновление пути рабочего текста при перемещении файла"""
        text_path = os.path.join(self.test_dir, "episode_01.json")
        with open(text_path, "w") as f:
            f.write("{}")

        data = {
            "project_folder": self.test_dir,
            "episodes": {},
            "video_paths": {},
            "episode_texts": {"1": "/wrong/episode_01.json"}
        }

        ass_count, video_count, text_count = self.service.scan_and_link_files(data)

        assert ass_count == 0
        assert video_count == 0
        assert text_count == 1
        assert data["episode_texts"]["1"] == text_path


class TestProjectFolderServiceWithRealStructure:
    """Тесты с реальной структурой папок"""

    def setup_method(self):
        """Создание тестовой структуры"""
        self.test_dir = tempfile.mkdtemp()
        self.service = ProjectFolderService()
        
        # Создаём структуру как в реальном проекте
        subs_dir = os.path.join(self.test_dir, "Subtitles")
        video_dir = os.path.join(self.test_dir, "Video")
        os.makedirs(subs_dir)
        os.makedirs(video_dir)
        
        # Создаём файлы
        for i in range(1, 4):
            ass_path = os.path.join(subs_dir, f"Series_E{i:02d}.ass")
            with open(ass_path, "w") as f:
                f.write("test")
            
            video_path = os.path.join(video_dir, f"Series_E{i:02d}.mkv")
            with open(video_path, "w") as f:
                f.write("test")

    def teardown_method(self):
        """Очистка"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_files_in_different_subfolders(self):
        """Поиск файлов в разных подпапках"""
        found = self.service.find_all_media_files(self.test_dir)
        
        assert len(found["ass"]) == 3
        assert len(found["video"]) == 3
        
        # Проверяем, что все серии найдены
        for i in range(1, 4):
            assert str(i) in found["ass"]
            assert str(i) in found["video"]

    def test_scan_and_link_with_different_subfolders_does_not_create_episodes(self):
        """Сканирование с разными подпапками не создаёт эпизоды"""
        data = {"episodes": {}, "video_paths": {}}
        ass_count, video_count, text_count = self.service.scan_and_link_files(data, self.test_dir)
        
        assert ass_count == 0
        assert video_count == 0
        assert text_count == 0
        assert len(data["episodes"]) == 0
        assert len(data["video_paths"]) == 0
