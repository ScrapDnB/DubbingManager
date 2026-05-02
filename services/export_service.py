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
                use_color, is_highlighted, actor
            )

            text_html = self._format_text_html(line, is_editable)

            if layout_type == "Таблица":
                html += self._build_table_row(
                    line, actor, text_html, bg_color, h_class, cfg,
                    is_first=idx == 0, is_last=idx == len(processed) - 1
                )
            else:
                html += self._build_scenario_row(
                    line, actor, text_html, bg_color, border_col, h_class
                )

        return html + "</body></html>"

    def _get_js_for_mode(self, is_editable: bool) -> str:
        """Return js for mode."""
        if is_editable:
            return self._get_editable_js()
        return self._get_static_css()

    def _get_html_header(self, js: str, cfg: Dict[str, Any]) -> str:
        """Return the HTML document header."""
        return f"""<html><head><meta charset='utf-8'>{js}<style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            padding: 50px 10%;
            background: #fdfdfd;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            background: white;
        }}
        td, th {{
            border: 1px solid #ddd;
            padding: 12px;
            vertical-align: top;
            overflow-wrap: break-word;
        }}
        .t {{
            width: 90px;
            font-family: monospace;
            font-size: {cfg.get('f_time', 12)}px;
            color: #666;
        }}
        .c {{
            width: 160px;
            font-weight: bold;
            font-size: {cfg.get('f_char', 14)}px;
        }}
        .a {{
            width: 160px;
            font-style: italic;
            font-size: {cfg.get('f_actor', 14)}px;
        }}
        .txt {{
            font-size: {cfg.get('f_text', 16)}px;
            line-height: 1.5;
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
        actor: Dict[str, Any]
    ) -> tuple:
        """Return colors for an export row."""
        if use_color and is_highlighted:
            bg_color = hex_to_rgba_string(actor['color'], 0.22)
            border_col = actor['color']
        else:
            bg_color = "#ffffff"
            border_col = "#eee"
        return bg_color, border_col

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

    def _build_table_row(
        self,
        line: Dict[str, Any],
        actor: Dict[str, Any],
        text_html: str,
        bg_color: str,
        h_class: str,
        cfg: Dict[str, Any],
        is_first: bool,
        is_last: bool
    ) -> str:
        """Build one table export row."""
        columns = []
        if cfg.get('col_tc', True):
            timing = self._format_export_timing(line, cfg)
            columns.append((translate_source("Время"), "t", escape(str(timing))))
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
        row = (
            f"<tr style='background-color:{bg_color}' "
            f"class='{h_class}'>"
            f"{cells}</tr>"
        )

        if is_first:
            headers = "".join(
                f"<th>{header}</th>"
                for header, _css_class, _value in columns
            )
            header = (
                "<table><thead><tr>"
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
        h_class: str
    ) -> str:
        """Build scenario row."""
        char = escape(str(line.get('char', '')))
        s_raw = escape(str(line.get('s_raw', '')))
        actor_name = escape(str(actor.get('name', '-')))
        return (
            f"<div class='line-container {h_class}' "
            f"style='background-color:{bg_color}; "
            f"border-left-color:{border_col}'>"
            f"<div class='meta'>"
            f"<span class='c'><b>{char}</b></span>"
            f" <span class='t'>[{s_raw}]</span>"
            f" <span class='a'><i>({actor_name})</i></span>"
            f"</div>"
            f"<div class='txt'>{text_html}</div></div>"
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

    def _get_times_font(self, size: float = 14.0, bold: bool = False, italic: bool = False) -> Font:
        """Return times font."""
        return Font(name='Times New Roman', size=size, bold=bold, italic=italic, charset=204)

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
        border: Optional[Border] = None
    ):
        """Apply cell styling."""
        cell.font = self._get_times_font(size=font_size)
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
                color_hex = stats['color'].replace('#', '')
                fill_color = color_hex if color_hex else 'FFFFFF'
            else:
                fill_color = 'FFFFFF'

            # Actor-name cell
            name_cell = ws.cell(row=row_num, column=1, value=actor_name)
            self._apply_cell_styling(name_cell, font_size=14.0, fill_color=fill_color, border=thin_border)

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
            'Номер': 8.66,
            'Таймкод': 13.0,  # Reduced so timing wraps to two lines
            'Персонаж': 28.83,
            'Актёр': 29.5,
            'Реплика': 92.33
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
                color_hex = actor.get('color', '#FFFFFF').replace('#', '')
            else:
                color_hex = 'FFFFFF'

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
                        all_episodes_data[ep] = lines

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
            if exported_count > 0:
                if sys.platform == 'darwin':
                    os.system(f'open "{folder}"')
                else:
                    os.startfile(folder)

            return True, f"{translate_source('Экспортировано файлов:')} {exported_count}"

        except Exception as e:
            logger.error(f"Batch export error: {e}")
            return False, f"{translate_source('Ошибка пакетного экспорта:')} {e}"
