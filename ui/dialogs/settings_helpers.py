"""Small helpers for settings dialog widgets and parsing."""

from copy import deepcopy
from typing import Any, List

from PySide6.QtWidgets import QLabel, QCheckBox, QDoubleSpinBox, QSpinBox

from config.constants import DEFAULT_DOCX_IMPORT_CONFIG


def parse_separators(text: str) -> List[str]:
    """Parse comma-separated DOCX time separators."""
    separators = [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]
    return separators or deepcopy(
        DEFAULT_DOCX_IMPORT_CONFIG["time_separators"]
    )


def hint_label(text: str) -> QLabel:
    """Create a subdued word-wrapped hint label."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #666; font-size: 11px;")
    return label


def check_box(text: str, checked: bool) -> QCheckBox:
    """Create a checkbox with normalized checked state."""
    checkbox = QCheckBox(text)
    checkbox.setChecked(bool(checked))
    return checkbox


def int_spin(minimum: int, maximum: int, value: Any) -> QSpinBox:
    """Create an integer spin box."""
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(int(value))
    return spin


def double_spin(
    minimum: float,
    maximum: float,
    value: Any,
    step: float = 1.0,
    decimals: int = 1
) -> QDoubleSpinBox:
    """Create a double spin box."""
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setValue(float(value))
    return spin
