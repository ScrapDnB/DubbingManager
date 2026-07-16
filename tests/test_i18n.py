"""Tests for the shared Widgets/QML translation catalog."""

from utils.i18n import JsonSourceTranslator, set_language, translate_source


def test_source_catalog_translates_qml_literals_and_falls_back():
    set_language("en")
    try:
        assert translate_source("Проект") == "Project"
        assert translate_source("Строка без перевода") == "Строка без перевода"
    finally:
        set_language("ru")


def test_qt_translator_preserves_unknown_placeholder_strings():
    set_language("en")
    try:
        translator = JsonSourceTranslator()
        assert translator.translate("Qt", "Value %1 of %2") == "Value %1 of %2"
    finally:
        set_language("ru")
