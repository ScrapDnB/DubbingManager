"""Service for importing DOCX files with flexible column mapping."""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

try:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-docx not installed. DOCX import disabled.")

from utils.helpers import srt_time_to_seconds

logger = logging.getLogger(__name__)


# Column types
COLUMN_TYPES = {
    'character': 'Имя персонажа',
    'time_start': 'Тайминг (начало)',
    'time_end': 'Тайминг (конец)',
    'time_split': 'Тайминг (вместе)',
    'text': 'Текст фразы'
}

# Default values for column mapping
DEFAULT_COLUMN_MAPPING = {
    'character': 0,
    'time_start': None,
    'time_end': None,
    'time_split': 1,
    'text': 2
}

# Default separators for combined timing columns
DEFAULT_TIME_SEPARATORS = ['-']


class DocxImportService:
    """Docx Import Service implementation."""

    def __init__(self, merge_gap: int = 5, fps: float = 25.0, time_separators: Optional[List[str]] = None):
        self.merge_gap = merge_gap
        self.fps = fps
        self.time_separators = time_separators or DEFAULT_TIME_SEPARATORS

    def set_merge_gap(self, gap: int) -> None:
        """Set the replica merge gap."""
        self.merge_gap = gap

    def set_fps(self, fps: float) -> None:
        """Set the frame rate."""
        self.fps = fps

    def set_time_separators(self, separators: List[str]) -> None:
        """Set time separators."""
        self.time_separators = separators

    def extract_tables_from_docx(self, path: str) -> List[List[List[str]]]:
        """Extract tables from docx."""
        if not DOCX_AVAILABLE:
            logger.error("python-docx not installed")
            return []

        # Reset the header flag
        self._has_header = False

        try:
            doc = Document(path)
            all_tables = []

            # Extract all tables
            if doc.tables:
                for table in doc.tables:
                    rows = []
                    for row in table.rows:
                        cells = [cell.text.strip() for cell in row.cells]
                        if any(cells):  # Skip empty rows
                            rows.append(cells)
                    if rows:  # Add only non-empty tables
                        all_tables.append(rows)
            else:
                # If there are no tables, try parsing text as a table
                # (separators are tabs or repeated spaces)
                rows = []
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if text:
                        # Try splitting by tabs
                        if '\t' in text:
                            cells = [c.strip() for c in text.split('\t')]
                        else:
                            cells = [text]
                        rows.append(cells)
                if rows:
                    all_tables.append(rows)

            return all_tables

        except Exception as e:
            logger.error(f"Error extracting tables from DOCX: {e}")
            return []

    def extract_first_table(self, path: str) -> List[List[str]]:
        """Extract first table."""
        all_tables = self.extract_tables_from_docx(path)
        if all_tables:
            self._has_header = False  # Reset for the first table
            return all_tables[0]
        return []

    def detect_columns(self, rows: List[List[str]]) -> Dict[str, int]:
        """Detect columns."""
        if not rows:
            return DEFAULT_COLUMN_MAPPING.copy()

        # Check the first row for headers
        header_row = rows[0] if rows else []
        mapping = {}
        has_header = False

        # Patterns for automatic detection
        patterns = {
            'character': [r'персонаж', r'имя', r'actor', r'character', r'char', r'voice'],
            'time_start': [r'начало', r'start', r'time.*start', r'in', r'from'],
            'time_end': [r'конец', r'end', r'time.*end', r'out', r'to'],
            'time_split': [r'тайминг', r'timing', r'time\s*$', r'время', r'таймкод'],
            'text': [r'текст', r'text', r'replica', r'фраз', r'dialog', r'speech', r'реплика']
        }

        # Map headers to column types
        for col_idx, header in enumerate(header_row):
            header_lower = header.lower()
            for col_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, header_lower):
                        if col_type not in mapping:  # Use the first match
                            mapping[col_type] = col_idx
                            has_header = True
                        break

        # Use defaults if not all columns were detected
        default_mapping = DEFAULT_COLUMN_MAPPING.copy()
        for col_type, default_idx in default_mapping.items():
            if col_type not in mapping:
                # If this is a text column and unnamed columns exist
                if col_type == 'text':
                    # Look for the last column
                    if rows:
                        max_cols = max(len(row) for row in rows)
                        if max_cols > 0:
                            mapping[col_type] = max_cols - 1
                else:
                    mapping[col_type] = default_idx

        # Store the header presence flag
        self._has_header = has_header

        return mapping

    def get_available_columns(self, rows: List[List[str]]) -> List[int]:
        """Return available columns."""
        if not rows:
            return []

        max_cols = max(len(row) for row in rows)
        return list(range(max_cols))

    def parse_with_mapping(
        self,
        rows: List[List[str]],
        column_mapping: Dict[str, Optional[int]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse with mapping."""
        from collections import defaultdict

        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )
        lines_list = []

        # Detect whether a header is present and skip the first row only then
        has_header = getattr(self, '_has_header', True)
        start_idx = 1 if has_header and len(rows) > 1 else 0
        data_rows = rows[start_idx:] if rows else []

        for row_idx, row in enumerate(data_rows):
            try:
                # Extract row data
                char_name = self._get_cell_value(row, column_mapping.get('character'))
                time_start = self._get_cell_value(row, column_mapping.get('time_start'))
                time_end = self._get_cell_value(row, column_mapping.get('time_end'))
                time_split = self._get_cell_value(row, column_mapping.get('time_split'))
                text = self._get_cell_value(row, column_mapping.get('text'))

                # Skip empty rows
                if not text and not char_name:
                    continue

                # Parse timings
                start_seconds = None
                end_seconds = None

                # Try a combined timing column first
                if time_split:
                    start_seconds, end_seconds = self._parse_split_time(time_split)

                # If that fails or split timing is absent, try separate timing columns
                if start_seconds is None:
                    start_seconds = self._parse_time(time_start)
                if end_seconds is None:
                    end_seconds = self._parse_time(time_end)

                # Use zero when no timings are available
                if start_seconds is None:
                    start_seconds = 0.0
                if end_seconds is None:
                    end_seconds = start_seconds + 1.0

                line_data = {
                    's': start_seconds,
                    'e': end_seconds,
                    'char': char_name or '',
                    'text': text or '',
                    's_raw': time_start or time_split or '',
                    'e_raw': time_end or '',
                }
                lines_list.append(line_data)

                # Update statistics
                if char_name:
                    char_data[char_name]["lines"] += 1
                    char_data[char_name]["raw"].append(line_data)

            except Exception as e:
                logger.warning(f"Error parsing row {row_idx}: {e}")
                continue

        # Calculate statistics
        # Do not merge DOCX rows; each row is a separate take
        # (the document is already merged; it is not subtitle timing)
        stats = []
        for char, info in char_data.items():
            char_lines = info["raw"]
            
            # For DOCX, rings equal lines because each replica is already merged
            rings = info["lines"]
            words = 0

            if char_lines:
                for line_data in char_lines:
                    words += len(line_data['text'].split())

            stats.append({
                "name": char,
                "lines": info["lines"],
                "rings": rings,
                "words": words
            })

        return stats, lines_list

    def _get_cell_value(self, row: List[str], col_idx: Optional[int]) -> Optional[str]:
        """Return cell value."""
        if col_idx is None or col_idx < 0 or col_idx >= len(row):
            return None
        return row[col_idx] if row[col_idx] else None

    def _parse_time(self, time_str: Optional[str]) -> Optional[float]:
        """Parse time."""
        if not time_str:
            return None

        time_str = time_str.strip()

        # Try several formats
        formats = [
            r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d+)',  # HH:MM:SS,mmm
            r'(\d{1,2}):(\d{2})[,.](\d+)',  # MM:SS,mmm
            r'(\d{1,2}):(\d{2}):(\d{2})',  # HH:MM:SS
            r'(\d{1,2}):(\d{2})',  # MM:SS
        ]

        for pattern in formats:
            match = re.match(pattern, time_str)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 4:  # HH:MM:SS,mmm
                        h, m, s, ms = groups
                        seconds = int(h) * 3600 + int(m) * 60 + float(f"{s}.{ms}")
                        return seconds
                    elif len(groups) == 3:  # Internal implementation detail
                        if ':' in time_str and time_str.count(':') == 2:
                            h, m, s = groups
                            seconds = int(h) * 3600 + int(m) * 60 + float(s)
                            return seconds
                        else:
                            m, s, ms = groups
                            seconds = int(m) * 60 + float(f"{s}.{ms}")
                            return seconds
                    elif len(groups) == 2:  # MM:SS
                        m, s = groups
                        seconds = int(m) * 60 + float(s)
                        return seconds
                except (ValueError, IndexError):
                    continue

        # If no format matches, try the standard parser
        try:
            return srt_time_to_seconds(time_str.replace(',', '.'))
        except Exception:
            return None

    def _parse_split_time(self, time_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        """Parse split time."""
        if not time_str:
            return None, None

        time_str = time_str.strip()

        # Try to find a separator
        for separator in self.time_separators:
            # Escape special regex characters
            if separator == '\\t':
                separator = '\t'
            escaped_sep = re.escape(separator)

            # Find a separator with optional surrounding spaces
            pattern = rf'^(.+?)\s*{escaped_sep}\s*(.+)$'
            match = re.match(pattern, time_str)

            if match:
                start_part = match.group(1).strip()
                end_part = match.group(2).strip()

                start_seconds = self._parse_time(start_part)
                end_seconds = self._parse_time(end_part)

                if start_seconds is not None and end_seconds is not None:
                    return start_seconds, end_seconds

        return None, None

    def get_preview_data(
        self,
        rows: List[List[str]],
        column_mapping: Dict[str, Optional[int]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return preview data."""
        preview = []
        # Honor the header flag
        has_header = getattr(self, '_has_header', True)
        start_idx = 1 if has_header and len(rows) > 1 else 0
        data_rows = rows[start_idx:start_idx + limit] if rows else []

        for row in data_rows:
            preview_row = {
                'raw': row,
                'mapped': {}
            }

            for col_type, col_idx in column_mapping.items():
                value = self._get_cell_value(row, col_idx)
                preview_row['mapped'][col_type] = value

                # Add the parsed value for timing fields
                if col_type in ['time_start', 'time_end']:
                    parsed = self._parse_time(value)
                    preview_row[f'{col_type}_parsed'] = parsed
                elif col_type == 'time_split':
                    start, end = self._parse_split_time(value)
                    preview_row['time_split_start_parsed'] = start
                    preview_row['time_split_end_parsed'] = end

            preview.append(preview_row)

        return preview
