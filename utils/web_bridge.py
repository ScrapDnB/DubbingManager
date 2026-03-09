"""Мост между JS и Python для веб-компонентов"""

from PySide6.QtCore import QObject, Slot
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class WebBridge(QObject):
    """Мост между JavaScript и Python для редактирования текста"""

    def __init__(self, main_app: Any, parent=None):
        super().__init__(parent)
        self.main_app = main_app

    @Slot(int, int)
    def sync_scroll_index(self, index: int, total: int) -> None:
        """Обновляет счетчик в окне предпросмотра при прокрутке"""
        if self.main_app and hasattr(self.main_app, 'preview_window'):
            self.main_app.preview_window.update_counter_label(index, total)

    @Slot(str, str)
    def update_text(self, line_id: str, new_text: str) -> None:
        """Принимает ID строки и новый текст из HTML"""
        try:
            lid = int(line_id)
            ep = self.main_app.ep_combo.currentData()

            loaded = self.main_app.data.get("loaded_episodes", {})
            ep_key = None
            if ep in loaded:
                ep_key = ep
            elif str(ep) in loaded:
                ep_key = str(ep)

            updated = False
            if ep_key is not None:
                lines = loaded[ep_key]
                target = next(
                    (l for l in lines if int(l.get('id', -1)) == lid),
                    None
                )
                if target and target.get('text') != new_text:
                    target['text'] = new_text
                    updated = True

            if not updated:
                try:
                    lines = self.main_app.get_episode_lines(ep)
                    target = next(
                        (l for l in lines if int(l.get('id', -1)) == lid),
                        None
                    )
                    if target and target.get('text') != new_text:
                        target['text'] = new_text
                        if 'loaded_episodes' not in self.main_app.data:
                            self.main_app.data['loaded_episodes'] = {}
                        self.main_app.data['loaded_episodes'][str(ep)] = lines
                        updated = True
                except Exception as e:
                    logger.warning(f"Error getting episode lines: {e}")

            if updated:
                try:
                    self.main_app.set_dirty(True)
                except Exception as e:
                    logger.warning(f"Error setting dirty: {e}")

                if (
                    hasattr(self.main_app, 'preview_window') and
                    self.main_app.preview_window
                ):
                    self.main_app.preview_window._has_text_changes = True
                    try:
                        self.main_app.preview_window.update_preview()
                    except Exception as e:
                        logger.warning(f"Error updating preview: {e}")

                    logger.debug(f"Updated line {lid}: {new_text}")
                
                # Обновляем флаг изменений текста
                ep = self.main_app.ep_combo.currentData()
                if ep:
                    if not hasattr(self.main_app, 'text_changes'):
                        self.main_app.text_changes = {}
                    self.main_app.text_changes[ep] = True
                    try:
                        self.main_app.update_save_ass_button()
                    except Exception as e:
                        logger.warning(f"Error updating save button: {e}")
        except Exception as e:
            logger.error(f"Error updating text: {e}")