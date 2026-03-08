"""Тесты для системы Undo/Redo"""

import pytest
import os
import tempfile
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


class TestUndoStack:
    """Тесты для UndoStack"""

    def test_empty_stack_cannot_undo(self):
        stack = UndoStack()
        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_push_enables_undo(self):
        stack = UndoStack()
        actors = {}
        command = AddActorCommand(actors, "id1", "Actor", "#FFFFFF")
        stack.push(command)
        
        assert stack.can_undo()
        assert not stack.can_redo()

    def test_undo_redo(self):
        stack = UndoStack()
        actors = {}
        
        command = AddActorCommand(actors, "id1", "Actor", "#FFFFFF")
        stack.push(command)
        
        assert "id1" in actors
        assert stack.can_undo()
        
        # Undo
        result = stack.undo()
        assert result is True
        assert "id1" not in actors
        assert not stack.can_undo()
        assert stack.can_redo()
        
        # Redo
        result = stack.redo()
        assert result is True
        assert "id1" in actors
        assert stack.can_undo()
        assert not stack.can_redo()

    def test_clear(self):
        stack = UndoStack()
        actors = {}
        
        command = AddActorCommand(actors, "id1", "Actor", "#FFFFFF")
        stack.push(command)
        stack.undo()
        
        stack.clear()
        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_new_command_clears_redo_stack(self):
        stack = UndoStack()
        actors = {}
        
        command1 = AddActorCommand(actors, "id1", "Actor1", "#FFFFFF")
        stack.push(command1)
        stack.undo()
        
        assert stack.can_redo()
        
        command2 = AddActorCommand(actors, "id2", "Actor2", "#000000")
        stack.push(command2)
        
        assert not stack.can_redo()


class TestAddActorCommand:
    """Тесты для AddActorCommand"""

    def test_execute_adds_actor(self):
        actors = {}
        command = AddActorCommand(actors, "id1", "Actor", "#FFFFFF")
        command.execute()
        
        assert "id1" in actors
        assert actors["id1"]["name"] == "Actor"
        assert actors["id1"]["color"] == "#FFFFFF"

    def test_undo_removes_actor(self):
        actors = {}
        command = AddActorCommand(actors, "id1", "Actor", "#FFFFFF")
        command.execute()
        command.undo()
        
        assert "id1" not in actors

    def test_description(self):
        command = AddActorCommand({}, "id1", "Actor", "#FFFFFF")
        assert command.get_description() == "Добавлен актёр: Actor"


class TestDeleteActorCommand:
    """Тесты для DeleteActorCommand"""

    def test_execute_removes_actor_and_mappings(self):
        actors = {"id1": {"name": "Actor", "color": "#FFFFFF", "roles": []}}
        global_map = {"Character1": "id1", "Character2": "id1"}
        
        command = DeleteActorCommand(actors, global_map, "id1")
        command.execute()
        
        assert "id1" not in actors
        assert "Character1" not in global_map
        assert "Character2" not in global_map

    def test_undo_restores_actor_and_mappings(self):
        actors = {"id1": {"name": "Actor", "color": "#FFFFFF", "roles": []}}
        global_map = {"Character1": "id1", "Character2": "id1"}
        
        command = DeleteActorCommand(actors, global_map, "id1")
        command.execute()
        command.undo()
        
        assert "id1" in actors
        assert actors["id1"]["name"] == "Actor"
        assert global_map["Character1"] == "id1"
        assert global_map["Character2"] == "id1"


class TestRenameActorCommand:
    """Тесты для RenameActorCommand"""

    def test_execute_renames_actor(self):
        actors = {"id1": {"name": "OldName", "color": "#FFFFFF", "roles": []}}
        command = RenameActorCommand(actors, "id1", "NewName")
        command.execute()
        
        assert actors["id1"]["name"] == "NewName"

    def test_undo_restores_old_name(self):
        actors = {"id1": {"name": "OldName", "color": "#FFFFFF", "roles": []}}
        command = RenameActorCommand(actors, "id1", "NewName")
        command.execute()
        command.undo()
        
        assert actors["id1"]["name"] == "OldName"


class TestUpdateActorColorCommand:
    """Тесты для UpdateActorColorCommand"""

    def test_execute_updates_color(self):
        actors = {"id1": {"name": "Actor", "color": "#FFFFFF", "roles": []}}
        command = UpdateActorColorCommand(actors, "id1", "#000000")
        command.execute()
        
        assert actors["id1"]["color"] == "#000000"

    def test_undo_restores_old_color(self):
        actors = {"id1": {"name": "Actor", "color": "#FFFFFF", "roles": []}}
        command = UpdateActorColorCommand(actors, "id1", "#000000")
        command.execute()
        command.undo()
        
        assert actors["id1"]["color"] == "#FFFFFF"


class TestAssignActorToCharacterCommand:
    """Тесты для AssignActorToCharacterCommand"""

    def test_execute_assigns_actor(self):
        global_map = {}
        command = AssignActorToCharacterCommand(global_map, "Character", "id1")
        command.execute()
        
        assert global_map["Character"] == "id1"

    def test_execute_removes_assignment_when_none(self):
        global_map = {"Character": "id1"}
        command = AssignActorToCharacterCommand(global_map, "Character", None)
        command.execute()
        
        assert "Character" not in global_map

    def test_undo_restores_previous_assignment(self):
        global_map = {"Character": "old_id"}
        command = AssignActorToCharacterCommand(global_map, "Character", "new_id")
        command.execute()
        command.undo()
        
        assert global_map["Character"] == "old_id"


class TestRenameCharacterCommand:
    """Тесты для RenameCharacterCommand"""

    def test_execute_renames_character(self):
        global_map = {"OldName": "id1"}
        loaded_episodes = {"ep1": [{"char": "OldName", "text": "Test"}]}
        current_ep_stats = [{"name": "OldName", "lines": 1}]
        
        command = RenameCharacterCommand(
            global_map, loaded_episodes, current_ep_stats,
            "ep1", "OldName", "NewName"
        )
        command.execute()
        
        assert "NewName" in global_map
        assert "OldName" not in global_map
        assert loaded_episodes["ep1"][0]["char"] == "NewName"
        assert current_ep_stats[0]["name"] == "NewName"

    def test_undo_restores_old_name(self):
        global_map = {"OldName": "id1"}
        loaded_episodes = {"ep1": [{"char": "OldName", "text": "Test"}]}
        current_ep_stats = [{"name": "OldName", "lines": 1}]
        
        command = RenameCharacterCommand(
            global_map, loaded_episodes, current_ep_stats,
            "ep1", "OldName", "NewName"
        )
        command.execute()
        command.undo()
        
        assert "OldName" in global_map
        assert "NewName" not in global_map
        assert loaded_episodes["ep1"][0]["char"] == "OldName"
        assert current_ep_stats[0]["name"] == "OldName"


class TestAddEpisodeCommand:
    """Тесты для AddEpisodeCommand"""

    def test_execute_adds_episode(self):
        episodes = {}
        command = AddEpisodeCommand(episodes, "1", "/path/to/file.ass")
        command.execute()
        
        assert episodes["1"] == "/path/to/file.ass"

    def test_undo_removes_episode(self):
        episodes = {}
        command = AddEpisodeCommand(episodes, "1", "/path/to/file.ass")
        command.execute()
        command.undo()
        
        assert "1" not in episodes


class TestRenameEpisodeCommand:
    """Тесты для RenameEpisodeCommand"""

    def test_execute_renames_episode(self):
        episodes = {"1": "/path/to/file.ass"}
        command = RenameEpisodeCommand(episodes, "1", "2")
        command.execute()
        
        assert "2" in episodes
        assert "1" not in episodes
        assert episodes["2"] == "/path/to/file.ass"

    def test_undo_restores_old_name(self):
        episodes = {"1": "/path/to/file.ass"}
        command = RenameEpisodeCommand(episodes, "1", "2")
        command.execute()
        command.undo()
        
        assert "1" in episodes
        assert "2" not in episodes
        assert episodes["1"] == "/path/to/file.ass"


class TestDeleteEpisodeCommand:
    """Тесты для DeleteEpisodeCommand"""

    def test_execute_removes_episode(self):
        episodes = {"1": "/path/to/file.ass"}
        video_paths = {"1": "/path/to/video.mp4"}
        loaded_episodes = {"1": [{"char": "Test"}]}
        
        command = DeleteEpisodeCommand(
            episodes, video_paths, loaded_episodes, "1"
        )
        command.execute()
        
        assert "1" not in episodes
        assert "1" not in video_paths
        assert "1" not in loaded_episodes

    def test_undo_restores_episode(self):
        episodes = {"1": "/path/to/file.ass"}
        video_paths = {"1": "/path/to/video.mp4"}
        loaded_episodes = {"1": [{"char": "Test"}]}
        
        command = DeleteEpisodeCommand(
            episodes, video_paths, loaded_episodes, "1"
        )
        command.execute()
        command.undo()
        
        assert episodes["1"] == "/path/to/file.ass"
        assert video_paths["1"] == "/path/to/video.mp4"
        assert loaded_episodes["1"] == [{"char": "Test"}]


class TestUpdateProjectNameCommand:
    """Тесты для UpdateProjectNameCommand"""

    def test_execute_updates_name(self):
        data = {"project_name": "Old Project"}
        command = UpdateProjectNameCommand(data, "New Project")
        command.execute()
        
        assert data["project_name"] == "New Project"

    def test_undo_restores_old_name(self):
        data = {"project_name": "Old Project"}
        command = UpdateProjectNameCommand(data, "New Project")
        command.execute()
        command.undo()
        
        assert data["project_name"] == "Old Project"


class TestSetProjectFolderCommand:
    """Тесты для SetProjectFolderCommand"""

    def test_execute_sets_folder(self):
        data = {}
        command = SetProjectFolderCommand(data, "/path/to/folder")
        command.execute()
        
        assert data["project_folder"] == "/path/to/folder"

    def test_undo_removes_folder(self):
        data = {}
        command = SetProjectFolderCommand(data, "/path/to/folder")
        command.execute()
        command.undo()
        
        assert "project_folder" not in data

    def test_execute_clears_folder(self):
        data = {"project_folder": "/old/path"}
        command = SetProjectFolderCommand(data, None)
        command.execute()
        
        assert "project_folder" not in data

    def test_undo_restores_folder(self):
        data = {"project_folder": "/old/path"}
        command = SetProjectFolderCommand(data, None)
        command.execute()
        command.undo()
        
        assert data["project_folder"] == "/old/path"

    def test_description_with_folder(self):
        command = SetProjectFolderCommand({}, "/path/to/my_project")
        desc = command.get_description()
        assert "my_project" in desc

    def test_description_clear(self):
        command = SetProjectFolderCommand({}, None)
        desc = command.get_description()
        assert "очищена" in desc.lower() or "folder" in desc.lower()
