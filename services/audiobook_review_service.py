"""Deterministic search and review queue for audiobook markup."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable

from services.assignment_service import get_actor_ids_for_character
from services.audiobook_document_service import DEFAULT_NARRATOR


REVIEW_ALL = "all"
REVIEW_ISSUES = "issues"
REVIEW_UNMARKED_DIALOGUE = "unmarked_dialogue"
REVIEW_UNASSIGNED = "unassigned"
REVIEW_IGNORED = "ignored"

_DIALOGUE_RE = re.compile(r"^\s*[—–]\s*\S", re.UNICODE)


class AudiobookReviewService:
    """Build searchable rows and deterministic markup warnings."""

    def rows(
        self,
        document: Dict[str, Any],
        project_data: Dict[str, Any],
        ignored_ids: Iterable[str] = (),
    ) -> list[Dict[str, Any]]:
        ignored = {str(value) for value in ignored_ids}
        aliases = project_data.get("character_aliases", {})
        result: list[Dict[str, Any]] = []
        for chapter in document.get("chapters", []):
            chapter_title = str(chapter.get("title", ""))
            for block_index, block in enumerate(chapter.get("blocks", [])):
                block_type = str(block.get("type", "p"))
                for run_index, run in enumerate(block.get("runs", [])):
                    text = " ".join(str(run.get("text", "")).split())
                    if not text or block_type in {"h1", "h2", "h3"}:
                        continue
                    character = str(
                        run.get("character") or DEFAULT_NARRATOR
                    )
                    actor_ids = get_actor_ids_for_character(
                        project_data, character, chapter_title
                    )
                    has_actor = bool(run.get("actor_id") or actor_ids)
                    kind = "ok"
                    label = "Размечено"
                    if character == DEFAULT_NARRATOR and self.looks_like_dialogue(text):
                        kind = REVIEW_UNMARKED_DIALOGUE
                        label = "Прямая речь без роли"
                    elif character != DEFAULT_NARRATOR and not has_actor:
                        kind = REVIEW_UNASSIGNED
                        label = "Роль без актёра"
                    elif character == DEFAULT_NARRATOR:
                        label = "Авторский текст"

                    item_id = self.item_id(
                        chapter_title,
                        kind,
                        text,
                        f"{block_index}:{run_index}",
                    )
                    character_aliases = aliases.get(character, [])
                    if not isinstance(character_aliases, list):
                        character_aliases = []
                    result.append({
                        "itemId": item_id,
                        "chapter": chapter_title,
                        "character": character,
                        "aliases": ", ".join(
                            str(value) for value in character_aliases
                        ),
                        "text": text,
                        "kind": kind,
                        "kindLabel": label,
                        "issue": kind != "ok",
                        "ignored": item_id in ignored,
                        "runId": str(
                            run.get("id") or f"{block_index}:{run_index}"
                        ),
                    })
        return result

    def filtered_rows(
        self,
        rows: Iterable[Dict[str, Any]],
        filter_name: str = REVIEW_ISSUES,
        search: str = "",
    ) -> list[Dict[str, Any]]:
        query = " ".join(str(search or "").split()).casefold()
        result = []
        for row in rows:
            kind = str(row.get("kind", "ok"))
            ignored = bool(row.get("ignored"))
            if filter_name == REVIEW_ISSUES and (
                kind == "ok" or ignored
            ):
                continue
            if filter_name == REVIEW_IGNORED and not ignored:
                continue
            if filter_name in {
                REVIEW_UNMARKED_DIALOGUE, REVIEW_UNASSIGNED
            } and (kind != filter_name or ignored):
                continue
            if query:
                haystack = " ".join((
                    str(row.get("chapter", "")),
                    str(row.get("character", "")),
                    str(row.get("aliases", "")),
                    str(row.get("text", "")),
                    str(row.get("kindLabel", "")),
                )).casefold()
                if query not in haystack:
                    continue
            result.append(dict(row))
        return result

    @staticmethod
    def looks_like_dialogue(text: str) -> bool:
        return bool(_DIALOGUE_RE.match(str(text or "")))

    @staticmethod
    def item_id(
        chapter: str, kind: str, text: str, location: str = ""
    ) -> str:
        normalized = "\0".join((
            str(chapter).strip().casefold(),
            str(kind).strip(),
            " ".join(str(text).split()).casefold(),
            str(location),
        ))
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()
