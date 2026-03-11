"""
Тесты для системы отмены/повтора действий (Undo/Redo)

Запуск:
    pytest tests/test_commands.py -v

Запуск с покрытием:
    pytest tests/test_commands.py -v --cov=core/commands --cov-report=html
"""

import pytest
from typing import Dict, List

from core.commands import (
    UndoStack,
    AddActorCommand,
    DeleteActorCommand,
    RenameActorCommand,
    UpdateActorColorCommand,
    AssignActorToCharacterCommand,
    RenameCharacterCommand,
    AddEpisodeCommand,
    RenameEpisodeCommand,
    DeleteEpisodeCommand,
    UpdateProjectNameCommand,
    SetProjectFolderCommand,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def actors() -> Dict[str, dict]:
    """Фикстура с тестовыми актёрами"""
    return {
        "actor1": {"name": "Иван Иванов", "color": "#FF0000", "roles": []},
        "actor2": {"name": "Пётр Петров", "color": "#00FF00", "roles": []},
    }


@pytest.fixture
def global_map() -> Dict[str, str]:
    """Фикстура с глобальной картой маппинга"""
    return {
        "Персонаж 1": "actor1",
        "Персонаж 2": "actor2",
    }


@pytest.fixture
def episodes() -> Dict[str, str]:
    """Фикстура с эпизодами"""
    return {
        "1": "/path/to/episode1.ass",
        "2": "/path/to/episode2.ass",
    }


# =============================================================================
# Tests for UndoStack
# =============================================================================

class TestUndoStack:
    """Тесты для стека отмены/повтора действий"""

    def test_push_and_undo(self):
        """Тест добавления команды и отмены"""
        stack = UndoStack()
        executed = []

        class SimpleCommand:
            def execute(self):
                executed.append("executed")

            def undo(self):
                executed.append("undo")

            def get_description(self):
                return "Simple command"

        cmd = SimpleCommand()
        stack.push(cmd)
        assert executed == ["executed"]

        stack.undo()
        assert executed == ["executed", "undo"]

    def test_redo(self):
        """Тест повтора действия"""
        stack = UndoStack()
        values = [0]

        class IncrementCommand:
            def execute(self):
                values[0] += 1

            def undo(self):
                values[0] -= 1

            def get_description(self):
                return "Increment"

        cmd = IncrementCommand()
        stack.push(cmd)
        assert values[0] == 1

        stack.undo()
        assert values[0] == 0

        stack.redo()
        assert values[0] == 1

    def test_clear(self):
        """Тест очистки стека"""
        stack = UndoStack()

        class SimpleCommand:
            def execute(self):
                pass

            def undo(self):
                pass

            def get_description(self):
                return "Simple"

        stack.push(SimpleCommand())
        stack.push(SimpleCommand())
        stack.clear()

        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_can_undo(self):
        """Тест проверки возможности отмены"""
        stack = UndoStack()
        assert not stack.can_undo()

        class SimpleCommand:
            def execute(self):
                pass

            def undo(self):
                pass

            def get_description(self):
                return "Simple"

        stack.push(SimpleCommand())
        assert stack.can_undo()

    def test_can_redo(self):
        """Тест проверки возможности повтора"""
        stack = UndoStack()
        assert not stack.can_redo()

        class SimpleCommand:
            def execute(self):
                pass

            def undo(self):
                pass

            def get_description(self):
                return "Simple"

        cmd = SimpleCommand()
        stack.push(cmd)
        stack.undo()
        assert stack.can_redo()

    def test_on_change_callback(self):
        """Тест колбэка изменения стека"""
        stack = UndoStack()
        callback_called = []

        def callback():
            callback_called.append(True)

        stack.on_change(callback)

        class SimpleCommand:
            def execute(self):
                pass

            def undo(self):
                pass

            def get_description(self):
                return "Simple"

        stack.push(SimpleCommand())
        assert len(callback_called) >= 1


# =============================================================================
# Tests for AddActorCommand
# =============================================================================

class TestAddActorCommand:
    """Тесты для команды добавления актёра"""

    def test_execute(self, actors):
        """Тест выполнения команды"""
        cmd = AddActorCommand(actors, "actor3", "Анна Анна", "#0000FF")
        cmd.execute()

        assert "actor3" in actors
        assert actors["actor3"]["name"] == "Анна Анна"
        assert actors["actor3"]["color"] == "#0000FF"

    def test_undo(self, actors):
        """Тест отмены команды"""
        cmd = AddActorCommand(actors, "actor3", "Анна Анна", "#0000FF")
        cmd.execute()
        assert "actor3" in actors

        cmd.undo()
        assert "actor3" not in actors

    def test_get_description(self, actors):
        """Тест описания команды"""
        cmd = AddActorCommand(actors, "actor3", "Анна Анна", "#0000FF")
        assert cmd.get_description() == "Добавлен актёр: Анна Анна"


# =============================================================================
# Tests for DeleteActorCommand
# =============================================================================

class TestDeleteActorCommand:
    """Тесты для команды удаления актёра"""

    def test_execute(self, actors):
        """Тест выполнения команды"""
        cmd = DeleteActorCommand(actors, {}, "actor1")
        cmd.execute()

        assert "actor1" not in actors

    def test_execute_removes_mappings(self, actors, global_map):
        """Тест удаления маппингов актёра"""
        cmd = DeleteActorCommand(actors, global_map, "actor1")
        cmd.execute()

        assert "Персонаж 1" not in global_map

    def test_undo(self, actors):
        """Тест отмены команды"""
        cmd = DeleteActorCommand(actors, {}, "actor1")
        cmd.execute()
        assert "actor1" not in actors

        cmd.undo()
        assert "actor1" in actors
        assert actors["actor1"]["name"] == "Иван Иванов"

    def test_undo_restores_mappings(self, actors, global_map):
        """Тест восстановления маппингов при отмене"""
        cmd = DeleteActorCommand(actors, global_map, "actor1")
        cmd.execute()
        assert "Персонаж 1" not in global_map

        cmd.undo()
        assert "Персонаж 1" in global_map
        assert global_map["Персонаж 1"] == "actor1"

    def test_get_description(self, actors):
        """Тест описания команды"""
        cmd = DeleteActorCommand(actors, {}, "actor1")
        # execute() должен быть вызван для получения имени
        cmd.execute()
        # После выполнения _deleted_data содержит удалённые данные
        assert "Удалён актёр:" in cmd.get_description()


# =============================================================================
# Tests for RenameActorCommand
# =============================================================================

class TestRenameActorCommand:
    """Тесты для команды переименования актёра"""

    def test_execute(self, actors):
        """Тест выполнения команды"""
        cmd = RenameActorCommand(actors, "actor1", "Новое Имя")
        cmd.execute()

        assert actors["actor1"]["name"] == "Новое Имя"

    def test_undo(self, actors):
        """Тест отмены команды"""
        cmd = RenameActorCommand(actors, "actor1", "Новое Имя")
        cmd.execute()
        assert actors["actor1"]["name"] == "Новое Имя"

        cmd.undo()
        assert actors["actor1"]["name"] == "Иван Иванов"

    def test_get_description(self, actors):
        """Тест описания команды"""
        cmd = RenameActorCommand(actors, "actor1", "Новое Имя")
        cmd.execute()
        assert cmd.get_description() == "Переименован актёр: Иван Иванов -> Новое Имя"


# =============================================================================
# Tests for UpdateActorColorCommand
# =============================================================================

class TestUpdateActorColorCommand:
    """Тесты для команды обновления цвета актёра"""

    def test_execute(self, actors):
        """Тест выполнения команды"""
        cmd = UpdateActorColorCommand(actors, "actor1", "#00FF00")
        cmd.execute()

        assert actors["actor1"]["color"] == "#00FF00"

    def test_undo(self, actors):
        """Тест отмены команды"""
        cmd = UpdateActorColorCommand(actors, "actor1", "#00FF00")
        cmd.execute()
        assert actors["actor1"]["color"] == "#00FF00"

        cmd.undo()
        assert actors["actor1"]["color"] == "#FF0000"

    def test_get_description(self, actors):
        """Тест описания команды"""
        cmd = UpdateActorColorCommand(actors, "actor1", "#00FF00")
        assert cmd.get_description() == "Изменён цвет актёра: None -> #00FF00"


# =============================================================================
# Tests for AssignActorToCharacterCommand
# =============================================================================

class TestAssignActorToCharacterCommand:
    """Тесты для команды назначения актёра на персонажа"""

    def test_execute_assign(self, global_map):
        """Тест назначения актёра"""
        cmd = AssignActorToCharacterCommand(global_map, "Персонаж 3", "actor1")
        cmd.execute()

        assert global_map["Персонаж 3"] == "actor1"

    def test_execute_unassign(self, global_map):
        """Тест отмены назначения"""
        cmd = AssignActorToCharacterCommand(global_map, "Персонаж 1", None)
        cmd.execute()

        assert "Персонаж 1" not in global_map

    def test_undo_assign(self, global_map):
        """Тест отмены назначения актёра"""
        cmd = AssignActorToCharacterCommand(global_map, "Персонаж 3", "actor1")
        cmd.execute()
        assert "Персонаж 3" in global_map

        cmd.undo()
        assert "Персонаж 3" not in global_map

    def test_undo_unassign(self, global_map):
        """Тест отмены отмены назначения"""
        cmd = AssignActorToCharacterCommand(global_map, "Персонаж 1", None)
        cmd.execute()
        assert "Персонаж 1" not in global_map

        cmd.undo()
        assert "Персонаж 1" in global_map
        assert global_map["Персонаж 1"] == "actor1"

    def test_get_description(self, global_map):
        """Тест описания команды"""
        cmd = AssignActorToCharacterCommand(global_map, "Персонаж 3", "actor1")
        assert cmd.get_description() == "Назначен актёр для: Персонаж 3"


# =============================================================================
# Tests for RenameCharacterCommand
# =============================================================================

class TestRenameCharacterCommand:
    """Тесты для команды переименования персонажа"""

    def test_execute(self, global_map, episodes):
        """Тест выполнения команды"""
        loaded_episodes = {"1": [{"char": "Персонаж 1", "text": "test"}]}
        current_ep_stats = [{"name": "Персонаж 1", "lines": 5}]
        cmd = RenameCharacterCommand(
            global_map, loaded_episodes, current_ep_stats,
            "1", "Персонаж 1", "Новый Персонаж"
        )
        cmd.execute()

        assert "Новый Персонаж" in global_map
        assert "Персонаж 1" not in global_map
        assert global_map["Новый Персонаж"] == "actor1"

    def test_undo(self, global_map, episodes):
        """Тест отмены команды"""
        loaded_episodes = {"1": [{"char": "Персонаж 1", "text": "test"}]}
        current_ep_stats = [{"name": "Персонаж 1", "lines": 5}]
        cmd = RenameCharacterCommand(
            global_map, loaded_episodes, current_ep_stats,
            "1", "Персонаж 1", "Новый Персонаж"
        )
        cmd.execute()
        assert "Новый Персонаж" in global_map

        cmd.undo()
        assert "Персонаж 1" in global_map
        assert "Новый Персонаж" not in global_map

    def test_get_description(self, global_map, episodes):
        """Тест описания команды"""
        loaded_episodes = {"1": [{"char": "Персонаж 1", "text": "test"}]}
        current_ep_stats = [{"name": "Персонаж 1", "lines": 5}]
        cmd = RenameCharacterCommand(
            global_map, loaded_episodes, current_ep_stats,
            "1", "Персонаж 1", "Новый Персонаж"
        )
        assert cmd.get_description() == "Переименован персонаж: Персонаж 1 -> Новый Персонаж"


# =============================================================================
# Tests for AddEpisodeCommand
# =============================================================================

class TestAddEpisodeCommand:
    """Тесты для команды добавления эпизода"""

    def test_execute(self, episodes):
        """Тест выполнения команды"""
        cmd = AddEpisodeCommand(episodes, "3", "/path/to/episode3.ass")
        cmd.execute()

        assert "3" in episodes
        assert episodes["3"] == "/path/to/episode3.ass"

    def test_undo(self, episodes):
        """Тест отмены команды"""
        cmd = AddEpisodeCommand(episodes, "3", "/path/to/episode3.ass")
        cmd.execute()
        assert "3" in episodes

        cmd.undo()
        assert "3" not in episodes

    def test_get_description(self, episodes):
        """Тест описания команды"""
        cmd = AddEpisodeCommand(episodes, "3", "/path/to/episode3.ass")
        assert cmd.get_description() == "Добавлена серия: 3"


# =============================================================================
# Tests for RenameEpisodeCommand
# =============================================================================

class TestRenameEpisodeCommand:
    """Тесты для команды переименования эпизода"""

    def test_execute(self, episodes):
        """Тест выполнения команды"""
        cmd = RenameEpisodeCommand(episodes, "1", "2")
        cmd.execute()

        assert "2" in episodes
        assert "1" not in episodes
        assert episodes["2"] == "/path/to/episode1.ass"

    def test_undo(self, episodes):
        """Тест отмены команды"""
        cmd = RenameEpisodeCommand(episodes, "1", "2")
        cmd.execute()
        assert "2" in episodes

        cmd.undo()
        assert "1" in episodes
        assert "2" not in episodes

    def test_get_description(self, episodes):
        """Тест описания команды"""
        cmd = RenameEpisodeCommand(episodes, "1", "2")
        assert cmd.get_description() == "Переименована серия: 1 -> 2"


# =============================================================================
# Tests for DeleteEpisodeCommand
# =============================================================================

class TestDeleteEpisodeCommand:
    """Тесты для команды удаления эпизода"""

    def test_execute(self, episodes):
        """Тест выполнения команды"""
        video_paths = {"1": "/path/to/video1.mp4"}
        loaded_episodes = {"1": [{"id": 0, "char": "Test"}]}
        cmd = DeleteEpisodeCommand(episodes, video_paths, loaded_episodes, "1")
        cmd.execute()

        assert "1" not in episodes
        assert "1" not in video_paths
        assert "1" not in loaded_episodes

    def test_undo(self, episodes):
        """Тест отмены команды"""
        video_paths = {"1": "/path/to/video1.mp4"}
        loaded_episodes = {"1": [{"id": 0, "char": "Test"}]}
        cmd = DeleteEpisodeCommand(episodes, video_paths, loaded_episodes, "1")
        cmd.execute()
        assert "1" not in episodes

        cmd.undo()
        assert "1" in episodes
        assert "1" in video_paths
        assert "1" in loaded_episodes

    def test_get_description(self, episodes):
        """Тест описания команды"""
        video_paths = {"1": "/path/to/video1.mp4"}
        loaded_episodes = {"1": [{"id": 0, "char": "Test"}]}
        cmd = DeleteEpisodeCommand(episodes, video_paths, loaded_episodes, "1")
        assert cmd.get_description() == "Удалена серия: 1"


# =============================================================================
# Tests for UpdateProjectNameCommand
# =============================================================================

class TestUpdateProjectNameCommand:
    """Тесты для команды обновления названия проекта"""

    def test_execute(self):
        """Тест выполнения команды"""
        data = {"project_name": "Старое название"}
        cmd = UpdateProjectNameCommand(data, "Новое название")
        cmd.execute()

        assert data["project_name"] == "Новое название"

    def test_undo(self):
        """Тест отмены команды"""
        data = {"project_name": "Старое название"}
        cmd = UpdateProjectNameCommand(data, "Новое название")
        cmd.execute()
        assert data["project_name"] == "Новое название"

        cmd.undo()
        assert data["project_name"] == "Старое название"

    def test_get_description(self):
        """Тест описания команды"""
        data = {"project_name": "Старое название"}
        cmd = UpdateProjectNameCommand(data, "Новое название")
        cmd.execute()
        assert "Переименован проект:" in cmd.get_description()


# =============================================================================
# Tests for SetProjectFolderCommand
# =============================================================================

class TestSetProjectFolderCommand:
    """Тесты для команды установки папки проекта"""

    def test_execute(self):
        """Тест выполнения команды"""
        data = {"project_folder": None}
        cmd = SetProjectFolderCommand(data, "/new/folder")
        cmd.execute()

        assert data["project_folder"] == "/new/folder"

    def test_undo(self):
        """Тест отмены команды"""
        data = {"project_folder": "/old/folder"}
        cmd = SetProjectFolderCommand(data, "/new/folder")
        cmd.execute()
        assert data["project_folder"] == "/new/folder"

        cmd.undo()
        assert data["project_folder"] == "/old/folder"

    def test_get_description(self):
        """Тест описания команды"""
        data = {"project_folder": None}
        cmd = SetProjectFolderCommand(data, "/new/folder")
        assert "Установлена папка:" in cmd.get_description()
