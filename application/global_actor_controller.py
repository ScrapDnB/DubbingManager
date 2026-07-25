"""Controller for project/global actor synchronization."""

from typing import Any, Dict


class GlobalActorController:
    """Synchronize project actor records with the global actor base."""

    def __init__(
        self,
        data_ref: Dict[str, Any],
        global_settings_service: Any,
    ) -> None:
        self.data_ref = data_ref
        self.global_settings_service = global_settings_service

    def sync_project_actors_with_global_base(self) -> int:
        """Sync project actor records with global actor records by name."""
        actors = self.data_ref.get("actors", {})
        if not isinstance(actors, dict) or not actors:
            return 0

        actor_base = self.global_settings_service.get_global_actor_base()
        if not actor_base:
            return 0

        global_by_name = {
            self.actor_name_key(actor.get("name", "")): (actor_id, actor)
            for actor_id, actor in actor_base.items()
            if isinstance(actor, dict) and self.actor_name_key(actor.get("name", ""))
        }

        changed = 0
        for project_actor_id, project_actor in list(actors.items()):
            if not isinstance(project_actor, dict):
                continue

            match = global_by_name.get(
                self.actor_name_key(project_actor.get("name", ""))
            )
            if not match:
                continue

            global_actor_id, global_actor = match
            if self.merge_project_actor_with_global(
                project_actor_id,
                global_actor_id,
                global_actor
            ):
                changed += 1

        return changed

    def actor_name_key(self, name: str) -> str:
        """Return a stable comparison key for actor names."""
        return " ".join(str(name or "").split()).casefold()

    def add_global_actor(
        self,
        global_settings: Dict[str, Any],
        name: str,
        gender: str
    ) -> bool:
        """Add an actor to the global actor base."""
        if self.global_settings_service.find_global_actor_by_name(name):
            return False
        self.global_settings_service.add_global_actor(name, gender=gender)
        self._store_global_actor_base(global_settings)
        return True

    def remove_global_actor(
        self,
        global_settings: Dict[str, Any],
        actor_id: str
    ) -> bool:
        """Remove an actor from the global actor base."""
        if not self.global_settings_service.remove_global_actor(actor_id):
            return False
        self._store_global_actor_base(global_settings)
        return True

    def global_actor_data(self, actor_id: str) -> Dict[str, Any]:
        """Return one global actor record."""
        return self.global_settings_service.get_global_actor_base().get(
            actor_id,
            {}
        )

    def project_actor_transfer_rows(self) -> tuple[list[dict[str, Any]], int]:
        """Return project actors annotated for adding to global base."""
        project_actors = self.data_ref.get("actors", {})
        global_names = {
            actor.get("name", "").strip().casefold()
            for actor in self.global_settings_service.get_global_actor_base().values()
            if isinstance(actor, dict)
        }

        rows = []
        available_count = 0
        for actor_id, actor in sorted(
            project_actors.items(),
            key=lambda item: item[1].get("name", "").lower()
        ):
            name = actor.get("name", actor_id)
            exists = name.strip().casefold() in global_names
            rows.append({
                "actor_id": actor_id,
                "name": name,
                "exists": exists,
                "label": f"{name} — уже есть в глобальной базе" if exists else name,
            })
            if not exists:
                available_count += 1
        return rows, available_count

    def add_project_actors_to_global(
        self,
        global_settings: Dict[str, Any],
        selected_ids: list[str]
    ) -> Dict[str, Any]:
        """Add selected project actors to the global actor base."""
        stats = self.global_settings_service.add_project_actors_to_global(
            self.data_ref.get("actors", {}),
            selected_ids
        )
        self._store_global_actor_base(global_settings)
        return stats

    def _store_global_actor_base(self, global_settings: Dict[str, Any]) -> None:
        """Persist the global actor base into global settings."""
        global_settings["global_actor_base"] = (
            self.global_settings_service.get_global_actor_base()
        )
        self.global_settings_service.save_settings(global_settings)

    def merge_project_actor_with_global(
        self,
        project_actor_id: str,
        global_actor_id: str,
        global_actor: Dict[str, Any]
    ) -> bool:
        """Merge one project actor with a global actor record."""
        actors = self.data_ref.setdefault("actors", {})
        old_actor = actors.get(project_actor_id)
        if not isinstance(old_actor, dict):
            return False

        merged_actor = old_actor.copy()
        merged_actor.update({
            "name": global_actor.get("name", old_actor.get("name", "")),
            "gender": global_actor.get("gender", old_actor.get("gender", "")),
        })

        changed = False
        if project_actor_id != global_actor_id:
            if global_actor_id in actors and isinstance(actors[global_actor_id], dict):
                target_actor = actors[global_actor_id].copy()
                target_actor.update(merged_actor)
                actors[global_actor_id] = target_actor
            else:
                actors[global_actor_id] = merged_actor
            del actors[project_actor_id]
            self.replace_project_actor_references(
                project_actor_id,
                global_actor_id
            )
            changed = True
        elif actors.get(project_actor_id) != merged_actor:
            actors[project_actor_id] = merged_actor
            changed = True

        return changed

    def replace_project_actor_references(
        self,
        old_actor_id: str,
        new_actor_id: str
    ) -> None:
        """Replace actor ids in project assignment and filter data."""
        for mapping_name in ("global_map",):
            mapping = self.data_ref.get(mapping_name, {})
            if not isinstance(mapping, dict):
                continue
            for char_name, actor_id in list(mapping.items()):
                if actor_id == old_actor_id:
                    mapping[char_name] = new_actor_id

        episode_maps = self.data_ref.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for episode_map in episode_maps.values():
                if not isinstance(episode_map, dict):
                    continue
                for char_name, actor_id in list(episode_map.items()):
                    if actor_id == old_actor_id:
                        episode_map[char_name] = new_actor_id

        export_config = self.data_ref.get("export_config", {})
        if (
            isinstance(export_config, dict) and
            isinstance(export_config.get("highlight_ids_export"), list)
        ):
            export_config["highlight_ids_export"] = (
                self.replace_actor_ids_in_list(
                    export_config.get("highlight_ids_export"),
                    old_actor_id,
                    new_actor_id
                )
            )

    def replace_actor_ids_in_list(
        self,
        values: Any,
        old_actor_id: str,
        new_actor_id: str
    ) -> Any:
        """Replace an actor id in a list while preserving order."""
        if not isinstance(values, list):
            return values

        result = []
        for value in values:
            next_value = new_actor_id if value == old_actor_id else value
            if next_value not in result:
                result.append(next_value)
        return result
