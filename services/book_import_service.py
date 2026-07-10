"""Services for importing and storing audiobook book chapters."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.constants import DEFAULT_AUDIOBOOK_CONFIG


try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PdfReader = None
    PYPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False


BOOK_TEXT_FORMAT_VERSION = "1.0"
NAMED_CHAPTER_TITLES = {
    "вступление",
    "введение",
    "пролог",
    "эпилог",
    "предисловие",
    "послесловие",
    "introduction",
    "prologue",
    "epilogue",
    "foreword",
    "afterword",
}
SKIPPED_SECTION_TITLES = {
    "оглавление",
    "содержание",
    "contents",
    "table of contents",
}


@dataclass
class BookChapter:
    """A chapter extracted from a book source."""

    title: str
    paragraphs: List[str] = field(default_factory=list)
    start_page: Optional[int] = None
    end_page: Optional[int] = None

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs).strip()


class BookImportError(Exception):
    """Raised when a book cannot be imported."""


class BookImportService:
    """Import PDF books and convert manual markup to project episodes."""

    def __init__(self, chapter_keywords: Optional[List[str]] = None) -> None:
        source_keywords = (
            DEFAULT_AUDIOBOOK_CONFIG["chapter_keywords"]
            if chapter_keywords is None
            else chapter_keywords
        )
        self.chapter_keywords = self._normalize_chapter_keywords(
            source_keywords
        )
        self.chapter_re = self._build_chapter_regex(self.chapter_keywords)

    def _normalize_chapter_keywords(self, keywords: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for keyword in keywords:
            normalized = " ".join(str(keyword).split())
            folded = normalized.casefold()
            if normalized and folded not in seen:
                seen.add(folded)
                result.append(normalized)
        return result

    def _build_chapter_regex(self, keywords: List[str]) -> re.Pattern[str]:
        if not keywords:
            return re.compile(r"(?!x)x")
        alternatives = "|".join(
            re.escape(keyword) for keyword in keywords
        )
        return re.compile(
            rf"^\s*(?:{alternatives})"
            r"(?:\s+([0-9ivxlcdm]+|[а-яёa-z-]+)(?:[\s.:,-].*)?)?\s*$",
            re.IGNORECASE,
        )

    def import_pdf(
        self,
        path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[BookChapter]:
        """Extract text from a PDF and split it into chapters."""
        if not PYPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise BookImportError(
                "Для импорта PDF нужен пакет pypdf или pdfplumber. "
                "Установите зависимости проекта."
            )

        if not os.path.exists(path):
            raise BookImportError(f"PDF файл не найден: {path}")

        page_texts = self._extract_pdf_pages(path, progress_callback)

        if not any(item["text"].strip() for item in page_texts):
            raise BookImportError(
                "Не удалось извлечь текст из PDF. Возможно, это скан без OCR."
            )

        return self.split_texts_into_chapters(page_texts)

    def _extract_pdf_pages(
        self,
        path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract page text with the best available PDF backend."""
        if PYPDF_AVAILABLE:
            try:
                reader = PdfReader(path)
            except Exception as exc:
                raise BookImportError(f"Не удалось открыть PDF: {exc}") from exc

            page_texts: List[Dict[str, Any]] = []
            total_pages = len(reader.pages)
            for page_index, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                page_texts.append({"page": page_index, "text": text})
                if progress_callback:
                    progress_callback(page_index, total_pages)
            return page_texts

        try:
            page_texts = []
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                for page_index, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text() or ""
                    except Exception:
                        text = ""
                    page_texts.append({"page": page_index, "text": text})
                    if progress_callback:
                        progress_callback(page_index, total_pages)
            return page_texts
        except Exception as exc:
            raise BookImportError(f"Не удалось открыть PDF: {exc}") from exc

    def split_texts_into_chapters(
        self,
        page_texts: List[Dict[str, Any]]
    ) -> List[BookChapter]:
        """Split extracted page texts into chapters using simple headings."""
        chapters: List[BookChapter] = []
        current: Optional[BookChapter] = None
        skipping_section = False

        for page_info in page_texts:
            page_num = page_info.get("page")
            paragraphs = self._paragraphs_from_text(page_info.get("text", ""))
            if (
                current
                and current.paragraphs
                and paragraphs
                and self._continues_previous_page(paragraphs[0])
            ):
                previous = current.paragraphs[-1]
                separator = ""
                if previous.endswith("-") and not previous.endswith(" -"):
                    previous = previous[:-1]
                else:
                    separator = " "
                current.paragraphs[-1] = previous + separator + paragraphs.pop(0)

            for paragraph in paragraphs:
                if self._looks_like_skipped_section_heading(paragraph):
                    if current and current.paragraphs:
                        current.end_page = page_num
                        chapters.append(current)
                    current = None
                    skipping_section = True
                    continue

                if self._looks_like_chapter_heading(paragraph):
                    if skipping_section and self._looks_like_toc_entry(paragraph):
                        continue
                    skipping_section = False
                    if current and current.paragraphs:
                        current.end_page = page_num
                        chapters.append(current)
                    current = BookChapter(
                        title=paragraph.strip(),
                        paragraphs=[],
                        start_page=page_num,
                        end_page=page_num,
                    )
                    continue

                if skipping_section:
                    continue

                if current is None:
                    current = BookChapter(
                        title="Глава 1",
                        paragraphs=[],
                        start_page=page_num,
                        end_page=page_num,
                    )
                current.paragraphs.append(paragraph)
                current.end_page = page_num

        if current and current.paragraphs:
            chapters.append(current)

        if not chapters:
            full_text = "\n\n".join(
                item.get("text", "").strip() for item in page_texts
            ).strip()
            if full_text:
                chapters.append(BookChapter("Глава 1", [full_text]))

        return chapters

    def chapter_to_html(self, chapter: BookChapter) -> str:
        """Return a simple book-like HTML document for a chapter."""
        parts = [
            "<!DOCTYPE HTML><html><head><meta charset=\"utf-8\"></head><body>",
            (
                "<h1 style=\"font-size:22pt; font-weight:600; "
                "margin-top:0; margin-bottom:18px;\">"
                f"{html.escape(chapter.title)}</h1>"
            ),
        ]
        for paragraph in chapter.paragraphs:
            escaped = html.escape(paragraph).replace("\n", "<br />")
            parts.append(
                "<p style=\"line-height:1.45; margin-top:0; "
                "margin-bottom:12px; text-indent:24px;\">"
                f"{escaped}</p>"
            )
        parts.append("</body></html>")
        return "".join(parts)

    def chapters_to_html(self, chapters: List[BookChapter]) -> str:
        """Return one book-like HTML document containing all imported chapters."""
        parts = [
            "<!DOCTYPE HTML><html><head><meta charset=\"utf-8\"></head><body>",
        ]
        for chapter in chapters:
            parts.append(
                "<h1 style=\"font-size:22pt; font-weight:600; "
                "margin-top:0; margin-bottom:18px;\">"
                f"{html.escape(chapter.title)}</h1>"
            )
            for paragraph in chapter.paragraphs:
                escaped = html.escape(paragraph).replace("\n", "<br />")
                parts.append(
                    "<p style=\"line-height:1.45; margin-top:0; "
                    "margin-bottom:12px; text-indent:24px;\">"
                    f"{escaped}</p>"
                )
        parts.append("</body></html>")
        return "".join(parts)

    def save_chapter_text(
        self,
        project_data: Dict[str, Any],
        episode: str,
        source_path: str,
        html_text: str,
        lines: List[Dict[str, Any]]
    ) -> None:
        """Store a marked chapter in project data and working-text payloads."""
        book_chapters = project_data.setdefault("book_chapters", {})
        book_chapters[str(episode)] = {
            "format_version": BOOK_TEXT_FORMAT_VERSION,
            "source": {
                "type": "pdf",
                "path": source_path,
                "imported_at": datetime.now().isoformat(),
                "mtime": (
                    Path(source_path).stat().st_mtime
                    if source_path and Path(source_path).exists()
                    else None
                ),
            },
            "html": html_text,
        }

        project_data.setdefault("loaded_episodes", {})[str(episode)] = lines

    def build_lines_from_segments(
        self,
        segments: List[Dict[str, Any]],
        narrator_name: str = "Автор"
    ) -> List[Dict[str, Any]]:
        """Convert marked text segments to regular project lines."""
        lines: List[Dict[str, Any]] = []
        current_time = 0.0

        for idx, segment in enumerate(segments):
            text = " ".join(segment.get("text", "").split())
            if not text:
                continue
            char = segment.get("character") or narrator_name
            duration = max(1.0, len(text.split()) * 0.45)
            lines.append({
                "id": len(lines),
                "s": current_time,
                "e": current_time + duration,
                "char": char,
                "text": text,
                "s_raw": "",
                "source_ids": [idx],
                "source_texts": [text],
                "_book_text": True,
            })
            current_time += duration

        return lines

    def _paragraphs_from_text(self, text: str) -> List[str]:
        normalized = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\xa0", " ")
        )
        raw_lines = normalized.split("\n")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_lines]
        lines = self._remove_page_header(lines)

        paragraphs: List[str] = []
        current = ""
        force_new_paragraph = False

        for line in lines:
            if not line:
                if current:
                    paragraphs.append(current)
                    current = ""
                force_new_paragraph = True
                continue

            if self._looks_like_chapter_heading(line):
                if current:
                    paragraphs.append(current)
                    current = ""
                paragraphs.append(line)
                force_new_paragraph = True
                continue

            if self._looks_like_skipped_section_heading(line):
                if current:
                    paragraphs.append(current)
                    current = ""
                paragraphs.append(line)
                force_new_paragraph = True
                continue

            if line.isupper() and len(line) <= 40:
                if current:
                    paragraphs.append(current)
                    current = ""
                paragraphs.append(line)
                force_new_paragraph = True
                continue

            starts_dialogue = bool(re.match(r"^[—–]\s*", line))
            sentence_finished = bool(
                current and re.search(r"[.!?…»)]$", current)
            )
            if current and (
                force_new_paragraph or starts_dialogue or sentence_finished
            ):
                paragraphs.append(current)
                current = ""

            if not current:
                current = line
            elif current.endswith("-") and not current.endswith(" -"):
                current = current[:-1] + line
            else:
                current += " " + line
            force_new_paragraph = False

        if current:
            paragraphs.append(current)
        return paragraphs

    def _remove_page_header(self, lines: List[str]) -> List[str]:
        """Remove common page numbers and short running headers."""
        result = list(lines)
        while result and not result[0]:
            result.pop(0)

        if result and re.fullmatch(r"\d{1,4}", result[0]):
            result.pop(0)

        while result and not result[0]:
            result.pop(0)

        if result and self._looks_like_running_header(result[0]):
            result.pop(0)
        return result

    def _looks_like_running_header(self, text: str) -> bool:
        candidate = " ".join(text.split())
        if (
            not candidate
            or self._looks_like_chapter_heading(candidate)
            or len(candidate) > 60
            or len(candidate.split()) > 6
        ):
            return False
        if re.search(r"[.!?…,:;—–-]$", candidate):
            return False
        return candidate.isupper() or bool(
            re.fullmatch(
                r"[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+){1,3}",
                candidate,
            )
        )

    def _continues_previous_page(self, text: str) -> bool:
        candidate = text.lstrip()
        return bool(candidate and candidate[0].islower())

    def _looks_like_chapter_heading(self, text: str) -> bool:
        candidate = " ".join(text.strip().split())
        if not candidate or len(candidate) > 80:
            return False
        return (
            bool(self.chapter_re.match(candidate))
            or self._normalized_heading(candidate) in NAMED_CHAPTER_TITLES
        )

    def _looks_like_skipped_section_heading(self, text: str) -> bool:
        return self._normalized_heading(text) in SKIPPED_SECTION_TITLES

    def _looks_like_toc_entry(self, text: str) -> bool:
        candidate = " ".join(text.strip().split())
        if not candidate:
            return False
        return bool(
            re.search(r"(?:\.{2,}|\s)\d{1,4}$", candidate)
        )

    def _normalized_heading(self, text: str) -> str:
        return re.sub(
            r"^[\W_]+|[\W_]+$",
            "",
            " ".join(text.strip().split()).casefold(),
        )
