"""Service for managing actors."""

import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from config.constants import MY_PALETTE

logger = logging.getLogger(__name__)


class ActorService:
    """Actor Service implementation."""

    def __init__(self):
        self._color_index = 0

    def add_actor(
        self,
        actors: Dict[str, dict],
        name: str,
        color: Optional[str] = None
    ) -> str:
        """Add actor."""
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
        """Update actor color."""
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
        """Rename actor."""
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
        """Delete actor."""
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
        """Assign actor to character."""
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
        """Bulk assign actors."""
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
        """Return actor roles."""
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
        """Update actor roles."""
        # Remove old mappings
        keys_to_remove = [
            k for k, v in global_map.items()
            if v == actor_id
        ]
        for key in keys_to_remove:
            del global_map[key]

        # Add new mappings
        for role_name in new_roles:
            global_map[role_name] = actor_id

    def get_actor_statistics(
        self,
        actors: Dict[str, dict],
        global_map: Dict[str, str],
        episode_stats: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Return actor statistics."""
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
        """Return the next available palette color."""
        used_colors = {
            actor.get("color", "").upper()
            for actor in actors.values()
        }

        for _ in range(len(MY_PALETTE)):
            color = MY_PALETTE[self._color_index]
            self._color_index = (self._color_index + 1) % len(MY_PALETTE)

            if color.upper() not in used_colors:
                return color

        # Return a random color when the palette is exhausted
        import random
        return random.choice(MY_PALETTE)

    def get_unassigned_characters(
        self,
        global_map: Dict[str, str],
        episode_stats: List[Dict[str, Any]]
    ) -> List[str]:
        """Return unassigned characters."""
        return [
            stat["name"] for stat in episode_stats
            if stat["name"] not in global_map
        ]
