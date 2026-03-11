"""Сервис для экспорта данных"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from utils.helpers import hex_to_rgba_string

logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("openpyxl not available - Excel export disabled")


class ExportService:
    """Сервис для экспорта в различные форматы: HTML, Excel, Reaper"""

    def __init__(self, project_data: Dict[str, Any]):
        self.project_data = project_data

    def process_merge_logic(
        self,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Логика слияния реплик"""
        p_short = cfg.get('p_short', 0.5)
        p_long = cfg.get('p_long', 2.0)
        fps = cfg.get('fps', 25.0)
        # Конвертируем merge_gap из кадров в секунды
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

        # Добавляем source_ids и source_texts
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
        """Генерация HTML"""
        js = self._get_js_for_mode(is_editable)
        html = self._get_html_header(js, cfg)

        project_name = self.project_data.get('project_name', 'Project')
        html += f"<h1>{project_name} - Серия {ep}</h1>"

        actors = self.project_data.get("actors", {})
        global_map = self.project_data.get("global_map", {})

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
            # Валидация данных реплики
            if 'char' not in line:
                logger.warning(f"Skipping line without 'char' field: {line}")
                continue
            if 'text' not in line:
                logger.warning(f"Skipping line without 'text' field: {line}")
                continue

            aid = global_map.get(line['char'])
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
                    line, actor, text_html, bg_color, h_class,
                    is_first=idx == 0, is_last=idx == len(processed) - 1
                )
            else:
                html += self._build_scenario_row(
                    line, actor, text_html, bg_color, border_col, h_class
                )

        return html + "</body></html>"

    def _get_js_for_mode(self, is_editable: bool) -> str:
        """Получение JavaScript для режима редактирования"""
        if is_editable:
            return self._get_editable_js()
        return self._get_static_css()

    def _get_html_header(self, js: str, cfg: Dict[str, Any]) -> str:
        """Получение заголовка HTML"""
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
        """JavaScript для редактируемого HTML"""
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
        """CSS для статичного HTML"""
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
        """Получение цветов для строки"""
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
        """Форматирование текста реплики"""
        text_html = ""

        if 'parts' in line:
            for part in line['parts']:
                if part['sep']:
                    text_html += f"<span class='sep'>{part['sep']}</span>"
                if is_editable:
                    text_html += (
                        f"<span id='{part['id']}' "
                        f"class='edit-span' "
                        f"contenteditable='true' "
                        f"onblur='onBlur(this)' "
                        f"onkeypress='onKeyPress(event, this)'>"
                        f"{part['text']}</span>"
                    )
                else:
                    text_html += f"<span>{part['text']}</span>"
        else:
            text_html = line['text']

        return text_html

    def _build_table_row(
        self,
        line: Dict[str, Any],
        actor: Dict[str, Any],
        text_html: str,
        bg_color: str,
        h_class: str,
        is_first: bool,
        is_last: bool
    ) -> str:
        """Построение строки таблицы"""
        row = (
            f"<tr style='background-color:{bg_color}' "
            f"class='{h_class}'>"
            f"<td class='t'>{line['s_raw']}</td>"
            f"<td class='c'>{line['char']}</td>"
            f"<td class='a'>{actor['name']}</td>"
            f"<td class='txt'>{text_html}</td></tr>"
        )

        if is_first:
            header = (
                "<table><thead><tr>"
                "<th>Время</th><th>Персонаж</th>"
                "<th>Актер</th><th>Текст</th>"
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
        """Построение строки сценария"""
        return (
            f"<div class='line-container {h_class}' "
            f"style='background-color:{bg_color}; "
            f"border-left-color:{border_col}'>"
            f"<div class='meta'>"
            f"<span class='c'><b>{line['char']}</b></span>"
            f" <span class='t'>[{line['s_raw']}]</span>"
            f" <span class='a'><i>({actor['name']})</i></span>"
            f"</div>"
            f"<div class='txt'>{text_html}</div></div>"
        )

    # ==========================================================================
    # Excel экспорт
    # ==========================================================================

    def create_excel_book(
        self,
        ep: str,
        processed: List[Dict[str, Any]],
        cfg: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Создание Excel книги"""
        if not EXCEL_AVAILABLE:
            raise ImportError("openpyxl not available")

        if cfg is None:
            cfg = self.project_data["export_config"]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["№", "Таймкод", "Персонаж", "Актер", "Текст"])

        use_color = cfg.get('use_color', True)
        highlight_ids = cfg.get('highlight_ids_export')
        all_actor_ids = set(self.project_data["actors"].keys())

        is_full_filter = (
            highlight_ids is not None and
            set(highlight_ids) == all_actor_ids
        )
        effective_filter = (
            None
            if (highlight_ids is None or is_full_filter)
            else set(highlight_ids)
        )

        for i, line in enumerate(processed, 2):
            aid = self.project_data["global_map"].get(line['char'])
            actor = self.project_data["actors"].get(
                aid, {"name": "-", "color": "#FFFFFF"}
            )

            ws.append([
                i-1,
                line['s_raw'],
                line['char'],
                actor['name'],
                line['text']
            ])

            if use_color:
                is_highlighted = (
                    effective_filter is None or
                    aid in effective_filter
                )
                if is_highlighted:
                    color = actor['color'].replace("#", "")
                else:
                    color = "FFFFFF"
            else:
                color = "FFFFFF"

            fill = PatternFill(
                start_color=color,
                end_color=color,
                fill_type="solid"
            )

            for col in range(1, 6):
                cell = ws.cell(row=i, column=col)
                cell.fill = fill
                cell.alignment = Alignment(
                    vertical='top',
                    wrap_text=(col == 5)
                )

        return wb

    def export_to_excel(
        self,
        ep: str,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        save_path: str
    ) -> Tuple[bool, str]:
        """
        Экспорт в Excel файл

        Returns:
            Tuple[success, message]
        """
        if not EXCEL_AVAILABLE:
            return False, "openpyxl не установлен"

        try:
            processed = self.process_merge_logic(lines, cfg)
            wb = self.create_excel_book(ep, processed, cfg)
            wb.save(save_path)
            return True, f"Excel сохранён: {save_path}"
        except Exception as e:
            logger.error(f"Excel export error: {e}")
            return False, f"Ошибка экспорта: {e}"

    # ==========================================================================
    # Пакетный экспорт
    # ==========================================================================

    def export_batch(
        self,
        episodes: Dict[str, str],
        get_lines_callback,
        do_html: bool = True,
        do_xls: bool = False,
        folder: str = None
    ) -> Tuple[bool, str]:
        """
        Пакетный экспорт нескольких эпизодов

        Args:
            episodes: словарь {ep_num: path}
            get_lines_callback: функция для получения реплик эпизода
            do_html: экспортировать в HTML
            do_xls: экспортировать в Excel
            folder: папка для сохранения

        Returns:
            Tuple[success, message]
        """
        if not folder:
            return False, "Папка для экспорта не указана"

        cfg = self.project_data["export_config"]
        merge_cfg = self.project_data.get("replica_merge_config", {})
        project_name = self.project_data.get('project_name', 'Project')
        exported_count = 0

        try:
            for ep, path in episodes.items():
                lines = get_lines_callback(ep)
                if not lines:
                    continue

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

                if do_xls and EXCEL_AVAILABLE:
                    filename = f"{project_name} - Ep{ep}.xlsx"
                    filepath = os.path.join(folder, filename)
                    success, _ = self.export_to_excel(
                        ep, lines, merge_cfg, filepath
                    )
                    if success:
                        exported_count += 1

            # Открыть папку
            if exported_count > 0:
                if sys.platform == 'darwin':
                    os.system(f'open "{folder}"')
                else:
                    os.startfile(folder)

            return True, f"Экспортировано файлов: {exported_count}"

        except Exception as e:
            logger.error(f"Batch export error: {e}")
            return False, f"Ошибка пакетного экспорта: {e}"
