"""Canonical structured storage for audiobook projects."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from lxml import etree
from lxml import html as lxml_html


AUDIOBOOK_DOCUMENT_VERSION = "1.0"
DEFAULT_NARRATOR = "Автор"
BLOCK_TAGS = {"h1", "h2", "h3", "p", "blockquote", "li", "div"}


class AudiobookDocumentService:
    """Convert audiobook documents between structured, HTML and line views."""

    def create_document(
        self,
        source_path: str,
        chapters: Iterable[tuple[str, str]],
    ) -> Dict[str, Any]:
        path = Path(str(source_path or ""))
        return {
            "format_version": AUDIOBOOK_DOCUMENT_VERSION,
            "source": {
                "type": "pdf",
                "path": str(source_path or ""),
                "imported_at": datetime.now().isoformat(),
                "mtime": path.stat().st_mtime if path.is_file() else None,
            },
            "chapters": [
                self.chapter_from_html(title, html_text)
                for title, html_text in chapters
            ],
        }

    def chapter_from_html(self, title: str, html_text: str) -> Dict[str, Any]:
        try:
            document = lxml_html.document_fromstring(html_text or "<html><body></body></html>")
            body = document.find("body")
            if body is None:
                body = document
        except (etree.ParserError, ValueError):
            body = lxml_html.Element("body")

        blocks = []
        if body.text and body.text.strip():
            blocks.append(self._block_from_text("p", body.text))
        for node in body:
            tag = str(getattr(node, "tag", "p")).lower()
            if tag not in BLOCK_TAGS:
                tag = "p"
            runs = self._runs_from_element(node)
            if runs:
                blocks.append({"type": tag, "runs": runs})
            if node.tail and node.tail.strip():
                blocks.append(self._block_from_text("p", node.tail))
        return {"title": str(title), "blocks": blocks}

    def chapter_to_html(
        self,
        chapter: Dict[str, Any],
        actor_colors: Optional[Dict[str, str]] = None,
    ) -> str:
        parts = ['<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>']
        for block in chapter.get("blocks", []):
            tag = str(block.get("type", "p")).lower()
            if tag not in BLOCK_TAGS:
                tag = "p"
            parts.append(f"<{tag}>")
            for run in block.get("runs", []):
                text = html.escape(str(run.get("text", ""))).replace("\n", "<br>")
                if not text:
                    continue
                attrs = [f'data-dm-run-id="{html.escape(str(run.get("id", "")))}"']
                character = str(run.get("character") or DEFAULT_NARRATOR)
                actor_id = str(run.get("actor_id") or "")
                if character != DEFAULT_NARRATOR:
                    attrs.append(f'data-dm-character="{html.escape(character)}"')
                if actor_id:
                    attrs.append(f'data-dm-actor="{html.escape(actor_id)}"')
                color = (actor_colors or {}).get(actor_id)
                if color or character != DEFAULT_NARRATOR:
                    attrs.append(
                        'style="background-color:'
                        f'{html.escape(str(color or "#fff2a8"))};color:#111"'
                    )
                parts.append(f"<span {' '.join(attrs)}>{text}</span>")
            parts.append(f"</{tag}>")
        parts.append("</body></html>")
        return "".join(parts)

    def combined_html(self, document: Dict[str, Any]) -> str:
        fragments = []
        for chapter in document.get("chapters", []):
            chapter_html = self.chapter_to_html(chapter)
            parsed = lxml_html.document_fromstring(chapter_html)
            body = parsed.find("body")
            if body is not None:
                fragments.extend(
                    etree.tostring(child, encoding="unicode", method="html")
                    for child in body
                )
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
            + "".join(fragments)
            + "</body></html>"
        )

    def chapter_titles(self, document: Dict[str, Any]) -> list[str]:
        return [
            str(chapter.get("title", ""))
            for chapter in document.get("chapters", [])
            if str(chapter.get("title", ""))
        ]

    def chapter(self, document: Dict[str, Any], title: str) -> Optional[Dict[str, Any]]:
        return next((
            chapter for chapter in document.get("chapters", [])
            if str(chapter.get("title", "")) == str(title)
        ), None)

    def lines(self, document: Dict[str, Any], title: str) -> list[Dict[str, Any]]:
        chapter = self.chapter(document, title)
        if not chapter:
            return []
        result = []
        current_time = 0.0
        for block_index, block in enumerate(chapter.get("blocks", [])):
            for run_index, run in enumerate(block.get("runs", [])):
                text = " ".join(str(run.get("text", "")).split())
                if not text:
                    continue
                duration = max(1.0, len(text.split()) * 0.45)
                run_id = str(run.get("id") or f"{block_index}:{run_index}")
                result.append({
                    "id": run_id,
                    "s": current_time,
                    "e": current_time + duration,
                    "char": str(run.get("character") or DEFAULT_NARRATOR),
                    "text": text,
                    "s_raw": "",
                    "source_ids": [run_id],
                    "source_texts": [text],
                    "_book_text": True,
                })
                current_time += duration
        return result

    def episode_payload(
        self,
        document: Dict[str, Any],
        title: str,
    ) -> Optional[Dict[str, Any]]:
        lines = self.lines(document, title)
        if not lines and self.chapter(document, title) is None:
            return None
        characters = sorted({line["char"] for line in lines})
        payload_lines = [{
            "id": line["id"],
            "source_ids": list(line["source_ids"]),
            "start": line["s"],
            "end": line["e"],
            "s_raw": "",
            "character": line["char"],
            "display_character": line["char"],
            "text": line["text"],
            "source_texts": list(line["source_texts"]),
            "dirty": False,
        } for line in lines]
        return {
            "format_version": "audiobook-1.0",
            "episode": str(title),
            "source": dict(document.get("source", {})),
            "source_lines_origin": "audiobook_document",
            "source_lines": [{
                "id": line["id"], "start": line["s"], "end": line["e"],
                "s_raw": "", "character": line["char"], "text": line["text"],
            } for line in lines],
            "merge_config": {"merge": False},
            "characters": {name: {"display_name": name} for name in characters},
            "lines": payload_lines,
        }

    def update_line_text(
        self, document: Dict[str, Any], title: str, line_id: Any, text: str,
    ) -> bool:
        run = self._find_run(document, title, line_id)
        if run is None or str(run.get("text", "")) == str(text):
            return False
        run["text"] = str(text)
        return True

    def update_line_character(
        self, document: Dict[str, Any], title: str, line_id: Any, character: str,
    ) -> bool:
        run = self._find_run(document, title, line_id)
        character = str(character or "").strip()
        if run is None or not character or str(run.get("character") or DEFAULT_NARRATOR) == character:
            return False
        run["character"] = character
        run.pop("actor_id", None)
        return True

    def split_line(
        self,
        document: Dict[str, Any],
        title: str,
        line_id: Any,
        remaining_text: str,
        split_text: str,
        split_character: str,
    ) -> bool:
        location = self._find_run_location(document, title, line_id)
        split_text = str(split_text or "").strip()
        split_character = str(split_character or "").strip()
        if location is None or not split_text or not split_character:
            return False
        runs, index = location
        runs[index]["text"] = str(remaining_text)
        runs.insert(index + 1, {
            "id": self._new_id(),
            "text": split_text,
            "character": split_character,
        })
        return True

    def rename_character(
        self, document: Dict[str, Any], old_name: str, new_name: str,
        title: Optional[str] = None,
    ) -> int:
        changed_chapters = 0
        for chapter in document.get("chapters", []):
            if title is not None and str(chapter.get("title")) != str(title):
                continue
            changed = False
            for block in chapter.get("blocks", []):
                for run in block.get("runs", []):
                    if str(run.get("character") or DEFAULT_NARRATOR) == old_name:
                        run["character"] = new_name
                        changed = True
            changed_chapters += int(changed)
        return changed_chapters

    def _runs_from_element(self, node: Any) -> list[Dict[str, Any]]:
        runs: list[Dict[str, Any]] = []

        def append_text(value: Any, character: str, actor_id: str) -> None:
            text = str(value or "")
            if not text:
                return
            if (
                runs and runs[-1].get("character") == character
                and runs[-1].get("actor_id", "") == actor_id
            ):
                runs[-1]["text"] += text
                return
            run = {"id": self._new_id(), "text": text, "character": character}
            if actor_id:
                run["actor_id"] = actor_id
            runs.append(run)

        def walk(element: Any, character: str, actor_id: str) -> None:
            current_character = str(element.attrib.get("data-dm-character", character))
            current_actor = str(element.attrib.get("data-dm-actor", actor_id))
            append_text(element.text, current_character, current_actor)
            for child in element:
                walk(child, current_character, current_actor)
                append_text(child.tail, current_character, current_actor)

        walk(node, DEFAULT_NARRATOR, "")
        return runs

    def _block_from_text(self, block_type: str, text: str) -> Dict[str, Any]:
        return {
            "type": block_type,
            "runs": [{
                "id": self._new_id(), "text": str(text),
                "character": DEFAULT_NARRATOR,
            }],
        }

    def _find_run(
        self, document: Dict[str, Any], title: str, line_id: Any,
    ) -> Optional[Dict[str, Any]]:
        location = self._find_run_location(document, title, line_id)
        return location[0][location[1]] if location else None

    def _find_run_location(
        self, document: Dict[str, Any], title: str, line_id: Any,
    ) -> Optional[tuple[list[Dict[str, Any]], int]]:
        chapter = self.chapter(document, title)
        if not chapter:
            return None
        target = str(line_id)
        flat_index = 0
        for block in chapter.get("blocks", []):
            runs = block.get("runs", [])
            for index, run in enumerate(runs):
                if str(run.get("id")) == target or str(flat_index) == target:
                    return runs, index
                flat_index += 1
        return None

    @staticmethod
    def _new_id() -> str:
        return uuid4().hex
