"""Контроллер экспорта данных"""

from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QUrl
from typing import Dict, List, Any, Optional, Tuple

import os
import logging
from copy import deepcopy

from services import ExportService, ScriptTextService
from config.constants import DEFAULT_EXPORT_CONFIG, DEFAULT_REPLICA_MERGE_CONFIG

logger = logging.getLogger(__name__)


class ExportController:
    """
    Контроллер для экспорта данных.

    Отвечает за:
    - Экспорт в HTML
    - Экспорт в Excel
    - Экспорт в Reaper RPP
    - Пакетный экспорт
    """

    def __init__(
        self,
        data_ref: Dict[str, Any],
        episode_service: Any,
        on_dirty_callback: Optional[callable] = None
    ):
        self.data_ref = data_ref
        self.episode_service = episode_service
        self.on_dirty_callback = on_dirty_callback
        self.script_text_service = ScriptTextService()

    def _get_episode_lines(self, ep: str) -> List[Dict[str, Any]]:
        """Получить реплики эпизода только из рабочего текста проекта."""
        working_lines = self.script_text_service.load_episode_lines(
            self.data_ref,
            ep
        )
        if working_lines:
            self.data_ref.setdefault("loaded_episodes", {})[ep] = working_lines
            return working_lines

        source_path = self.data_ref.get("episodes", {}).get(ep, "")
        if os.path.splitext(source_path or "")[1].lower() in {'.ass', '.srt'}:
            self.data_ref.get("loaded_episodes", {}).pop(ep, None)

        return []

    def _missing_working_text_message(self, ep: str) -> str:
        """Сообщение для серии без рабочего текста."""
        return (
            f"Для серии {ep} не найден рабочий текст. "
            "Создайте его из субтитров в окне «Файлы проекта»."
        )

    def _mark_dirty(self) -> None:
        """Пометка проекта как изменённого"""
        if self.on_dirty_callback:
            self.on_dirty_callback()

    def export_to_html(
        self,
        ep: str,
        save_path: str,
        highlight_ids: Optional[List[str]] = None,
        is_editable: bool = True
    ) -> Tuple[bool, str]:
        """
        Экспорт в HTML

        Args:
            ep: номер эпизода
            save_path: путь сохранения
            highlight_ids: ID актёров для подсветки
            is_editable: редактируемый ли HTML

        Returns:
            Tuple[success, message]
        """
        try:
            export_config = self.data_ref.get(
                "export_config",
                deepcopy(DEFAULT_EXPORT_CONFIG)
            )
            merge_config = self.data_ref.get(
                "replica_merge_config",
                deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
            )

            lines = self._get_episode_lines(ep)

            if not lines:
                return False, self._missing_working_text_message(ep)

            effective_highlight_ids = (
                highlight_ids
                if highlight_ids is not None
                else export_config.get('highlight_ids_export')
            )

            export_service = ExportService(self.data_ref)
            processed = export_service.process_merge_logic(lines, merge_config)

            html = export_service.generate_html(
                ep=ep,
                processed=processed,
                cfg=export_config,
                highlight_ids=effective_highlight_ids,
                layout_type=export_config.get('layout_type', 'Таблица'),
                is_editable=is_editable
            )

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"HTML exported to {save_path}")
            return True, f"Экспортировано в {save_path}"

        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            return False, f"Ошибка экспорта: {e}"

    def export_to_excel(
        self,
        ep: str,
        save_path: str,
        all_episodes: bool = False
    ) -> Tuple[bool, str]:
        """
        Экспорт в Excel

        Args:
            ep: номер эпизода
            save_path: путь сохранения
            all_episodes: экспортировать все эпизоды или только текущий

        Returns:
            Tuple[success, message]
        """
        try:
            export_config = self.data_ref.get(
                "export_config",
                deepcopy(DEFAULT_EXPORT_CONFIG)
            )
            merge_config = self.data_ref.get(
                "replica_merge_config",
                deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
            )

            if all_episodes:
                # Собираем данные по всем эпизодам
                episodes_data = {}
                for ep_num in self.data_ref.get("episodes", {}).keys():
                    lines = self._get_episode_lines(ep_num)
                    if lines:
                        export_service = ExportService(self.data_ref)
                        episodes_data[ep_num] = export_service.process_merge_logic(lines, merge_config)
                if not episodes_data:
                    return False, (
                        "Не найдено рабочих текстов для экспорта. "
                        "Создайте их из субтитров в окне «Файлы проекта»."
                    )
            else:
                lines = self._get_episode_lines(ep)
                if not lines:
                    return False, self._missing_working_text_message(ep)
                export_service = ExportService(self.data_ref)
                episodes_data = {ep: export_service.process_merge_logic(lines, merge_config)}

            export_service = ExportService(self.data_ref)
            wb = export_service.create_excel_book(episodes_data, export_config)

            wb.save(save_path)

            logger.info(f"Excel exported to {save_path}")
            return True, f"Экспортировано в {save_path}"

        except ImportError:
            return False, "openpyxl не установлен"
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return False, f"Ошибка экспорта: {e}"

    def export_to_reaper_rpp(
        self,
        ep: str,
        save_path: str
    ) -> Tuple[bool, str]:
        """
        Экспорт в Reaper RPP

        Args:
            ep: номер эпизода
            save_path: путь сохранения

        Returns:
            Tuple[success, message]
        """
        try:
            lines = self._get_episode_lines(ep)

            if not lines:
                return False, self._missing_working_text_message(ep)

            export_service = ExportService(self.data_ref)
            rpp_content = export_service.generate_reaper_rpp(
                ep,
                lines,
                merge_cfg=self.data_ref.get("replica_merge_config", {})
            )

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(rpp_content)

            logger.info(f"Reaper RPP exported to {save_path}")
            return True, f"Экспортировано в {save_path}"

        except Exception as e:
            logger.error(f"Reaper export failed: {e}")
            return False, f"Ошибка экспорта: {e}"

    def run_unified_export(
        self,
        ep: str,
        export_html: bool = True,
        export_xls: bool = False,
        all_episodes: bool = False,
        parent_widget=None
    ) -> Tuple[bool, str]:
        """
        Универсальный экспорт

        Args:
            ep: номер эпизода
            export_html: экспортировать в HTML
            export_xls: экспортировать в Excel
            all_episodes: все эпизоды или только текущий
            parent_widget: родительский виджет для диалогов

        Returns:
            Tuple[success, message]
        """
        results = []

        # Определяем путь сохранения
        default_name = f"Export_{ep}" if not all_episodes else "Export_All"

        if export_html:
            path, _ = QFileDialog.getSaveFileName(
                parent_widget,
                "Сохранить HTML",
                f"{default_name}.html",
                "HTML Files (*.html)"
            )
            if path:
                success, msg = self.export_to_html(ep, path)
                results.append(("HTML", success, msg))

        if export_xls:
            path, _ = QFileDialog.getSaveFileName(
                parent_widget,
                "Сохранить Excel",
                f"{default_name}.xlsx",
                "Excel Files (*.xlsx)"
            )
            if path:
                success, msg = self.export_to_excel(ep, path, all_episodes)
                results.append(("Excel", success, msg))

        # Формируем итоговое сообщение
        if not results:
            return False, "Экспорт не выполнен"

        successes = sum(1 for _, success, _ in results if success)
        failures = len(results) - successes

        if failures == 0:
            return True, f"Успешно экспортировано: {successes}"
        elif successes > 0:
            return True, f"Экспортировано: {successes}, ошибок: {failures}"
        else:
            return False, f"Ошибок: {failures}"

    def get_export_preview(
        self,
        ep: str,
        highlight_ids: Optional[List[str]] = None
    ) -> str:
        """
        Получение превью экспорта

        Args:
            ep: номер эпизода
            highlight_ids: ID актёров для подсветки

        Returns:
            HTML для превью
        """
        export_config = self.data_ref.get(
            "export_config",
            deepcopy(DEFAULT_EXPORT_CONFIG)
        )
        merge_config = self.data_ref.get(
            "replica_merge_config",
            deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
        )

        lines = self._get_episode_lines(ep)

        if not lines:
            return (
                "<html><body>"
                f"<h3>{self._missing_working_text_message(ep)}</h3>"
                "</body></html>"
            )

        effective_highlight_ids = (
            highlight_ids
            if highlight_ids is not None
            else export_config.get('highlight_ids_export')
        )

        export_service = ExportService(self.data_ref)
        processed = export_service.process_merge_logic(lines, merge_config)

        return export_service.generate_html(
            ep=ep,
            processed=processed,
            cfg=export_config,
            highlight_ids=effective_highlight_ids,
            layout_type=export_config.get('layout_type', 'Таблица'),
            is_editable=False
        )
