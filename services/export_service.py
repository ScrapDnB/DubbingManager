"""Service for exporting project data."""

import os
import sys
import logging
import re
from html import escape
from typing import Dict, List, Any, Optional, Set, Tuple, Callable

from services.assignment_service import get_actor_for_character
from utils.helpers import (
    hex_to_rgba_string,
    format_seconds_to_full_tc,
    format_seconds_to_tc,
    format_timing_range,
)
from utils.i18n import translate_source

logger = logging.getLogger(__name__)

try:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None
    WD_ORIENT = None
    WD_CELL_VERTICAL_ALIGNMENT = None
    WD_TABLE_ALIGNMENT = None
    WD_ALIGN_PARAGRAPH = None
    OxmlElement = None
    qn = None
    Cm = None
    Pt = None
    RGBColor = None
    logger.warning("python-docx not available - DOCX export disabled")

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("openpyxl not available - Excel export disabled")


class ExportService:
    """Export Service implementation."""

    def __init__(self, project_data: Dict[str, Any]):
        self.project_data = project_data

    def _get_effective_highlight_filter(
        self,
        cfg: Dict[str, Any]
    ) -> Optional[Set[str]]:
        """Return effective highlight filter."""
        highlight_ids = cfg.get('highlight_ids_export')
        if highlight_ids is None:
            return None

        selected_ids = set(highlight_ids)
        all_actor_ids = set(self.project_data.get("actors", {}).keys())
        if selected_ids == all_actor_ids:
            return None

        return selected_ids

    def _format_export_timing(
        self,
        line: Dict[str, Any],
        cfg: Dict[str, Any]
    ) -> str:
        """Format timing according to export settings."""
        start = line.get('s', 0)
        end = line.get('e', 0)
        start_only = cfg.get('time_display', 'range') == 'start'

        if cfg.get('round_time', False):
            start_tc = format_seconds_to_tc(start)
            if start_only:
                return start_tc
            return f"{start_tc}-{format_seconds_to_tc(end)}"

        if start_only:
            return format_seconds_to_full_tc(start)

        return format_timing_range(start, end)

    def _format_table_timing_text(
        self,
        line: Dict[str, Any],
        cfg: Dict[str, Any]
    ) -> str:
        """Format timing for table-like exports."""
        timing = self._format_export_timing(line, cfg)
        if cfg.get('time_display', 'range') == 'start':
            return timing
        return timing.replace('-', '\n')

    def _table_column_width_rem(self, cfg: Dict[str, Any], key: str) -> float:
        """Return a sane table column width in rem units."""
        defaults = {
            'table_width_time': 7.0,
            'table_width_char': 10.0,
            'table_width_actor': 8.5,
        }
        try:
            value = float(cfg.get(key, defaults[key]))
        except (TypeError, ValueError):
            value = defaults[key]
        return max(4.0, min(24.0, value))

    def _table_column_width_css(self, cfg: Dict[str, Any], key: str) -> str:
        """Return responsive CSS width for a metadata table column."""
        width = self._table_column_width_rem(cfg, key)
        min_width = max(4.0, width * 0.72)
        vw_width = max(5.0, width * 1.05)
        return f"clamp({min_width:.2f}rem, {vw_width:.2f}vw, {width:.2f}rem)"

    def _table_column_width_cm(self, cfg: Dict[str, Any], key: str) -> float:
        """Return DOCX column width matching table preview proportions."""
        return self._table_column_width_rem(cfg, key) * 0.18

    def _docx_font_size_from_cfg(
        self,
        cfg: Dict[str, Any],
        key: str,
        default: float
    ) -> float:
        """Map preview pixel font settings to readable DOCX point sizes."""
        try:
            value = float(cfg.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(7.0, min(18.0, value * 0.5))

    def process_merge_logic(
        self,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply replica merge rules."""
        if lines and all(line.get("_working_text") for line in lines):
            return [line.copy() for line in lines]

        p_short = cfg.get('p_short', 0.5)
        p_long = cfg.get('p_long', 2.0)
        fps = cfg.get('fps', 25.0)
        # Convert merge_gap from frames to seconds
        gap_seconds = cfg.get('merge_gap', 5) / fps

        res = []
        curr = None

        if lines:
            curr = lines[0].copy()
            curr['parts'] = [{
                'id': lines[0]['id'],
                'text': lines[0]['text'],
                'sep': ''
            }]

            for i in range(1, len(lines)):
                nxt = lines[i]
                diff = nxt['s'] - curr['e']

                if (
                    cfg.get('merge', True) and
                    nxt['char'] == curr['char'] and
                    diff < gap_seconds
                ):
                    if diff >= p_long:
                        sep = " //  "
                    elif diff >= p_short:
                        sep = " /  "
                    else:
                        sep = "  "

                    curr['parts'].append({
                        'id': nxt['id'],
                        'text': nxt['text'],
                        'sep': sep
                    })
                    curr['text'] += sep + nxt['text']
                    curr['e'] = nxt['e']
                else:
                    res.append(curr)
                    curr = nxt.copy()
                    curr['parts'] = [{
                        'id': nxt['id'],
                        'text': nxt['text'],
                        'sep': ''
                    }]

            res.append(curr)

        # Add source_ids and source_texts
        for item in res:
            if 'parts' in item:
                item['source_ids'] = [p['id'] for p in item['parts']]
                item['source_texts'] = [p['text'] for p in item['parts']]
            else:
                item['source_ids'] = [item.get('id')]
                item['source_texts'] = [item.get('text', '')]

        return res

    def generate_html(
        self,
        ep: str,
        processed: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        highlight_ids: Optional[List[str]] = None,
        layout_type: str = "Таблица",
        is_editable: bool = True
    ) -> str:
        """Generate HTML export content."""
        js = self._get_js_for_mode(is_editable)
        html = self._get_html_header(js, cfg)

        project_name = escape(str(self.project_data.get('project_name', 'Project')))
        ep_label = escape(str(ep))
        html += f"<h1>{project_name} - Серия {ep_label}</h1>"

        actors = self.project_data.get("actors", {})
        all_actor_ids = set(actors.keys())
        is_full_filter = (
            highlight_ids is not None and
            set(highlight_ids) == all_actor_ids
        )
        effective_filter = (
            None
            if (highlight_ids is None or is_full_filter)
            else set(highlight_ids)
        )
        use_color = cfg.get('use_color', True)
        soften_colors = cfg.get('soften_colors', True)

        for idx, line in enumerate(processed):
            # Validate replica data
            if 'char' not in line:
                logger.warning(f"Skipping line without 'char' field: {line}")
                continue
            if 'text' not in line:
                logger.warning(f"Skipping line without 'text' field: {line}")
                continue

            aid = get_actor_for_character(self.project_data, line['char'], ep)
            actor = actors.get(aid, {"name": "-", "color": "#ffffff"})

            is_highlighted = (
                effective_filter is None or
                aid in effective_filter
            )
            h_class = "highlighted-block" if is_highlighted else ""

            bg_color, border_col = self._get_colors(
                use_color, is_highlighted, actor, soften_colors
            )
            text_color = self._negative_text_color(
                aid,
                cfg,
                is_highlighted
            )

            text_html = self._format_text_html(line, is_editable)

            if layout_type == "Таблица":
                html += self._build_table_row(
                    line, actor, text_html, bg_color, text_color, h_class, cfg,
                    is_first=idx == 0, is_last=idx == len(processed) - 1
                )
            else:
                html += self._build_scenario_row(
                    line, actor, text_html, bg_color, border_col, text_color,
                    h_class, cfg
                )

        return html + "</body></html>"

    def _get_js_for_mode(self, is_editable: bool) -> str:
        """Return js for mode."""
        if is_editable:
            return self._get_editable_js()
        return self._get_static_css()

    def _get_html_header(self, js: str, cfg: Dict[str, Any]) -> str:
        """Return the HTML document header."""
        time_width = self._table_column_width_css(cfg, 'table_width_time')
        char_width = self._table_column_width_css(cfg, 'table_width_char')
        actor_width = self._table_column_width_css(cfg, 'table_width_actor')
        return f"""<html><head><meta charset='utf-8'>{js}<style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            padding: 36px clamp(18px, 4vw, 64px);
            background: #f6f7f8;
            color: #202124;
        }}
        h1 {{
            margin: 0 0 24px;
            font-size: 24px;
            font-weight: 650;
            line-height: 1.25;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            background: white;
            border: 1px solid #d8dde3;
        }}
        td, th {{
            border: 1px solid #d8dde3;
            padding: 8px 10px;
            vertical-align: top;
            overflow-wrap: break-word;
            word-break: normal;
        }}
        th {{
            background: #eef1f4;
            color: #4f5965;
            font-size: 12px;
            font-weight: 650;
            text-align: left;
            padding: 7px 10px;
        }}
        .col-t {{
            width: {time_width};
        }}
        .col-c {{
            width: {char_width};
        }}
        .col-a {{
            width: {actor_width};
        }}
        .col-txt {{
            width: auto;
        }}
        .t {{
            font-family: monospace;
            font-size: {cfg.get('f_time', 12)}px;
            line-height: 1.25;
            color: inherit;
            white-space: normal;
        }}
        .c {{
            font-weight: bold;
            font-size: {cfg.get('f_char', 14)}px;
            line-height: 1.25;
        }}
        .a {{
            font-style: italic;
            font-size: {cfg.get('f_actor', 14)}px;
            line-height: 1.25;
        }}
        .txt {{
            font-size: {cfg.get('f_text', 16)}px;
            line-height: 1.45;
        }}
        .time-sep {{
            display: block;
            line-height: 0.9;
            opacity: 0.75;
        }}
        .line-container {{
            margin-bottom: 30px;
            padding: 20px;
            border-left: 8px solid #eee;
            background: white;
        }}
        </style></head><body>
        """

    def _get_editable_js(self) -> str:
        """Return editable js."""
        return """
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
            var backend;
            new QWebChannel(qt.webChannelTransport, function (channel) {
                backend = channel.objects.backend;
            });

            function onBlur(el) {
                if(backend) {
                    var cleanText = el.innerText;
                    cleanText = cleanText.replace(/(\\r\\n|\\n|\\r)/gm, "\\n");
                    backend.update_text(el.id, cleanText);
                }
            }
            function onKeyPress(e, el) {
                if (e.keyCode === 13) {
                    e.preventDefault();
                    el.blur();
                }
            }
        </script>
        <style>
            .edit-span {
                border-bottom: 1px dashed #ccc;
                padding: 1px 2px;
            }
            .edit-span:focus {
                background-color: #fff;
                outline: 2px solid #5B9BD5;
                border-bottom: none;
            }
            .sep {
                color: #888;
                font-weight: bold;
            }
            .highlighted-block {
                transition: outline 0.3s, box-shadow 0.3s;
            }
        </style>
        """

    def _get_static_css(self) -> str:
        """Return CSS for static HTML export."""
        return """
        <style>
            .highlighted-block {
                transition: outline 0.3s, box-shadow 0.3s;
            }
        </style>
        """

    def _get_colors(
        self,
        use_color: bool,
        is_highlighted: bool,
        actor: Dict[str, Any],
        soften_colors: bool = True
    ) -> tuple:
        """Return colors for an export row."""
        if use_color and is_highlighted:
            actor_color = actor.get('color', '#ffffff')
            bg_color = (
                hex_to_rgba_string(actor_color, 0.22)
                if soften_colors
                else actor_color
            )
            border_col = actor_color
        else:
            bg_color = "#ffffff"
            border_col = "#eee"
        return bg_color, border_col

    def _negative_text_color(
        self,
        actor_id: Optional[str],
        cfg: Dict[str, Any],
        is_highlighted: bool
    ) -> Optional[str]:
        """Return white text when actor highlight is marked as negative."""
        if not actor_id or not is_highlighted:
            return None
        negative_ids = set(cfg.get('highlight_negative_ids_export') or [])
        if actor_id in negative_ids:
            return "#ffffff"
        return None

    def _format_text_html(
        self,
        line: Dict[str, Any],
        is_editable: bool
    ) -> str:
        """Format text html."""
        text_html = ""

        if 'parts' in line:
            for part in line['parts']:
                if part['sep']:
                    sep = escape(str(part['sep']))
                    text_html += f"<span class='sep'>{sep}</span>"
                part_text = escape(str(part.get('text', '')))
                if is_editable:
                    part_id = escape(str(part.get('id', '')), quote=True)
                    text_html += (
                        f"<span id='{part_id}' "
                        f"class='edit-span' "
                        f"contenteditable='true' "
                        f"onblur='onBlur(this)' "
                        f"onkeypress='onKeyPress(event, this)'>"
                        f"{part_text}</span>"
                    )
                else:
                    text_html += f"<span>{part_text}</span>"
        else:
            text_html = escape(str(line.get('text', '')))

        return text_html

    def _format_timing_html(self, line: Dict[str, Any], cfg: Dict[str, Any]) -> str:
        """Format timing for table HTML, allowing ranges to wrap cleanly."""
        start_tc, end_tc = self._format_timing_parts(line, cfg)
        if cfg.get('time_display', 'range') == 'start':
            return escape(start_tc)

        return (
            f"{escape(start_tc)}"
            "<span class='time-sep'>-</span>"
            f"{escape(end_tc)}"
        )

    def _format_timing_parts(
        self,
        line: Dict[str, Any],
        cfg: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Return formatted start and end timing strings."""
        start = float(line.get('s', 0.0))
        end = float(line.get('e', 0.0))

        if cfg.get('round_time', False):
            return format_seconds_to_tc(start), format_seconds_to_tc(end)

        return format_seconds_to_full_tc(start), format_seconds_to_full_tc(end)

    def _format_timing_text(self, line: Dict[str, Any], cfg: Dict[str, Any]) -> str:
        """Format timing as plain text for scenario HTML."""
        start_tc, end_tc = self._format_timing_parts(line, cfg)
        if cfg.get('time_display', 'range') == 'start':
            return start_tc
        return f"{start_tc}-{end_tc}"

    def _build_table_row(
        self,
        line: Dict[str, Any],
        actor: Dict[str, Any],
        text_html: str,
        bg_color: str,
        text_color: Optional[str],
        h_class: str,
        cfg: Dict[str, Any],
        is_first: bool,
        is_last: bool
    ) -> str:
        """Build one table export row."""
        columns = []
        if cfg.get('col_tc', True):
            timing = self._format_timing_html(line, cfg)
            columns.append((translate_source("Время"), "t", timing))
        if cfg.get('col_char', True):
            columns.append((translate_source("Персонаж"), "c", escape(str(line.get('char', '')))))
        if cfg.get('col_actor', True):
            actor_name = escape(str(actor.get('name', '-')))
            columns.append((translate_source("Актер"), "a", actor_name))
        if cfg.get('col_text', True):
            columns.append((translate_source("Текст"), "txt", text_html))

        if not columns:
            columns.append((" ", "txt", ""))

        cells = "".join(
            f"<td class='{css_class}'>{value}</td>"
            for _header, css_class, value in columns
        )
        color_style = f"; color:{text_color or '#000000'}"
        row = (
            f"<tr style='background-color:{bg_color}{color_style}' "
            f"class='{h_class}'>"
            f"{cells}</tr>"
        )

        if is_first:
            colgroup = "".join(
                f"<col class='col-{css_class}'>"
                for _header, css_class, _value in columns
            )
            headers = "".join(
                f"<th>{header}</th>"
                for header, _css_class, _value in columns
            )
            header = (
                f"<table><colgroup>{colgroup}</colgroup><thead><tr>"
                f"{headers}"
                "</tr></thead><tbody>"
            )
            row = header + row

        if is_last:
            row += "</tbody></table>"

        return row

    def _build_scenario_row(
        self,
        line: Dict[str, Any],
        actor: Dict[str, Any],
        text_html: str,
        bg_color: str,
        border_col: str,
        text_color: Optional[str],
        h_class: str,
        cfg: Dict[str, Any]
    ) -> str:
        """Build scenario row."""
        meta_parts = []
        if cfg.get('col_char', True):
            char = escape(str(line.get('char', '')))
            meta_parts.append(f"<span class='c'><b>{char}</b></span>")
        if cfg.get('col_tc', True):
            timing = escape(self._format_timing_text(line, cfg))
            meta_parts.append(f"<span class='t'>[{timing}]</span>")
        if cfg.get('col_actor', True):
            actor_name = escape(str(actor.get('name', '-')))
            meta_parts.append(f"<span class='a'><i>({actor_name})</i></span>")

        meta_html = " ".join(meta_parts)
        text_block = (
            f"<div class='txt'>{text_html}</div>"
            if cfg.get('col_text', True)
            else ""
        )
        color_style = f"; color:{text_color or '#000000'}"
        return (
            f"<div class='line-container {h_class}' "
            f"style='background-color:{bg_color}; "
            f"border-left-color:{border_col}{color_style}'>"
            f"<div class='meta'>{meta_html}</div>"
            f"{text_block}</div>"
        )

    def _episode_sort_key(self, ep_num: Any) -> Tuple[Any, ...]:
        """Return a natural sort key for episode identifiers."""
        parts = re.split(r'(\d+)', str(ep_num))
        return tuple(
            (0, int(part)) if part.isdigit() else (1, part.lower())
            for part in parts
            if part != ''
        )

    # ==========================================================================
    # Excel export
    # ==========================================================================

    def _get_times_font(
        self,
        size: float = 14.0,
        bold: bool = False,
        italic: bool = False,
        color: Optional[str] = None
    ) -> Font:
        """Return times font."""
        return Font(
            name='Times New Roman',
            size=size,
            bold=bold,
            italic=italic,
            charset=204,
            color=color
        )

    def _get_thin_border(self) -> Border:
        """Return thin border."""
        side = Side(style='thin', color='00000000')
        return Border(left=side, right=side, top=side, bottom=side)

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        # Split on whitespace and count non-empty tokens
        words = re.findall(r'\S+', text.strip())
        return len(words)

    def _apply_cell_styling(
        self,
        cell,
        font_size: float = 14.0,
        wrap_text: bool = False,
        fill_color: Optional[str] = None,
        text_color: Optional[str] = None,
        border: Optional[Border] = None
    ):
        """Apply cell styling."""
        font_color = None
        if text_color:
            font_color = text_color.replace('#', '')
            if len(font_color) == 6:
                font_color = 'FF' + font_color
        cell.font = self._get_times_font(size=font_size, color=font_color)
        cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=wrap_text)
        if border:
            cell.border = border
        if fill_color:
            # Ensure color is in ARGB format (8 chars)
            color = fill_color.replace('#', '')
            if len(color) == 6:
                color = 'FF' + color  # Add alpha channel
            fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
            cell.fill = fill

    def _create_actors_summary_sheet(
        self,
        wb: openpyxl.Workbook,
        episodes_data: Dict[str, List[Dict[str, Any]]],
        cfg: Dict[str, Any]
    ):
        """Create actors summary sheet."""
        # Remove the default sheet if it exists
        if 'Sheet' in wb.sheetnames:
            del wb['Sheet']

        ws = wb.create_sheet(title='Сводка')

        actors = self.project_data.get('actors', {})
        effective_filter = self._get_effective_highlight_filter(cfg)
        soften_colors = cfg.get('soften_colors', True)

        # Sort episode numbers for the correct column order
        sorted_ep_keys = sorted(episodes_data.keys(), key=self._episode_sort_key)

        # Collect actor statistics
        actor_stats: Dict[str, Dict[str, Any]] = {}
        for actor_id, actor_data in actors.items():
            actor_stats[actor_id] = {
                'name': actor_data.get('name', ''),
                'color': actor_data.get('color', '#FFFFFF'),
                'roles': [],
                'episode_words': {}
            }

        # Count words by episode using the real episode numbers
        for ep_key in sorted_ep_keys:
            lines = episodes_data[ep_key]
            for line in lines:
                char_name = line.get('char', '')
                actor_id = get_actor_for_character(
                    self.project_data, char_name, ep_key
                )
                if actor_id and actor_id in actor_stats:
                    if char_name not in actor_stats[actor_id]['roles']:
                        actor_stats[actor_id]['roles'].append(char_name)
                    if ep_key not in actor_stats[actor_id]['episode_words']:
                        actor_stats[actor_id]['episode_words'][ep_key] = 0
                    actor_stats[actor_id]['episode_words'][ep_key] += self._count_words(line.get('text', ''))

        # Dynamic headers with real episode numbers
        headers = ['Актёр', 'Персонаж']
        for ep_key in sorted_ep_keys:
            headers.append(f'{ep_key} серия')
        headers.append('Всего слов')
        ws.append(headers)

        # Header styles
        header_font = self._get_times_font(size=14.0)
        header_alignment = Alignment(horizontal='left', vertical='top')
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_font
            cell.alignment = header_alignment

        # Column widths
        ws.column_dimensions['A'].width = 21.5
        ws.column_dimensions['B'].width = 55.33
        # Dynamic width for episode columns
        for i in range(1, len(sorted_ep_keys) + 2):
            col_letter = openpyxl.utils.get_column_letter(2 + i)
            ws.column_dimensions[col_letter].width = 11.83

        # First-row height
        ws.row_dimensions[1].height = 20.0

        # Fill data
        row_num = 2
        thin_border = self._get_thin_border()
        for actor_id, stats in actor_stats.items():
            if not stats['roles']:  # Skip actors without roles
                continue

            actor_name = stats['name']
            roles_str = ', '.join(stats['roles'])
            episode_words = stats['episode_words']

            # Actor color
            is_highlighted = (
                effective_filter is None or
                actor_id in effective_filter
            )
            if is_highlighted:
                actor_color = stats['color']
                fill_color = (
                    self._docx_soft_fill_color(actor_color)
                    if soften_colors
                    else actor_color.replace('#', '')
                )
            else:
                fill_color = 'FFFFFF'
            text_color = self._negative_text_color(actor_id, cfg, is_highlighted)

            # Actor-name cell
            name_cell = ws.cell(row=row_num, column=1, value=actor_name)
            self._apply_cell_styling(
                name_cell,
                font_size=14.0,
                fill_color=fill_color,
                text_color=text_color,
                border=thin_border
            )

            # Character cell
            roles_cell = ws.cell(row=row_num, column=2, value=roles_str)
            self._apply_cell_styling(roles_cell, font_size=9.0, border=thin_border)

            # Word-count cells by episode in sorted-key order
            total_words = 0
            for ep_idx, ep_key in enumerate(sorted_ep_keys):
                word_count = episode_words.get(ep_key, 0)
                total_words += word_count
                cell = ws.cell(row=row_num, column=3 + ep_idx, value=word_count)
                self._apply_cell_styling(cell, font_size=14.0, border=thin_border)

            # Total word-count cell
            total_cell = ws.cell(row=row_num, column=3 + len(sorted_ep_keys), value=total_words)
            self._apply_cell_styling(total_cell, font_size=14.0, border=thin_border)

            row_num += 1

        # Do not add a filter; sorting is not needed on the actor page

    def _create_episode_sheet(
        self,
        wb: openpyxl.Workbook,
        ep_num: str,
        processed: List[Dict[str, Any]],
        cfg: Dict[str, Any]
    ):
        """Create one episode sheet."""
        sheet_name = f'серия ({ep_num})'
        ws = wb.create_sheet(title=sheet_name)

        actors = self.project_data.get('actors', {})
        use_color = cfg.get('use_color', True)
        soften_colors = cfg.get('soften_colors', True)
        effective_filter = self._get_effective_highlight_filter(cfg)

        # Choose columns from settings
        col_tc = cfg.get('col_tc', True)
        col_char = cfg.get('col_char', True)
        col_actor = cfg.get('col_actor', True)
        col_text = cfg.get('col_text', True)

        # Headers only for selected columns
        headers = [translate_source('Номер')]
        if col_tc:
            headers.append(translate_source('Таймкод'))
        if col_char:
            headers.append(translate_source('Персонаж'))
        if col_actor:
            headers.append(translate_source('Актёр'))
        if col_text:
            headers.append(translate_source('Реплика'))
        ws.append(headers)

        # Header styles
        header_fonts = {
            'номер': self._get_times_font(size=14.0),
            'тайм': self._get_times_font(size=13.0),
            'персонаж': self._get_times_font(size=12.0),
            'актёр': self._get_times_font(size=14.0),
            'реплика': self._get_times_font(size=14.0)
        }
        header_alignment = Alignment(horizontal='left', vertical='top')

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.font = header_fonts.get(header, self._get_times_font(size=14.0))
            cell.alignment = header_alignment

        # Column widths
        col_widths = {
            'Номер': 6.5,
            'Таймкод': 10.5,
            'Персонаж': 18.0,
            'Актёр': 18.0,
            'Реплика': 118.0
        }
        for col_idx, header in enumerate(headers, 1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = col_widths.get(header, 13.0)

        # Thin borders for all cells
        thin_border = self._get_thin_border()

        # Fill data
        for row_idx, line in enumerate(processed, 2):
            char_name = line.get('char', '')
            actor_id = get_actor_for_character(
                self.project_data, char_name, ep_num
            )
            actor = actors.get(actor_id, {}) if actor_id else {}
            actor_name = actor.get('name', '-') if actor else '-'

            # Determine the color
            is_highlighted = (
                effective_filter is None or
                actor_id in effective_filter
            )
            if use_color and actor_id and is_highlighted:
                actor_color = actor.get('color', '#FFFFFF')
                color_hex = (
                    self._docx_soft_fill_color(actor_color)
                    if soften_colors
                    else actor_color.replace('#', '')
                )
            else:
                color_hex = 'FFFFFF'
            text_color = self._negative_text_color(
                actor_id,
                cfg,
                is_highlighted
            )

            timing = self._format_export_timing(line, cfg)

            # Row data only for selected columns
            row_data = [row_idx - 1]  # Always include the row number
            if col_tc:
                row_data.append(timing)
            if col_char:
                row_data.append(char_name)
            if col_actor:
                row_data.append(actor_name)
            if col_text:
                row_data.append(line.get('text', ''))

            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)

                # Apply styles
                font_size = 14.0
                # Use wrap_text for timing and replica text
                timing_col = 2 if col_tc else None  # Timing column, second after the number
                wrap_text = (timing_col and col == timing_col) or (col_text and col == len(row_data))

                self._apply_cell_styling(
                    cell,
                    font_size=font_size,
                    wrap_text=wrap_text,
                    fill_color=color_hex,
                    text_color=text_color,
                    border=thin_border
                )

                # Set row height for the replica column
                if col_text and col == len(row_data):
                    # Approximate row height based on text length
                    text = value if isinstance(value, str) else ''
                    lines_count = max(1, text.count('\n') + 1 + len(text) // 80)
                    ws.row_dimensions[row_idx].height = min(120, 20 + lines_count * 15)

        # Add a filter
        last_col_letter = openpyxl.utils.get_column_letter(len(headers))
        ws.auto_filter.ref = f'A1:{last_col_letter}{len(processed) + 1}'

    def create_excel_book(
        self,
        episodes_data: Dict[str, List[Dict[str, Any]]],
        cfg: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create an Excel workbook with multiple sheets."""
        if not EXCEL_AVAILABLE:
            raise ImportError("openpyxl not available")

        if cfg is None:
            cfg = self.project_data.get("export_config", {})

        wb = openpyxl.Workbook()

        # Create the actor summary sheet
        self._create_actors_summary_sheet(wb, episodes_data, cfg)

        # Create episode sheets in sorted order
        for ep_num in sorted(episodes_data.keys(), key=self._episode_sort_key):
            lines = episodes_data[ep_num]
            self._create_episode_sheet(wb, ep_num, lines, cfg)

        return wb

    def _set_docx_cell_shading(self, cell: Any, color_hex: str) -> None:
        """Set a table cell background color."""
        tc_pr = cell._tc.get_or_add_tcPr()
        shading = tc_pr.find(qn('w:shd'))
        if shading is None:
            shading = OxmlElement('w:shd')
            tc_pr.append(shading)
        shading.set(qn('w:fill'), color_hex.replace('#', '').upper())

    def _set_docx_cell_width(self, cell: Any, width_cm: float) -> None:
        """Set a table cell width in twentieths of a point."""
        tc_pr = cell._tc.get_or_add_tcPr()
        width = tc_pr.find(qn('w:tcW'))
        if width is None:
            width = OxmlElement('w:tcW')
            tc_pr.append(width)
        width.set(qn('w:w'), str(int(width_cm * 567)))
        width.set(qn('w:type'), 'dxa')

    def _cm_to_twips(self, width_cm: float) -> int:
        """Convert centimeters to Word twips."""
        return int(width_cm * 567)

    def _set_docx_table_grid(
        self,
        table: Any,
        column_widths: List[float]
    ) -> None:
        """Set fixed DOCX table layout and grid for better Pages support."""
        table_width = sum(column_widths)
        table_pr = table._tbl.tblPr

        layout = table_pr.find(qn('w:tblLayout'))
        if layout is None:
            layout = OxmlElement('w:tblLayout')
            table_pr.append(layout)
        layout.set(qn('w:type'), 'fixed')

        width = table_pr.find(qn('w:tblW'))
        if width is None:
            width = OxmlElement('w:tblW')
            table_pr.append(width)
        width.set(qn('w:w'), str(self._cm_to_twips(table_width)))
        width.set(qn('w:type'), 'dxa')

        existing_grid = table._tbl.tblGrid
        if existing_grid is not None:
            table._tbl.remove(existing_grid)
        grid = OxmlElement('w:tblGrid')
        for column_width in column_widths:
            grid_col = OxmlElement('w:gridCol')
            grid_col.set(qn('w:w'), str(self._cm_to_twips(column_width)))
            grid.append(grid_col)
        table._tbl.insert(0, grid)

    def _docx_soft_fill_color(self, color_hex: str, alpha: float = 0.22) -> str:
        """Return a light color similar to transparent HTML row highlight."""
        value = str(color_hex or "").strip().lstrip("#")
        if len(value) != 6:
            return "FFFFFF"
        try:
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
        except ValueError:
            return "FFFFFF"
        red = round(255 - (255 - red) * alpha)
        green = round(255 - (255 - green) * alpha)
        blue = round(255 - (255 - blue) * alpha)
        return f"{red:02X}{green:02X}{blue:02X}"

    def _set_docx_cell_text(
        self,
        cell: Any,
        text: Any,
        font_size: float,
        bold: bool = False,
        align: Any = WD_ALIGN_PARAGRAPH.LEFT,
        fill_color: Optional[str] = None,
        text_color: Optional[str] = None
    ) -> None:
        """Fill a DOCX table cell with styled text."""
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.alignment = align
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        run = paragraph.add_run(str(text or ""))
        run.bold = bold
        run.font.name = "Segoe UI"
        run._element.rPr.rFonts.set(qn('w:eastAsia'), "Segoe UI")
        run.font.size = Pt(font_size)
        if text_color:
            clean_color = text_color.strip().lstrip("#")
            if len(clean_color) == 6:
                run.font.color.rgb = RGBColor.from_string(clean_color.upper())
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        if fill_color:
            self._set_docx_cell_shading(cell, fill_color)

    def _create_docx_episode_table(
        self,
        document: Any,
        ep_num: str,
        processed: List[Dict[str, Any]],
        cfg: Dict[str, Any]
    ) -> None:
        """Create a DOCX table for one episode."""
        actors = self.project_data.get('actors', {})
        use_color = cfg.get('use_color', True)
        soften_colors = cfg.get('soften_colors', True)
        effective_filter = self._get_effective_highlight_filter(cfg)

        columns: List[Tuple[str, str, float, float]] = []
        if cfg.get('col_tc', True):
            columns.append((
                translate_source('Время'),
                'time',
                self._table_column_width_cm(cfg, 'table_width_time'),
                self._docx_font_size_from_cfg(cfg, 'f_time', 21),
            ))
        if cfg.get('col_char', True):
            columns.append((
                translate_source('Персонаж'),
                'char',
                self._table_column_width_cm(cfg, 'table_width_char'),
                self._docx_font_size_from_cfg(cfg, 'f_char', 20),
            ))
        if cfg.get('col_actor', True):
            columns.append((
                translate_source('Актёр'),
                'actor',
                self._table_column_width_cm(cfg, 'table_width_actor'),
                self._docx_font_size_from_cfg(cfg, 'f_actor', 14),
            ))
        if cfg.get('col_text', True):
            metadata_width = sum(column[2] for column in columns)
            columns.append((
                translate_source('Реплика'),
                'text',
                max(7.0, 18.0 - metadata_width),
                self._docx_font_size_from_cfg(cfg, 'f_text', 30),
            ))
        if not columns:
            columns.append((translate_source('Реплика'), 'text', 18.0, 11.0))

        if len(document.paragraphs) > 1 or document.tables:
            document.add_page_break()
        heading = document.add_heading(
            f"{self.project_data.get('project_name', 'Project')} - "
            f"{translate_source('Серия')} {ep_num}",
            level=1
        )
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT

        table = document.add_table(rows=1, cols=len(columns))
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        table.autofit = False
        table.style = 'Table Grid'
        self._set_docx_table_grid(
            table,
            [width for _title, _key, width, _size in columns]
        )

        header_cells = table.rows[0].cells
        for cell, (title, _key, width, _size) in zip(header_cells, columns):
            self._set_docx_cell_width(cell, width)
            self._set_docx_cell_text(
                cell,
                title,
                font_size=9.0,
                bold=True,
                fill_color='EAEAEA'
            )

        for line in processed:
            row_cells = table.add_row().cells
            char_name = line.get('char', '')
            actor_id = get_actor_for_character(
                self.project_data, char_name, ep_num
            )
            actor = actors.get(actor_id, {}) if actor_id else {}
            actor_name = actor.get('name', '-') if actor else '-'

            is_highlighted = (
                effective_filter is None or
                actor_id in effective_filter
            )
            fill_color = None
            if use_color and actor_id and is_highlighted:
                actor_color = actor.get('color', '#FFFFFF')
                fill_color = (
                    self._docx_soft_fill_color(actor_color)
                    if soften_colors
                    else actor_color.replace('#', '')
                )
            text_color = self._negative_text_color(
                actor_id,
                cfg,
                is_highlighted
            )

            values = {
                'time': self._format_table_timing_text(line, cfg),
                'char': char_name,
                'actor': actor_name,
                'text': line.get('text', ''),
            }
            for cell, (_title, key, width, font_size) in zip(row_cells, columns):
                self._set_docx_cell_width(cell, width)
                self._set_docx_cell_text(
                    cell,
                    values.get(key, ''),
                    font_size=font_size,
                    fill_color=fill_color,
                    text_color=text_color
                )

    def create_docx_document(
        self,
        episodes_data: Dict[str, List[Dict[str, Any]]],
        cfg: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Create a DOCX document with one table per episode."""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not available")

        if cfg is None:
            cfg = self.project_data.get("export_config", {})

        document = Document()
        section = document.sections[0]
        section.orientation = WD_ORIENT.PORTRAIT
        section.left_margin = Cm(1.2)
        section.right_margin = Cm(1.2)
        section.top_margin = Cm(1.2)
        section.bottom_margin = Cm(1.2)

        for ep_num in sorted(episodes_data.keys(), key=self._episode_sort_key):
            self._create_docx_episode_table(
                document,
                ep_num,
                episodes_data[ep_num],
                cfg
            )

        return document

    def export_to_docx(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        save_path: str,
        all_episodes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        merge_cfg: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Export data to a DOCX table document."""
        if not DOCX_AVAILABLE:
            return False, translate_source("python-docx не установлен")

        try:
            episodes_data = all_episodes if all_episodes else {ep: lines}
            if merge_cfg and not all_episodes:
                episodes_data = {
                    ep: self.process_merge_logic(lines, merge_cfg)
                }
            document = self.create_docx_document(episodes_data, cfg)
            document.save(save_path)
            return True, f"{translate_source('Экспортировано в')} {save_path}"
        except Exception as e:
            logger.error(f"DOCX export error: {e}")
            return False, f"{translate_source('Ошибка экспорта DOCX:')} {e}"

    def export_to_excel(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        save_path: str,
        all_episodes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        merge_cfg: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Export data to an Excel file."""
        if not EXCEL_AVAILABLE:
            return False, translate_source("openpyxl не установлен")

        try:
            # Use all episodes for the summary when provided
            if all_episodes:
                episodes_data = all_episodes
            else:
                episodes_data = {ep: lines}

            # Use merge_cfg for replica processing and cfg for formatting
            if merge_cfg is None:
                merge_cfg = self.project_data.get("replica_merge_config", {})

            processed_episodes = {}
            for ep_num, ep_lines in episodes_data.items():
                processed_episodes[ep_num] = self.process_merge_logic(ep_lines, merge_cfg)

            wb = self.create_excel_book(processed_episodes, cfg)
            wb.save(save_path)
            return True, f"{translate_source('Excel сохранён:')} {save_path}"
        except Exception as e:
            logger.error(f"Excel export error: {e}")
            return False, f"{translate_source('Ошибка экспорта:')} {e}"

    # ==========================================================================
    # Reaper RPP export
    # ==========================================================================

    def _hex_to_reaper_color(self, hex_color: str) -> int:
        """Hex to reaper color."""
        if not hex_color or not isinstance(hex_color, str):
            return 0

        value = hex_color.strip().lstrip('#')
        if len(value) != 6:
            return 0

        try:
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
        except ValueError:
            return 0

        return 0x01000000 | (blue << 16) | (green << 8) | red

    def _escape_rpp_text(self, text: Any) -> str:
        """Escape rpp text."""
        return (
            str(text)
            .replace('"', "' ")
            .replace('\r', ' ')
            .replace('\n', ' ')
            .strip()
        )

    def save_reaper_rpp(self, save_path: str, rpp_content: str) -> None:
        """Save an RPP file with an encoding Reaper reads reliably."""
        with open(save_path, 'w', encoding='utf-8-sig') as f:
            f.write(rpp_content)

    def generate_reaper_rpp(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        merge_cfg: Optional[Dict[str, Any]] = None,
        video_path: Optional[str] = None,
        use_video: bool = False,
        use_regions: bool = True
    ) -> str:
        """Generate a Reaper RPP project from episode lines."""
        if merge_cfg is None:
            merge_cfg = self.project_data.get("replica_merge_config", {})

        processed_lines = self.process_merge_logic(lines, merge_cfg)
        actors = self.project_data.get("actors", {})

        active_actor_ids: Set[str] = set()
        for line in processed_lines:
            actor_id = get_actor_for_character(
                self.project_data,
                line.get('char', ''),
                ep
            )
            if actor_id:
                active_actor_ids.add(actor_id)

        max_time = 600.0
        if processed_lines:
            max_time = max(float(line.get('e', 0.0)) for line in processed_lines)
            max_time += 600.0

        rpp = ['<REAPER_PROJECT 0.1 "7.0"']

        if use_regions:
            for i, line in enumerate(processed_lines):
                start = float(line.get('s', 0.0))
                end = float(line.get('e', 0.0))

                char = line.get('char', '')
                label = (
                    f"{self._escape_rpp_text(char)}: "
                    f"{self._escape_rpp_text(line.get('text', ''))}"
                )

                actor_id = get_actor_for_character(self.project_data, char, ep)
                actor = actors.get(actor_id, {}) if actor_id else {}
                color_int = self._hex_to_reaper_color(actor.get("color", ""))

                rpp.append(
                    f'  MARKER {i + 1} {start:.4f} "{label}" 1 {color_int}'
                )
                rpp.append(
                    f'  MARKER {i + 1} {end:.4f} "" 1 {color_int}'
                )

        if use_video and video_path:
            rpp.append('   <TRACK')
            rpp.append('    NAME "VIDEO"')
            rpp.append('     <ITEM')
            rpp.append('      POSITION 0.0')
            rpp.append('      LOOP 0')
            rpp.append(f'      LENGTH {max_time:.4f}')
            rpp.append('       <SOURCE VIDEO')
            rpp.append(f'        FILE "{self._escape_rpp_text(video_path)}"')
            rpp.append('       >')
            rpp.append('     >')
            rpp.append('   >')

        sorted_actors = sorted(
            (
                actors[actor_id]
                for actor_id in active_actor_ids
                if actor_id in actors
            ),
            key=lambda actor: actor.get('name', '').lower()
        )

        for actor in sorted_actors:
            color_int = self._hex_to_reaper_color(actor.get('color', ''))
            rpp.append('   <TRACK')
            rpp.append(f'    NAME "{self._escape_rpp_text(actor.get("name", ""))}"')
            rpp.append(f'    PEAKCOL {color_int}')
            rpp.append('    REC 0')
            rpp.append('    SHOWINMIX 1')
            rpp.append('   >')

        rpp.append('>')
        return '\n'.join(rpp)

    def get_reaper_rpp_preview(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        merge_cfg: Optional[Dict[str, Any]] = None,
        video_path: Optional[str] = None,
        use_video: bool = False,
        use_regions: bool = True
    ) -> Dict[str, Any]:
        """Return a user-facing preview summary for RPP export."""
        if merge_cfg is None:
            merge_cfg = self.project_data.get("replica_merge_config", {})

        processed_lines = self.process_merge_logic(lines, merge_cfg)
        actors = self.project_data.get("actors", {})

        active_actor_ids: Set[str] = set()
        invalid_lines = 0
        sample_regions: List[str] = []

        for line in processed_lines:
            start = float(line.get('s', 0.0))
            end = float(line.get('e', 0.0))
            if end <= start:
                invalid_lines += 1

            char = line.get('char', '')
            actor_id = get_actor_for_character(self.project_data, char, ep)
            if actor_id:
                active_actor_ids.add(actor_id)

            if use_regions and len(sample_regions) < 5:
                label = (
                    f"{self._escape_rpp_text(char)}: "
                    f"{self._escape_rpp_text(line.get('text', ''))}"
                )
                sample_regions.append(f"{start:.2f}-{end:.2f}  {label}")

        active_actor_names = sorted(
            actors.get(actor_id, {}).get("name", actor_id)
            for actor_id in active_actor_ids
        )

        return {
            "regions": len(processed_lines) if use_regions else 0,
            "tracks": len(active_actor_ids),
            "actors": active_actor_names,
            "video": bool(use_video and video_path),
            "video_path": video_path if use_video and video_path else None,
            "invalid_lines": invalid_lines,
            "sample_regions": sample_regions,
        }

    # ==========================================================================
    # Batch export
    # ==========================================================================

    def export_batch(
        self,
        episodes: Dict[str, str],
        get_lines_callback,
        do_html: bool = True,
        do_xls: bool = False,
        do_docx: bool = False,
        folder: str = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[bool, str]:
        """Export several episodes in one batch."""
        if not folder:
            return False, translate_source("Папка для экспорта не указана")

        cfg = self.project_data["export_config"]
        merge_cfg = self.project_data.get("replica_merge_config", {})
        project_name = self.project_data.get('project_name', 'Project')
        exported_count = 0
        total_episodes = len(episodes)

        try:
            # Collect all episodes for the Excel summary
            all_episodes_data = {}
            if do_xls:
                for ep, path in episodes.items():
                    lines = get_lines_callback(ep)
                    if lines:
                        all_episodes_data[ep] = self.process_merge_logic(
                            lines,
                            merge_cfg
                        )

            for idx, (ep, path) in enumerate(episodes.items(), 1):
                lines = get_lines_callback(ep)
                if not lines:
                    if progress_callback:
                        progress_callback(
                            idx,
                            total_episodes,
                            f"{translate_source('Пропуск серии')} {ep}..."
                        )
                    continue

                if progress_callback:
                    progress_callback(
                        idx - 1,
                        total_episodes,
                        f"{translate_source('Экспорт серии')} {ep}..."
                    )

                if do_html:
                    filename = f"{project_name} - Ep{ep}.html"
                    filepath = os.path.join(folder, filename)
                    html = self.generate_html(
                        ep,
                        self.process_merge_logic(lines, merge_cfg),
                        cfg,
                        cfg.get('highlight_ids_export'),
                        layout_type=cfg.get('layout_type', 'Таблица'),
                        is_editable=cfg.get('allow_edit', True)
                    )
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html)
                    exported_count += 1

                if do_docx and DOCX_AVAILABLE:
                    filename = f"{project_name} - Ep{ep}.docx"
                    filepath = os.path.join(folder, filename)
                    document = self.create_docx_document(
                        {
                            ep: self.process_merge_logic(lines, merge_cfg)
                        },
                        cfg
                    )
                    document.save(filepath)
                    exported_count += 1

            if do_xls and EXCEL_AVAILABLE and all_episodes_data:
                filename = f"{project_name} - {translate_source('Все серии')}.xlsx"
                filepath = os.path.join(folder, filename)
                first_ep = next(iter(all_episodes_data))
                first_lines = all_episodes_data[first_ep]
                success, _ = self.export_to_excel(
                    first_ep, first_lines, cfg, filepath,
                    all_episodes_data, merge_cfg
                )
                if success:
                    exported_count += 1

            # Advance progress to completion
            if progress_callback:
                progress_callback(total_episodes, total_episodes, translate_source("Готово!"))

            # Open the folder
            if exported_count > 0 and cfg.get('open_auto', True):
                if sys.platform == 'darwin':
                    os.system(f'open "{folder}"')
                else:
                    os.startfile(folder)

            return True, f"{translate_source('Экспортировано файлов:')} {exported_count}"

        except Exception as e:
            logger.error(f"Batch export error: {e}")
            return False, f"{translate_source('Ошибка пакетного экспорта:')} {e}"
