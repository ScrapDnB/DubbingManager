"""Lightweight JSON-based interface localization."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "ru"
SUPPORTED_LANGUAGES = {
    "ru": "Русский",
    "en": "English",
}


class I18n:
    """Load UI strings from editable JSON files."""

    def __init__(self) -> None:
        self._language = DEFAULT_LANGUAGE
        self._cache: Dict[str, Dict[str, str]] = {}
        self._source_cache: Dict[str, Dict[str, str]] = {}
        self._base_dir = Path(__file__).resolve().parents[1] / "resources" / "i18n"

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        self._language = language

    def available_languages(self) -> Dict[str, str]:
        return dict(SUPPORTED_LANGUAGES)

    def tr(self, key: str, **kwargs: Any) -> str:
        value = self._catalog(self._language).get(key)
        if value is None and self._language != DEFAULT_LANGUAGE:
            value = self._catalog(DEFAULT_LANGUAGE).get(key)
        if value is None:
            value = key

        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, IndexError, ValueError) as exc:
                logger.warning("Failed to format translation %s: %s", key, exc)
        return value

    def translate_source(self, text: str) -> str:
        """Translate a literal source UI string when a source map entry exists."""
        if self._language == DEFAULT_LANGUAGE or not text:
            return text
        return self._source_catalog(self._language).get(text, text)

    def _catalog(self, language: str) -> Dict[str, str]:
        if language in self._cache:
            return self._cache[language]

        path = self._base_dir / f"{language}.json"
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            logger.warning("Translation file not found: %s", path)
            data = {}
        except json.JSONDecodeError as exc:
            logger.warning("Invalid translation file %s: %s", path, exc)
            data = {}

        if not isinstance(data, dict):
            logger.warning("Translation file %s must contain a JSON object", path)
            data = {}

        self._cache[language] = {
            str(key): str(value)
            for key, value in data.items()
        }
        return self._cache[language]

    def _source_catalog(self, language: str) -> Dict[str, str]:
        if language in self._source_cache:
            return self._source_cache[language]

        path = self._base_dir / f"source_{language}.json"
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError as exc:
            logger.warning("Invalid source translation file %s: %s", path, exc)
            data = {}

        if not isinstance(data, dict):
            data = {}

        self._source_cache[language] = {
            str(key): str(value)
            for key, value in data.items()
        }
        return self._source_cache[language]


i18n = I18n()


def set_language(language: str) -> None:
    i18n.set_language(language)


def get_language() -> str:
    return i18n.language


def available_languages() -> Dict[str, str]:
    return i18n.available_languages()


def tr(key: str, **kwargs: Any) -> str:
    return i18n.tr(key, **kwargs)


def translate_source(text: str) -> str:
    return i18n.translate_source(text)


def translate_widget_tree(root: Any) -> None:
    """Translate static widget texts under a Qt widget tree."""
    if get_language() == DEFAULT_LANGUAGE or root is None:
        return

    from PySide6.QtWidgets import (
        QAbstractButton,
        QGroupBox,
        QLabel,
        QLineEdit,
        QTabWidget,
        QTableWidget,
        QTreeWidget,
        QWidget,
    )

    widgets = [root]
    if isinstance(root, QWidget):
        widgets.extend(root.findChildren(QWidget))

    for widget in widgets:
        if hasattr(widget, "windowTitle") and hasattr(widget, "setWindowTitle"):
            title = widget.windowTitle()
            translated = translate_source(title)
            if translated != title:
                widget.setWindowTitle(translated)

        if hasattr(widget, "toolTip") and hasattr(widget, "setToolTip"):
            tooltip = widget.toolTip()
            translated = translate_source(tooltip)
            if translated != tooltip:
                widget.setToolTip(translated)

        if isinstance(widget, QLabel):
            text = widget.text()
            translated = translate_source(text)
            if translated != text:
                widget.setText(translated)
        elif isinstance(widget, QAbstractButton):
            text = widget.text()
            translated = translate_source(text)
            if translated != text:
                widget.setText(translated)
        elif isinstance(widget, QGroupBox):
            title = widget.title()
            translated = translate_source(title)
            if translated != title:
                widget.setTitle(translated)
        elif isinstance(widget, QLineEdit):
            placeholder = widget.placeholderText()
            translated = translate_source(placeholder)
            if translated != placeholder:
                widget.setPlaceholderText(translated)
        elif isinstance(widget, QTabWidget):
            for index in range(widget.count()):
                text = widget.tabText(index)
                translated = translate_source(text)
                if translated != text:
                    widget.setTabText(index, translated)
        elif isinstance(widget, QTableWidget):
            for index in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(index)
                if item is not None:
                    text = item.text()
                    translated = translate_source(text)
                    if translated != text:
                        item.setText(translated)
        elif isinstance(widget, QTreeWidget):
            item = widget.headerItem()
            if item is not None:
                for index in range(widget.columnCount()):
                    text = item.text(index)
                    translated = translate_source(text)
                    if translated != text:
                        item.setText(index, translated)
