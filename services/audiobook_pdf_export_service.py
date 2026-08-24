"""Book-layout PDF export for marked audiobook documents."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Dict, Iterable

from lxml import etree
from lxml import html as lxml_html

from services.audiobook_document_service import AudiobookDocumentService
from services.pdf_export_service import PdfExportService


class AudiobookPdfExportService:
    """Render selected audiobook chapters as one or several PDF files."""

    def __init__(self, renderer: PdfExportService | None = None) -> None:
        self._renderer = renderer or PdfExportService()
        self._documents = AudiobookDocumentService()

    def export_combined(
        self,
        document: Dict[str, Any],
        project_data: Dict[str, Any],
        chapter_titles: Iterable[str],
        save_path: str,
        studio_layout: bool = False,
    ) -> Path:
        titles = self._selected_titles(document, chapter_titles)
        if not titles:
            raise ValueError("Не выбраны главы для экспорта")
        path = Path(save_path)
        if path.suffix.lower() != ".pdf":
            path = path.with_suffix(".pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        output = self.build_html(
            document, project_data, titles, studio_layout=studio_layout
        )
        self._renderer.render_html_to_pdf(output, str(path))
        return path

    def export_separate(
        self,
        document: Dict[str, Any],
        project_data: Dict[str, Any],
        chapter_titles: Iterable[str],
        folder: str,
        studio_layout: bool = False,
    ) -> list[Path]:
        titles = self._selected_titles(document, chapter_titles)
        if not titles:
            raise ValueError("Не выбраны главы для экспорта")
        output_folder = Path(folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        used: set[str] = set()
        paths: list[Path] = []
        for index, title in enumerate(titles, 1):
            stem = self.safe_filename(title) or f"Глава {index}"
            candidate = stem
            suffix = 2
            while candidate.casefold() in used:
                candidate = f"{stem} ({suffix})"
                suffix += 1
            used.add(candidate.casefold())
            path = output_folder / f"{candidate}.pdf"
            output = self.build_html(
                document, project_data, [title], studio_layout=studio_layout
            )
            self._renderer.render_html_to_pdf(output, str(path))
            paths.append(path)
        return paths

    def build_html(
        self,
        document: Dict[str, Any],
        project_data: Dict[str, Any],
        chapter_titles: Iterable[str],
        studio_layout: bool = False,
    ) -> str:
        titles = self._selected_titles(document, chapter_titles)
        actor_colors = {
            str(actor_id): str(actor.get("color") or "#f1d77a")
            for actor_id, actor in project_data.get("actors", {}).items()
            if isinstance(actor, dict)
        }
        chapter_parts = []
        used_characters: set[str] = set()
        for chapter_index, title in enumerate(titles):
            chapter = self._documents.chapter(document, title)
            if not chapter:
                continue
            chapter_html = self._documents.chapter_to_html(
                chapter, actor_colors
            )
            parsed = lxml_html.document_fromstring(chapter_html)
            body = parsed.find("body")
            if body is None:
                continue
            if chapter_index:
                headings = body.xpath(".//h1")
                target = headings[0] if headings else next(iter(body), None)
                if target is not None:
                    target.text = (
                        PdfExportService.PAGE_BREAK_MARKER + (target.text or "")
                    )
            for span in body.xpath('.//span[@data-dm-character]'):
                character = str(span.attrib.get("data-dm-character", ""))
                if not character:
                    continue
                used_characters.add(character)
                if studio_layout:
                    label = lxml_html.Element("span", {"class": "dm-role"})
                    label.text = f"{character}: "
                    label.tail = span.text
                    span.text = None
                    span.insert(0, label)
            fragment = (body.text or "") + "".join(
                etree.tostring(child, encoding="unicode", method="html")
                for child in body
            )
            chapter_parts.append(
                '<section class="chapter">' + fragment + "</section>"
            )

        legend = self._legend_html(
            used_characters, project_data, actor_colors
        )
        project_name = html.escape(str(
            project_data.get("project_name") or "Аудиокнига"
        ))
        layout_class = "studio" if studio_layout else "reader"
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:16mm 15mm 18mm; }}
body {{ color:#1d1d1d; font-family:Georgia, 'Times New Roman', serif;
  font-size:{'12pt' if studio_layout else '11pt'}; line-height:1.48; }}
.book-title {{ font-size:20pt; font-weight:600; margin:0 0 8mm; }}
.legend {{ margin:0 0 9mm; padding:4mm; border:1px solid #c9c9c9; }}
.legend-title {{ font-family:Arial,sans-serif; font-weight:600; margin-bottom:2mm; }}
.legend-item {{ margin:1.2mm 0; }} .swatch {{ padding:0 2mm; }}
.chapter {{ page-break-before:always; }}
.chapter:first-of-type {{ page-break-before:auto; }}
h1 {{ font-size:19pt; margin:0 0 8mm; }} h2 {{ font-size:16pt; }}
p {{ margin:0 0 4mm; text-indent:{'0' if studio_layout else '7mm'}; }}
span[data-dm-character] {{ padding:0 1mm; }}
.dm-role {{ background:transparent; font-family:Arial,sans-serif;
  font-size:9pt; font-weight:700; color:#333; }}
.studio p {{ text-indent:0; margin-bottom:5mm; }}
</style></head><body class="{layout_class}">
<div class="book-title">{project_name}</div>{legend}
{''.join(chapter_parts)}</body></html>"""

    def _legend_html(
        self,
        characters: set[str],
        project_data: Dict[str, Any],
        actor_colors: Dict[str, str],
    ) -> str:
        if not characters:
            return ""
        actors = project_data.get("actors", {})
        assignments = project_data.get("global_map", {})
        aliases = project_data.get("character_aliases", {})
        items = []
        for character in sorted(characters, key=str.casefold):
            value = assignments.get(character)
            actor_ids = value if isinstance(value, list) else [value]
            actor_ids = [str(item) for item in actor_ids if item]
            actor_names = [
                str(actors.get(actor_id, {}).get("name") or actor_id)
                for actor_id in actor_ids
            ]
            color = actor_colors.get(actor_ids[0], "#fff2a8") if actor_ids else "#fff2a8"
            alias_values = aliases.get(character, [])
            alias_text = (
                f" — алиасы: {html.escape(', '.join(alias_values))}"
                if isinstance(alias_values, list) and alias_values else ""
            )
            actor_text = (
                f" — {html.escape(' / '.join(actor_names))}"
                if actor_names else " — актёр не назначен"
            )
            items.append(
                '<div class="legend-item"><span class="swatch" '
                f'style="background-color:{html.escape(color)}">'
                f"{html.escape(character)}</span>{actor_text}{alias_text}</div>"
            )
        return (
            '<div class="legend"><div class="legend-title">Роли и актёры</div>'
            + "".join(items) + "</div>"
        )

    def _selected_titles(
        self, document: Dict[str, Any], requested: Iterable[str]
    ) -> list[str]:
        selected = {str(value) for value in requested}
        return [
            title for title in self._documents.chapter_titles(document)
            if title in selected
        ]

    @staticmethod
    def safe_filename(value: str) -> str:
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value))
        return value.strip(" .")[:120]
