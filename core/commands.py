"""Система отмены/повтора действий (Undo/Redo)"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)


class Command(ABC):
    """
    Базовый класс команды для системы Undo/Redo.
    
    Все команды должны наследовать этот класс и реализовать:
    - execute(): выполнение действия
    - undo(): отмена действия
    - get_description(): текстовое описание для UI
    """

    @abstractmethod
    def execute(self) -> None:
        """Выполнение команды"""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Отмена команды"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Текстовое описание команды для отображения в UI"""
        pass


class AddActorCommand(Command):
    """Команда добавления актёра"""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        name: str,
        color: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.name = name
        self.color = color
        self._old_data: Optional[dict] = None

    def execute(self) -> None:
        self._old_data = self.actors.get(self.actor_id)
        self.actors[self.actor_id] = {
            "name": self.name,
            "color": self.color,
            "roles": []
        }
        logger.debug(f"AddActorCommand executed: {self.name}")

    def undo(self) -> None:
        if self._old_data is not None:
            self.actors[self.actor_id] = self._old_data
        else:
            self.actors.pop(self.actor_id, None)
        logger.debug(f"AddActorCommand undone: {self.name}")

    def get_description(self) -> str:
        return f"Добавлен актёр: {self.name}"


class DeleteActorCommand(Command):
    """Команда удаления актёра"""

    def __init__(
        self,
        actors: Dict[str, dict],
        global_map: Dict[str, str],
        actor_id: str
    ):
        self.actors = actors
        self.global_map = global_map
        self.actor_id = actor_id
        self._deleted_data: Optional[dict] = None
        self._removed_mappings: List[tuple] = []

    def execute(self) -> None:
        self._deleted_data = self.actors.get(self.actor_id)

        # Сохраняем и удаляем маппинги
        self._removed_mappings = [
            (char, aid) for char, aid in self.global_map.items()
            if aid == self.actor_id
        ]
        # Явно создаём копию списка ключей для безопасного удаления
        chars_to_remove = [char for char, aid in self.global_map.items() if aid == self.actor_id]
        for char in chars_to_remove:
            del self.global_map[char]

        # Удаляем актёра
        if self.actor_id in self.actors:
            del self.actors[self.actor_id]

        logger.debug(f"DeleteActorCommand executed: {self.actor_id}")

    def undo(self) -> None:
        # Восстанавливаем актёра
        if self._deleted_data:
            self.actors[self.actor_id] = self._deleted_data
        
        # Восстанавливаем маппинги
        for char, aid in self._removed_mappings:
            self.global_map[char] = aid
        
        logger.debug(f"DeleteActorCommand undone: {self.actor_id}")

    def get_description(self) -> str:
        actor_name = self._deleted_data["name"] if self._deleted_data else "Неизвестный"
        return f"Удалён актёр: {actor_name}"


class RenameActorCommand(Command):
    """Команда переименования актёра"""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_name: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.new_name = new_name
        self._old_name: Optional[str] = None

    def execute(self) -> None:
        if self.actor_id in self.actors:
            self._old_name = self.actors[self.actor_id]["name"]
            self.actors[self.actor_id]["name"] = self.new_name
        logger.debug(f"RenameActorCommand executed: {self.actor_id} -> {self.new_name}")

    def undo(self) -> None:
        if self.actor_id in self.actors and self._old_name:
            self.actors[self.actor_id]["name"] = self._old_name
        logger.debug(f"RenameActorCommand undone: {self.actor_id} -> {self._old_name}")

    def get_description(self) -> str:
        return f"Переименован актёр: {self._old_name} -> {self.new_name}"


class UpdateActorColorCommand(Command):
    """Команда обновления цвета актёра"""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_color: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.new_color = new_color
        self._old_color: Optional[str] = None

    def execute(self) -> None:
        if self.actor_id in self.actors:
            self._old_color = self.actors[self.actor_id]["color"]
            self.actors[self.actor_id]["color"] = self.new_color
        logger.debug(f"UpdateActorColorCommand executed: {self.actor_id} -> {self.new_color}")

    def undo(self) -> None:
        if self.actor_id in self.actors and self._old_color:
            self.actors[self.actor_id]["color"] = self._old_color
        logger.debug(f"UpdateActorColorCommand undone: {self.actor_id} -> {self._old_color}")

    def get_description(self) -> str:
        return f"Изменён цвет актёра: {self._old_color} -> {self.new_color}"


class AssignActorToCharacterCommand(Command):
    """Команда назначения актёра на персонажа"""

    def __init__(
        self,
        global_map: Dict[str, str],
        character_name: str,
        actor_id: Optional[str]
    ):
        self.global_map = global_map
        self.character_name = character_name
        self.actor_id = actor_id
        self._old_actor_id: Optional[str] = None

    def execute(self) -> None:
        self._old_actor_id = self.global_map.get(self.character_name)
        if self.actor_id:
            self.global_map[self.character_name] = self.actor_id
        elif self.character_name in self.global_map:
            del self.global_map[self.character_name]
        logger.debug(f"AssignActorToCharacterCommand executed: {self.character_name} -> {self.actor_id}")

    def undo(self) -> None:
        if self._old_actor_id:
            self.global_map[self.character_name] = self._old_actor_id
        elif self.character_name in self.global_map:
            del self.global_map[self.character_name]
        logger.debug(f"AssignActorToCharacterCommand undone: {self.character_name}")

    def get_description(self) -> str:
        return f"Назначен актёр для: {self.character_name}"


class RenameCharacterCommand(Command):
    """Команда переименования персонажа"""

    def __init__(
        self,
        global_map: Dict[str, str],
        loaded_episodes: Dict[str, List[Dict[str, Any]]],
        current_ep_stats: List[Dict[str, Any]],
        episode: str,
        old_name: str,
        new_name: str,
        rename_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.global_map = global_map
        self.loaded_episodes = loaded_episodes
        self.current_ep_stats = current_ep_stats
        self.episode = episode
        self.old_name = old_name
        self.new_name = new_name
        self.rename_callback = rename_callback

    def execute(self) -> None:
        self._update_names(self.old_name, self.new_name)
        logger.debug(f"RenameCharacterCommand executed: {self.old_name} -> {self.new_name}")

    def undo(self) -> None:
        self._update_names(self.new_name, self.old_name)
        logger.debug(f"RenameCharacterCommand undone: {self.new_name} -> {self.old_name}")

    def _update_names(self, from_name: str, to_name: str) -> None:
        # Обновляем global_map
        if from_name in self.global_map:
            actor_id = self.global_map[from_name]
            del self.global_map[from_name]
            self.global_map[to_name] = actor_id

        # Обновляем загруженные эпизоды
        if self.episode in self.loaded_episodes:
            for line in self.loaded_episodes[self.episode]:
                if line.get('char') == from_name:
                    line['char'] = to_name

        # Обновляем статистику эпизода
        for stat in self.current_ep_stats:
            if stat.get("name") == from_name:
                stat["name"] = to_name
                break

        if self.rename_callback:
            self.rename_callback(from_name, to_name)

    def get_description(self) -> str:
        return f"Переименован персонаж: {self.old_name} -> {self.new_name}"


class AddEpisodeCommand(Command):
    """Команда добавления эпизода"""

    def __init__(
        self,
        episodes: Dict[str, str],
        episode_num: str,
        path: str
    ):
        self.episodes = episodes
        self.episode_num = episode_num
        self.path = path
        self._old_path: Optional[str] = None

    def execute(self) -> None:
        self._old_path = self.episodes.get(self.episode_num)
        self.episodes[self.episode_num] = self.path
        logger.debug(f"AddEpisodeCommand executed: {self.episode_num} -> {self.path}")

    def undo(self) -> None:
        if self._old_path is not None:
            self.episodes[self.episode_num] = self._old_path
        else:
            self.episodes.pop(self.episode_num, None)
        logger.debug(f"AddEpisodeCommand undone: {self.episode_num}")

    def get_description(self) -> str:
        return f"Добавлена серия: {self.episode_num}"


class RenameEpisodeCommand(Command):
    """Команда переименования эпизода"""

    def __init__(
        self,
        episodes: Dict[str, str],
        old_name: str,
        new_name: str
    ):
        self.episodes = episodes
        self.old_name = old_name
        self.new_name = new_name
        self._old_data: Optional[str] = None

    def execute(self) -> None:
        self._old_data = self.episodes.get(self.old_name)
        if self._old_data:
            del self.episodes[self.old_name]
            self.episodes[self.new_name] = self._old_data
        logger.debug(f"RenameEpisodeCommand executed: {self.old_name} -> {self.new_name}")

    def undo(self) -> None:
        if self._old_data:
            del self.episodes[self.new_name]
            self.episodes[self.old_name] = self._old_data
        logger.debug(f"RenameEpisodeCommand undone: {self.new_name} -> {self.old_name}")

    def get_description(self) -> str:
        return f"Переименована серия: {self.old_name} -> {self.new_name}"


class DeleteEpisodeCommand(Command):
    """Команда удаления эпизода"""

    def __init__(
        self,
        episodes: Dict[str, str],
        video_paths: Dict[str, str],
        loaded_episodes: Dict[str, List[Dict[str, Any]]],
        episode_num: str
    ):
        self.episodes = episodes
        self.video_paths = video_paths
        self.loaded_episodes = loaded_episodes
        self.episode_num = episode_num
        self._deleted_episode: Optional[str] = None
        self._deleted_video: Optional[str] = None
        self._deleted_loaded_data: Optional[List[Dict[str, Any]]] = None

    def execute(self) -> None:
        self._deleted_episode = self.episodes.get(self.episode_num)
        self._deleted_video = self.video_paths.get(self.episode_num)
        self._deleted_loaded_data = self.loaded_episodes.get(self.episode_num)

        self.episodes.pop(self.episode_num, None)
        self.video_paths.pop(self.episode_num, None)
        self.loaded_episodes.pop(self.episode_num, None)

        logger.debug(f"DeleteEpisodeCommand executed: {self.episode_num}")

    def undo(self) -> None:
        if self._deleted_episode:
            self.episodes[self.episode_num] = self._deleted_episode
        if self._deleted_video:
            self.video_paths[self.episode_num] = self._deleted_video
        if self._deleted_loaded_data:
            self.loaded_episodes[self.episode_num] = self._deleted_loaded_data

        logger.debug(f"DeleteEpisodeCommand undone: {self.episode_num}")

    def get_description(self) -> str:
        return f"Удалена серия: {self.episode_num}"


class UpdateProjectNameCommand(Command):
    """Команда переименования проекта"""

    def __init__(
        self,
        data: Dict[str, Any],
        new_name: str
    ):
        self.data = data
        self.new_name = new_name
        self._old_name: Optional[str] = None

    def execute(self) -> None:
        self._old_name = self.data.get("project_name")
        self.data["project_name"] = self.new_name
        logger.debug(f"UpdateProjectNameCommand executed: {self._old_name} -> {self.new_name}")

    def undo(self) -> None:
        if self._old_name:
            self.data["project_name"] = self._old_name
        logger.debug(f"UpdateProjectNameCommand undone: {self.new_name} -> {self._old_name}")

    def get_description(self) -> str:
        return f"Переименован проект: {self._old_name} -> {self.new_name}"


class SetProjectFolderCommand(Command):
    """Команда установки папки проекта"""

    def __init__(
        self,
        data: Dict[str, Any],
        folder_path: Optional[str]
    ):
        self.data = data
        self.folder_path = folder_path
        self._old_folder: Optional[str] = None

    def execute(self) -> None:
        self._old_folder = self.data.get("project_folder")
        if self.folder_path:
            self.data["project_folder"] = self.folder_path
        elif "project_folder" in self.data:
            del self.data["project_folder"]
        logger.debug(f"SetProjectFolderCommand executed: {self.folder_path}")

    def undo(self) -> None:
        if self._old_folder:
            self.data["project_folder"] = self._old_folder
        elif "project_folder" in self.data:
            del self.data["project_folder"]
        logger.debug(f"SetProjectFolderCommand undone")

    def get_description(self) -> str:
        if self.folder_path:
            folder_name = os.path.basename(self.folder_path)
            return f"Установлена папка: {folder_name}"
        return "Папка проекта очищена"


class UndoStack:
    """
    Стек отмены/повтора действий.

    Хранит историю выполненных команд и позволяет:
    - Отменять последние действия (undo)
    - Повторять отменённые действия (redo)
    - Очищать историю
    
    Примечание: для предотвращения утечки памяти при достижении
    max_size старые команды удаляются без вызова undo().
    """

    def __init__(self, max_size: int = 100):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_size = max_size
        self._on_change_callbacks: List[Callable] = []

    def push(self, command: Command) -> None:
        """
        Выполнение и сохранение команды.

        Args:
            command: Команда для выполнения
        """
        command.execute()
        self._undo_stack.append(command)

        # Ограничиваем размер стека - удаляем старые команды
        # (без вызова undo, т.к. они уже применены)
        while len(self._undo_stack) > self._max_size:
            old_command = self._undo_stack.pop(0)
            # Очищаем ссылки на данные для предотвращения утечек памяти
            self._cleanup_command(old_command)

        # Очищаем redo стек при новом действии
        self._redo_stack.clear()

        self._notify_change()
        logger.debug(f"Command pushed: {command.get_description()}")

    def _cleanup_command(self, command: Command) -> None:
        """
        Очистка ссылок на данные в команде для предотвращения утечек памяти.
        
        Args:
            command: Команда для очистки
        """
        # Очищаем атрибуты команды, которые могут держать большие объекты
        for attr_name in ['_old_data', '_deleted_data', '_removed_mappings', 
                          '_old_name', '_old_color', '_old_folder', '_old_actor_id']:
            if hasattr(command, attr_name):
                setattr(command, attr_name, None)

    def undo(self) -> bool:
        """
        Отмена последнего действия.
        
        Returns:
            True если отмена успешна
        """
        if not self._undo_stack:
            logger.debug("Undo failed: stack is empty")
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        
        self._notify_change()
        logger.debug(f"Undo performed: {command.get_description()}")
        return True

    def redo(self) -> bool:
        """
        Повтор отменённого действия.
        
        Returns:
            True если повтор успешен
        """
        if not self._redo_stack:
            logger.debug("Redo failed: stack is empty")
            return False

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        
        self._notify_change()
        logger.debug(f"Redo performed: {command.get_description()}")
        return True

    def can_undo(self) -> bool:
        """Проверка возможности отмены"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Проверка возможности повтора"""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Очистка всех стеков с освобождением памяти"""
        # Очищаем все команды для освобождения памяти
        for command in self._undo_stack:
            self._cleanup_command(command)
        for command in self._redo_stack:
            self._cleanup_command(command)
            
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_change()
        logger.debug("UndoStack cleared")

    def on_change(self, callback: Callable) -> None:
        """
        Регистрация обработчика изменений стека.
        
        Args:
            callback: Функция обратного вызова
        """
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Уведомление подписчиков об изменении"""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"UndoStack callback error: {e}")
