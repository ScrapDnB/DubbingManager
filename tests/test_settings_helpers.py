"""Tests for settings dialog helper functions."""

from PySide6.QtWidgets import QApplication

from config.constants import DEFAULT_DOCX_IMPORT_CONFIG
from ui.dialogs.settings_helpers import (
    check_box,
    double_spin,
    hint_label,
    int_spin,
    parse_separators,
)


def test_parse_separators_uses_values_or_defaults():
    assert parse_separators("a, b,,c") == ["a", "b", "c"]
    assert parse_separators(" , ") == DEFAULT_DOCX_IMPORT_CONFIG["time_separators"]


def test_widget_factories_create_expected_controls():
    app = QApplication.instance() or QApplication([])
    hint = hint_label("hello")
    checkbox = check_box("flag", True)
    spin = int_spin(1, 10, 5)
    dbl = double_spin(0.0, 2.0, 1.5, step=0.5, decimals=2)

    assert hint.wordWrap() is True
    assert checkbox.isChecked() is True
    assert spin.value() == 5
    assert dbl.value() == 1.5
