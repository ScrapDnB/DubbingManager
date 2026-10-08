"""Validation for the persisted Dubbing Manager project format."""

from __future__ import annotations

from typing import Any, Dict

from packaging.version import InvalidVersion, Version

from config.constants import PROJECT_VERSION
from services.audiobook_document_service import (
    AUDIOBOOK_DOCUMENT_VERSION,
    BLOCK_TAGS,
)
from services.dynamic_script_storage import (
    DYNAMIC_SCRIPT_MODEL,
    DYNAMIC_SCRIPT_SCHEMA_REVISION,
    SOURCE_LINE_MODES,
    is_dynamic_script_project,
)


class ProjectSchemaError(ValueError):
    """Raised when persisted project data does not match the current schema."""


class ProjectSchemaService:
    """Validate project versions and the current on-disk structure."""

    def validate_supported_version(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ProjectSchemaError("Корень файла проекта должен быть объектом.")
        metadata = data.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ProjectSchemaError("Поле metadata должно быть объектом.")

        raw_version = (metadata or {}).get("format_version")
        if raw_version not in (None, ""):
            try:
                found = Version(str(raw_version))
                supported = Version(PROJECT_VERSION)
            except InvalidVersion as exc:
                raise ProjectSchemaError(
                    f"Некорректная версия формата проекта: {raw_version}."
                ) from exc
            if found > supported:
                raise ProjectSchemaError(
                    "Проект создан в более новой версии Dubbing Manager "
                    f"(формат {found}; поддерживается до {supported})."
                )

        if self._has_legacy_audiobook_data(data):
            raise ProjectSchemaError(
                "Этот файл использует предварительный формат аудиокниги. "
                "Проектов этого формата не выпускалось; импортируйте PDF заново."
            )

    def validate_current(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ProjectSchemaError("Корень файла проекта должен быть объектом.")
        self._require_type(data, "metadata", dict)
        self._require_type(data, "project_name", str)
        self._require_type(data, "project_kind", str)
        self._require_type(data, "actors", dict)
        self._require_type(data, "global_map", dict)
        self._require_type(data, "character_aliases", dict)
        self._require_type(data, "episode_actor_map", dict)
        self._require_type(data, "episodes", dict)
        self._require_type(data, "video_paths", dict)
        self._require_type(data, "project_settings", dict)
        kind = data["project_kind"]
        dynamic_scripts = is_dynamic_script_project(data)
        if dynamic_scripts:
            self._require_type(data, "script_storage", dict)
            self._validate_dynamic_scripts(data["script_storage"])
            if kind == "subtitle" and set(
                data["script_storage"].get("episodes", {})
            ) - set(data["episodes"]):
                raise ProjectSchemaError(
                    "script_storage содержит текст неизвестной серии."
                )
        else:
            self._require_type(data, "episode_texts", dict)
            self._require_type(data, "episode_working_texts", dict)
        self._require_type(data, "audiobook_document", dict)

        if kind not in {"subtitle", "audiobook"}:
            raise ProjectSchemaError(
                "project_kind должен быть subtitle или audiobook."
            )
        if not data["project_name"].strip():
            raise ProjectSchemaError("Название проекта не должно быть пустым.")

        metadata = data["metadata"]
        if str(metadata.get("format_version", "")) != PROJECT_VERSION:
            raise ProjectSchemaError(
                f"Проект не обновлён до формата {PROJECT_VERSION}."
            )
        for key in ("created_at", "modified_at", "app_version"):
            if not isinstance(metadata.get(key), str):
                raise ProjectSchemaError(f"metadata.{key} должно быть строкой.")

        self._validate_string_mapping(data["episodes"], "episodes")
        self._validate_project_settings(data["project_settings"])
        self._validate_actors(data["actors"])
        self._validate_character_aliases(data["character_aliases"])
        if kind == "audiobook":
            self._validate_audiobook(data)

    def _validate_audiobook(self, data: Dict[str, Any]) -> None:
        document = data["audiobook_document"]
        if document.get("format_version") != AUDIOBOOK_DOCUMENT_VERSION:
            raise ProjectSchemaError(
                "Неподдерживаемая версия audiobook_document: "
                f"{document.get('format_version')!r}."
            )
        self._require_type(document, "source", dict, "audiobook_document")
        self._require_type(document, "chapters", list, "audiobook_document")
        source = document["source"]
        if not isinstance(source.get("path", ""), str):
            raise ProjectSchemaError(
                "audiobook_document.source.path должно быть строкой."
            )

        titles = []
        run_ids = set()
        for chapter_index, chapter in enumerate(document["chapters"]):
            path = f"audiobook_document.chapters[{chapter_index}]"
            if not isinstance(chapter, dict):
                raise ProjectSchemaError(f"{path} должно быть объектом.")
            title = chapter.get("title")
            if not isinstance(title, str) or not title.strip():
                raise ProjectSchemaError(f"{path}.title должно быть непустой строкой.")
            titles.append(title)
            blocks = chapter.get("blocks")
            if not isinstance(blocks, list):
                raise ProjectSchemaError(f"{path}.blocks должно быть списком.")
            for block_index, block in enumerate(blocks):
                self._validate_block(block, path, block_index, run_ids)

        if len(titles) != len(set(titles)):
            raise ProjectSchemaError("Названия глав аудиокниги должны быть уникальны.")
        if set(data["episodes"]) != set(titles):
            raise ProjectSchemaError(
                "Список глав в episodes не совпадает с audiobook_document."
            )
        if data.get("episode_working_texts") or data.get("episode_texts"):
            raise ProjectSchemaError(
                "Аудиокнига не должна содержать дублирующие рабочие тексты."
            )

    def _validate_dynamic_scripts(self, storage: Dict[str, Any]) -> None:
        if storage.get("model") != DYNAMIC_SCRIPT_MODEL:
            raise ProjectSchemaError("Неизвестная модель script_storage.")
        if storage.get("schema_revision") != DYNAMIC_SCRIPT_SCHEMA_REVISION:
            raise ProjectSchemaError(
                "Неподдерживаемая ревизия script_storage: "
                f"{storage.get('schema_revision')!r}."
            )
        self._require_type(storage, "episodes", dict, "script_storage")
        for episode, payload in storage["episodes"].items():
            path = f"script_storage.episodes[{episode!r}]"
            if not isinstance(payload, dict):
                raise ProjectSchemaError(f"{path} должно быть объектом.")
            source_lines = payload.get("source_lines")
            edit_blocks = payload.get("edit_blocks")
            if not isinstance(payload.get("source"), dict):
                raise ProjectSchemaError(f"{path}.source должно быть объектом.")
            line_mode = payload["source"].get("line_mode")
            if line_mode is not None and line_mode not in SOURCE_LINE_MODES:
                raise ProjectSchemaError(
                    f"{path}.source.line_mode содержит неизвестное значение."
                )
            if not isinstance(source_lines, list):
                raise ProjectSchemaError(f"{path}.source_lines должно быть списком.")
            if not isinstance(edit_blocks, list):
                raise ProjectSchemaError(f"{path}.edit_blocks должно быть списком.")
            source_ids: set[str] = set()
            source_order: list[str] = []
            for index, line in enumerate(source_lines):
                line_path = f"{path}.source_lines[{index}]"
                if not isinstance(line, dict):
                    raise ProjectSchemaError(f"{line_path} должно быть объектом.")
                source_id = line.get("id")
                if not isinstance(source_id, str) or not source_id:
                    raise ProjectSchemaError(f"{line_path}.id должно быть строкой.")
                if source_id in source_ids:
                    raise ProjectSchemaError(f"Повторяющийся source id: {source_id}.")
                source_ids.add(source_id)
                source_order.append(source_id)
                for key in ("text", "character"):
                    if not isinstance(line.get(key), str):
                        raise ProjectSchemaError(
                            f"{line_path}.{key} должно быть строкой."
                        )
            covered_ids: set[str] = set()
            fragment_ids: set[str] = set()
            source_positions = {
                source_id: position
                for position, source_id in enumerate(source_order)
            }
            for index, block in enumerate(edit_blocks):
                block_path = f"{path}.edit_blocks[{index}]"
                if not isinstance(block, dict):
                    raise ProjectSchemaError(f"{block_path} должно быть объектом.")
                block_sources = block.get("source_ids")
                fragments = block.get("fragments")
                if not isinstance(block_sources, list) or not block_sources:
                    raise ProjectSchemaError(
                        f"{block_path}.source_ids должен быть непустым списком."
                    )
                if not isinstance(fragments, list) or not fragments:
                    raise ProjectSchemaError(
                        f"{block_path}.fragments должен быть непустым списком."
                    )
                for source_id in block_sources:
                    if source_id not in source_ids:
                        raise ProjectSchemaError(
                            f"{block_path} ссылается на неизвестный source id."
                        )
                    if source_id in covered_ids:
                        raise ProjectSchemaError(
                            f"Source id {source_id} изменён несколькими блоками."
                        )
                    covered_ids.add(source_id)
                positions = [source_positions[source_id] for source_id in block_sources]
                if positions != list(range(positions[0], positions[0] + len(positions))):
                    raise ProjectSchemaError(
                        f"{block_path}.source_ids должны быть соседними строками."
                    )
                for fragment in fragments:
                    if not isinstance(fragment, dict):
                        raise ProjectSchemaError(
                            f"{block_path}.fragments содержит не объект."
                        )
                    fragment_id = fragment.get("id")
                    if not isinstance(fragment_id, str) or not fragment_id:
                        raise ProjectSchemaError(
                            f"{block_path} содержит fragment без id."
                        )
                    if fragment_id in fragment_ids:
                        raise ProjectSchemaError(
                            f"Повторяющийся fragment id: {fragment_id}."
                        )
                    fragment_ids.add(fragment_id)

    @staticmethod
    def _validate_project_settings(settings: Dict[str, Any]) -> None:
        try:
            fps = float(settings.get("fps"))
        except (TypeError, ValueError) as exc:
            raise ProjectSchemaError(
                "project_settings.fps должно быть числом."
            ) from exc
        if not 1.0 <= fps <= 120.0:
            raise ProjectSchemaError(
                "project_settings.fps должно быть в диапазоне 1–120."
            )
        if not isinstance(settings.get("fps_source"), str):
            raise ProjectSchemaError(
                "project_settings.fps_source должно быть строкой."
            )

    def _validate_block(
        self,
        block: Any,
        chapter_path: str,
        block_index: int,
        run_ids: set[str],
    ) -> None:
        path = f"{chapter_path}.blocks[{block_index}]"
        if not isinstance(block, dict):
            raise ProjectSchemaError(f"{path} должно быть объектом.")
        if block.get("type") not in BLOCK_TAGS:
            raise ProjectSchemaError(f"{path}.type содержит неизвестный тип блока.")
        runs = block.get("runs")
        if not isinstance(runs, list):
            raise ProjectSchemaError(f"{path}.runs должно быть списком.")
        for run_index, run in enumerate(runs):
            run_path = f"{path}.runs[{run_index}]"
            if not isinstance(run, dict):
                raise ProjectSchemaError(f"{run_path} должно быть объектом.")
            run_id = run.get("id")
            if not isinstance(run_id, str) or not run_id:
                raise ProjectSchemaError(f"{run_path}.id должно быть непустой строкой.")
            if run_id in run_ids:
                raise ProjectSchemaError(f"Повторяющийся id фрагмента: {run_id}.")
            run_ids.add(run_id)
            if not isinstance(run.get("text"), str):
                raise ProjectSchemaError(f"{run_path}.text должно быть строкой.")
            character = run.get("character")
            if not isinstance(character, str) or not character:
                raise ProjectSchemaError(
                    f"{run_path}.character должно быть непустой строкой."
                )
            if "actor_id" in run and not isinstance(run["actor_id"], str):
                raise ProjectSchemaError(f"{run_path}.actor_id должно быть строкой.")

    @staticmethod
    def _validate_character_aliases(aliases: Dict[str, Any]) -> None:
        for character, values in aliases.items():
            if not isinstance(character, str) or not character.strip():
                raise ProjectSchemaError(
                    "character_aliases содержит некорректное имя персонажа."
                )
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip()
                for value in values
            ):
                raise ProjectSchemaError(
                    f"character_aliases.{character} должно быть списком непустых строк."
                )
            folded = [value.strip().casefold() for value in values]
            if len(folded) != len(set(folded)):
                raise ProjectSchemaError(
                    f"character_aliases.{character} содержит повторяющиеся алиасы."
                )

    @staticmethod
    def _require_type(
        mapping: Dict[str, Any],
        key: str,
        expected: type,
        prefix: str = "project",
    ) -> None:
        if key not in mapping:
            raise ProjectSchemaError(f"Отсутствует обязательное поле {prefix}.{key}.")
        if not isinstance(mapping[key], expected):
            raise ProjectSchemaError(
                f"{prefix}.{key} должно иметь тип {expected.__name__}."
            )

    @staticmethod
    def _validate_string_mapping(mapping: Dict[str, Any], path: str) -> None:
        for key, value in mapping.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ProjectSchemaError(
                    f"{path} должно содержать только строковые ключи и значения."
                )

    @staticmethod
    def _validate_actors(actors: Dict[str, Any]) -> None:
        for actor_id, actor in actors.items():
            if not isinstance(actor_id, str) or not isinstance(actor, dict):
                raise ProjectSchemaError("actors содержит некорректную запись.")
            if not isinstance(actor.get("name", ""), str):
                raise ProjectSchemaError(f"actors.{actor_id}.name должно быть строкой.")

    @staticmethod
    def _has_legacy_audiobook_data(data: Dict[str, Any]) -> bool:
        if data.get("project_kind") == "audiobook" and not data.get(
            "audiobook_document"
        ):
            return True
        return any(data.get(key) for key in (
            "book_chapters", "audiobook_source", "audiobook_chapter_order"
        ))
