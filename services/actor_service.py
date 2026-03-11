"""Сервис для управления актёрами"""

import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from config.constants import MY_PALETTE

logger = logging.getLogger(__name__)


class ActorService:
    """Сервис для работы с актёрами: добавление, редактирование, назначение ролей"""

    def __init__(self):
        self._color_index = 0

    def add_actor(
        self,
        actors: Dict[str, dict],
        name: str,
        color: Optional[str] = None
    ) -> str:
        """
        Добавление нового актёра

        Args:
            actors: словарь актёров проекта
            name: имя актёра
            color: цвет актёра (если None - выбирается автоматически)

        Returns:
            ID нового актёра
        """
        actor_id = str(datetime.now().timestamp())

        if not color:
            color = self._get_next_color(actors)

        actors[actor_id] = {
            "name": name,
            "color": color,
            "roles": []
        }

        logger.info(f"Actor added: {name} ({actor_id})")
        return actor_id

    def update_actor_color(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        color: str
    ) -> bool:
        """
        Обновление цвета актёра

        Args:
            actors: словарь актёров
            actor_id: ID актёра
            color: новый цвет

        Returns:
            True если успешно
        """
        if actor_id not in actors:
            return False

        actors[actor_id]["color"] = color
        logger.debug(f"Actor color updated: {actor_id} -> {color}")
        return True

    def rename_actor(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_name: str
    ) -> bool:
        """
        Переименование актёра

        Args:
            actors: словарь актёров
            actor_id: ID актёра
            new_name: новое имя

        Returns:
            True если успешно
        """
        if actor_id not in actors:
            return False

        actors[actor_id]["name"] = new_name
        logger.debug(f"Actor renamed: {actor_id} -> {new_name}")
        return True

    def delete_actor(
        self,
        actors: Dict[str, dict],
        actor_id: str
    ) -> bool:
        """
        Удаление актёра

        Args:
            actors: словарь актёров
            actor_id: ID актёра

        Returns:
            True если успешно
        """
        if actor_id not in actors:
            return False

        del actors[actor_id]
        logger.info(f"Actor deleted: {actor_id}")
        return True

    def assign_actor_to_character(
        self,
        global_map: Dict[str, str],
        character_name: str,
        actor_id: Optional[str]
    ) -> None:
        """
        Назначение актёра на персонажа

        Args:
            global_map: глобальная карта маппинга
            character_name: имя персонажа
            actor_id: ID актёра (None для удаления назначения)
        """
        if actor_id:
            global_map[character_name] = actor_id
        else:
            global_map.pop(character_name, None)

    def bulk_assign_actors(
        self,
        global_map: Dict[str, str],
        characters: List[str],
        actor_id: Optional[str]
    ) -> int:
        """
        Массовое назначение актёра на персонажей

        Args:
            global_map: глобальная карта маппинга
            characters: список имён персонажей
            actor_id: ID актёра (None для удаления назначения)

        Returns:
            Количество назначенных персонажей
        """
        count = 0
        for char in characters:
            if actor_id:
                global_map[char] = actor_id
            else:
                global_map.pop(char, None)
            count += 1
        return count

    def get_actor_roles(
        self,
        global_map: Dict[str, str],
        actor_id: str
    ) -> List[str]:
        """
        Получение списка ролей актёра

        Args:
            global_map: глобальная карта маппинга
            actor_id: ID актёра

        Returns:
            Список имён персонажей
        """
        return [
            char for char, aid in global_map.items()
            if aid == actor_id
        ]

    def update_actor_roles(
        self,
        global_map: Dict[str, str],
        actor_id: str,
        new_roles: List[str]
    ) -> None:
        """
        Обновление ролей актёра

        Args:
            global_map: глобальная карта маппинга
            actor_id: ID актёра
            new_roles: новый список ролей
        """
        # Удаляем старые маппинги
        keys_to_remove = [
            k for k, v in global_map.items()
            if v == actor_id
        ]
        for key in keys_to_remove:
            del global_map[key]

        # Добавляем новые
        for role_name in new_roles:
            global_map[role_name] = actor_id

    def get_actor_statistics(
        self,
        actors: Dict[str, dict],
        global_map: Dict[str, str],
        episode_stats: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получение статистики по актёрам

        Args:
            actors: словарь актёров
            global_map: глобальная карта маппинга
            episode_stats: статистика эпизода

        Returns:
            Словарь со статистикой по каждому актёру
        """
        stats = {}

        for actor_id, actor in actors.items():
            roles = self.get_actor_roles(global_map, actor_id)

            total_lines = 0
            total_words = 0

            for stat in episode_stats:
                if stat["name"] in roles:
                    total_lines += stat["lines"]
                    total_words += stat["words"]

            stats[actor_id] = {
                "name": actor["name"],
                "color": actor["color"],
                "roles": roles,
                "total_lines": total_lines,
                "total_words": total_words
            }

        return stats

    def _get_next_color(self, actors: Dict[str, dict]) -> str:
        """Получение следующего свободного цвета из палитры"""
        used_colors = {
            actor.get("color", "").upper()
            for actor in actors.values()
        }

        for _ in range(len(MY_PALETTE)):
            color = MY_PALETTE[self._color_index]
            self._color_index = (self._color_index + 1) % len(MY_PALETTE)

            if color.upper() not in used_colors:
                return color

        # Если все цвета заняты - возвращаем случайный
        import random
        return random.choice(MY_PALETTE)

    def get_unassigned_characters(
        self,
        global_map: Dict[str, str],
        episode_stats: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Получение списка неназначенных персонажей

        Args:
            global_map: глобальная карта маппинга
            episode_stats: статистика эпизода

        Returns:
            Список имён неназначенных персонажей
        """
        return [
            stat["name"] for stat in episode_stats
            if stat["name"] not in global_map
        ]
