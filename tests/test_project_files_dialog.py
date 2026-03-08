"""Тесты для ProjectFilesDialog"""

import pytest
import os
import tempfile
import shutil
from PySide6.QtWidgets import QApplication
from ui.dialogs.project_files import ProjectFilesDialog


@pytest.fixture
def app():
    """Создание QApplication для тестов"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_data():
    """Создание тестовых данных"""
    test_dir = tempfile.mkdtemp()
    
    # Создаём тестовые файлы
    ass_path = os.path.join(test_dir, "Episode_01.ass")
    video_path = os.path.join(test_dir, "Episode_01.mp4")
    
    with open(ass_path, "w") as f:
        f.write("test")
    with open(video_path, "w") as f:
        f.write("test")
    
    data = {
        "episodes": {
            "1": ass_path,
            "2": "/nonexistent/path.ass"
        },
        "video_paths": {
            "1": video_path,
            "2": "/nonexistent/video.mp4"
        },
        "project_folder": test_dir
    }
    
    yield data, test_dir
    
    shutil.rmtree(test_dir, ignore_errors=True)


class TestProjectFilesDialog:
    """Тесты для ProjectFilesDialog"""

    def test_dialog_creation(self, app, test_data):
        """Создание диалога"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        assert dialog is not None
        assert dialog.windowTitle() == "Файлы проекта"

    def test_dialog_populates_tree(self, app, test_data):
        """Заполнение дерева файлов"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что дерево не пустое
        assert dialog.file_tree.topLevelItemCount() > 0

    def test_found_file_status(self, app, test_data):
        """Статус найденного файла"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Получаем первый элемент
        root_item = dialog.file_tree.topLevelItem(0)
        assert root_item is not None
        
        # Проверяем первый файл (ASS)
        ass_item = root_item.child(0)
        if ass_item:
            status = ass_item.text(2)
            assert "✓" in status or "Найден" in status

    def test_missing_file_status(self, app, test_data):
        """Статус отсутствующего файла"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Ищем элемент для серии 2
        for i in range(dialog.file_tree.topLevelItemCount()):
            root_item = dialog.file_tree.topLevelItem(i)
            if "2" in root_item.text(0):
                ass_item = root_item.child(0)
                if ass_item:
                    status = ass_item.text(2)
                    assert "✗" in status or "Не найден" in status
                    break

    def test_statistics_display(self, app, test_data):
        """Отображение статистики"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        stats_text = dialog.lbl_stats.text()
        assert "Всего файлов:" in stats_text
        assert "Найдено:" in stats_text
        assert "Не найдено:" in stats_text

    def test_refresh_button(self, app, test_data):
        """Кнопка обновления"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что кнопка существует
        assert dialog.btn_refresh is not None
        
        # Нажимаем кнопку
        dialog.btn_refresh.click()
        
        # Проверяем, что дерево не пустое
        assert dialog.file_tree.topLevelItemCount() > 0

    def test_close_button(self, app, test_data):
        """Кнопка закрытия"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что кнопка существует
        assert dialog.btn_close is not None
        
        # Нажимаем кнопку
        dialog.btn_close.click()
        
        # Диалог должен закрыться
        assert not dialog.isVisible()

    def test_relink_button_initial_state(self, app, test_data):
        """Состояние кнопки перепривязки"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Кнопка должна быть отключена без выбора
        assert not dialog.btn_relink.isEnabled()

    def test_tree_expanded(self, app, test_data):
        """Дерево развёрнуто"""
        data, _ = test_data
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что элементы развёрнуты
        for i in range(dialog.file_tree.topLevelItemCount()):
            item = dialog.file_tree.topLevelItem(i)
            assert item.isExpanded()


class TestProjectFilesDialogEmpty:
    """Тесты для пустого проекта"""

    def test_empty_project(self, app):
        """Диалог с пустым проектом"""
        data = {
            "episodes": {},
            "video_paths": {},
            "project_folder": None
        }
        
        dialog = ProjectFilesDialog(data)
        
        # Дерево должно быть пустым
        assert dialog.file_tree.topLevelItemCount() == 0
        
        # Статистика должна показывать 0
        stats_text = dialog.lbl_stats.text()
        assert "Всего файлов: 0" in stats_text


class TestProjectFilesDialogWithOnlyAss:
    """Тесты для проекта только с ASS файлами"""

    def test_only_ass_files(self, app, test_data):
        """Проект только с субтитрами"""
        data, _ = test_data
        
        # Удаляем видео пути
        data["video_paths"] = {}
        
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что есть элементы
        assert dialog.file_tree.topLevelItemCount() > 0
        
        # Проверяем, что нет видео элементов
        for i in range(dialog.file_tree.topLevelItemCount()):
            root_item = dialog.file_tree.topLevelItem(i)
            has_video = False
            for j in range(root_item.childCount()):
                child = root_item.child(j)
                if "Видео" in child.text(1):
                    has_video = True
                    break
            assert not has_video


class TestProjectFilesDialogWithOnlyVideo:
    """Тесты для проекта только с видео файлами"""

    def test_only_video_files(self, app, test_data):
        """Проект только с видео"""
        data, test_dir = test_data
        
        # Создаём только видео
        data["episodes"] = {}
        data["video_paths"] = {
            "1": os.path.join(test_dir, "Episode_01.mp4")
        }
        
        dialog = ProjectFilesDialog(data)
        
        # Проверяем, что есть элементы
        assert dialog.file_tree.topLevelItemCount() > 0
