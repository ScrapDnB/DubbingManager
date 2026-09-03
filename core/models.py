"""Typed views of the canonical configuration and project data schemas."""

from copy import deepcopy
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import logging
import re

from config.constants import (
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    EXPORT_LAYOUT_TYPES,
    PROMPTER_FLOAT_LIMITS,
    PROMPTER_INT_LIMITS,
    PROMPTER_LAYOUT_TYPES,
)

logger = logging.getLogger(__name__)


def _validate_hex_color(color: str, field_name: str) -> None:
    """Validate hex color."""
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError(f"Invalid hex color for {field_name}: {color}")


@dataclass
class PrompterColors:
    """Prompter Colors class."""
    bg: str = DEFAULT_PROMPTER_CONFIG["colors"]["bg"]
    active_text: str = DEFAULT_PROMPTER_CONFIG["colors"]["active_text"]
    inactive_text: str = DEFAULT_PROMPTER_CONFIG["colors"]["inactive_text"]
    tc: str = DEFAULT_PROMPTER_CONFIG["colors"]["tc"]
    actor: str = DEFAULT_PROMPTER_CONFIG["colors"]["actor"]
    header_bg: str = DEFAULT_PROMPTER_CONFIG["colors"]["header_bg"]
    header_text: str = DEFAULT_PROMPTER_CONFIG["colors"]["header_text"]
    block_border: str = DEFAULT_PROMPTER_CONFIG["colors"]["block_border"]
    page_target_highlight: str = DEFAULT_PROMPTER_CONFIG["colors"][
        "page_target_highlight"
    ]

    def __post_init__(self) -> None:
        """Post init."""
        _validate_hex_color(self.bg, "bg")
        _validate_hex_color(self.active_text, "active_text")
        _validate_hex_color(self.inactive_text, "inactive_text")
        _validate_hex_color(self.tc, "tc")
        _validate_hex_color(self.actor, "actor")
        _validate_hex_color(self.header_bg, "header_bg")
        _validate_hex_color(self.header_text, "header_text")
        _validate_hex_color(self.block_border, "block_border")
        _validate_hex_color(self.page_target_highlight, "page_target_highlight")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrompterColors':
        """From dict."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class PrompterConfig:
    """Typed teleprompter config kept in sync with the persisted schema."""

    f_tc: int = DEFAULT_PROMPTER_CONFIG["f_tc"]
    f_char: int = DEFAULT_PROMPTER_CONFIG["f_char"]
    f_actor: int = DEFAULT_PROMPTER_CONFIG["f_actor"]
    f_text: int = DEFAULT_PROMPTER_CONFIG["f_text"]
    bold_tc: bool = DEFAULT_PROMPTER_CONFIG["bold_tc"]
    bold_char: bool = DEFAULT_PROMPTER_CONFIG["bold_char"]
    bold_actor: bool = DEFAULT_PROMPTER_CONFIG["bold_actor"]
    bold_text: bool = DEFAULT_PROMPTER_CONFIG["bold_text"]
    layout_type: str = DEFAULT_PROMPTER_CONFIG["layout_type"]
    layout_font_sizes: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: deepcopy(
            DEFAULT_PROMPTER_CONFIG["layout_font_sizes"]
        )
    )
    layout_font_bold: Dict[str, Dict[str, bool]] = field(
        default_factory=lambda: deepcopy(
            DEFAULT_PROMPTER_CONFIG["layout_font_bold"]
        )
    )
    show_timecode: bool = DEFAULT_PROMPTER_CONFIG["show_timecode"]
    show_end_timecode: bool = DEFAULT_PROMPTER_CONFIG["show_end_timecode"]
    show_character: bool = DEFAULT_PROMPTER_CONFIG["show_character"]
    show_actor: bool = DEFAULT_PROMPTER_CONFIG["show_actor"]
    show_replica: bool = DEFAULT_PROMPTER_CONFIG["show_replica"]
    show_block_borders: bool = DEFAULT_PROMPTER_CONFIG["show_block_borders"]
    hide_leading_timecode_zeros: bool = DEFAULT_PROMPTER_CONFIG[
        "hide_leading_timecode_zeros"
    ]
    focus_ratio: float = DEFAULT_PROMPTER_CONFIG["focus_ratio"]
    is_mirrored: bool = DEFAULT_PROMPTER_CONFIG["is_mirrored"]
    show_header: bool = DEFAULT_PROMPTER_CONFIG["show_header"]
    port_in: int = DEFAULT_PROMPTER_CONFIG["port_in"]
    port_out: int = DEFAULT_PROMPTER_CONFIG["port_out"]
    osc_enabled: bool = DEFAULT_PROMPTER_CONFIG["osc_enabled"]
    sync_in: bool = DEFAULT_PROMPTER_CONFIG["sync_in"]
    sync_out: bool = DEFAULT_PROMPTER_CONFIG["sync_out"]
    sync_play_only: bool = DEFAULT_PROMPTER_CONFIG["sync_play_only"]
    reaper_offset_enabled: bool = DEFAULT_PROMPTER_CONFIG[
        "reaper_offset_enabled"
    ]
    reaper_offset_seconds: float = DEFAULT_PROMPTER_CONFIG[
        "reaper_offset_seconds"
    ]
    key_prev: str = DEFAULT_PROMPTER_CONFIG["key_prev"]
    key_next: str = DEFAULT_PROMPTER_CONFIG["key_next"]
    scroll_smoothness_slider: int = DEFAULT_PROMPTER_CONFIG[
        "scroll_smoothness_slider"
    ]
    scroll_delay_seconds: float = DEFAULT_PROMPTER_CONFIG[
        "scroll_delay_seconds"
    ]
    scroll_deadline_enabled: bool = DEFAULT_PROMPTER_CONFIG[
        "scroll_deadline_enabled"
    ]
    page_scroll_mode: bool = DEFAULT_PROMPTER_CONFIG["page_scroll_mode"]
    smooth_scroll_mode: bool = DEFAULT_PROMPTER_CONFIG[
        "smooth_scroll_mode"
    ]
    page_timecode_highlight_enabled: bool = DEFAULT_PROMPTER_CONFIG[
        "page_timecode_highlight_enabled"
    ]
    page_gap_prefetch_seconds: float = DEFAULT_PROMPTER_CONFIG[
        "page_gap_prefetch_seconds"
    ]
    page_gap_prefetch_delay_seconds: float = DEFAULT_PROMPTER_CONFIG[
        "page_gap_prefetch_delay_seconds"
    ]
    page_target_highlight_enabled: bool = DEFAULT_PROMPTER_CONFIG[
        "page_target_highlight_enabled"
    ]
    page_target_highlight_opacity: float = DEFAULT_PROMPTER_CONFIG[
        "page_target_highlight_opacity"
    ]
    page_target_highlight_fade_in_ms: int = DEFAULT_PROMPTER_CONFIG[
        "page_target_highlight_fade_in_ms"
    ]
    page_target_highlight_fade_ms: int = DEFAULT_PROMPTER_CONFIG[
        "page_target_highlight_fade_ms"
    ]
    page_debug_overlay: bool = DEFAULT_PROMPTER_CONFIG["page_debug_overlay"]
    show_diagnostic_controls: bool = DEFAULT_PROMPTER_CONFIG[
        "show_diagnostic_controls"
    ]
    colors: PrompterColors = field(
        default_factory=lambda: PrompterColors.from_dict(
            DEFAULT_PROMPTER_CONFIG["colors"]
        )
    )

    def __post_init__(self) -> None:
        """Post init."""
        if self.layout_type not in PROMPTER_LAYOUT_TYPES:
            raise ValueError(f"Unknown teleprompter layout: {self.layout_type}")
        for key, (minimum, maximum) in PROMPTER_INT_LIMITS.items():
            value = getattr(self, key)
            if not minimum <= value <= maximum:
                raise ValueError(
                    f"{key} must be {minimum}-{maximum}, got {value}"
                )
        for key, (minimum, maximum) in PROMPTER_FLOAT_LIMITS.items():
            value = getattr(self, key)
            if not minimum <= value <= maximum:
                raise ValueError(
                    f"{key} must be {minimum}-{maximum}, got {value}"
                )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrompterConfig':
        """From dict."""
        if not data:
            return cls()

        colors_data = data.get('colors', {})
        if isinstance(colors_data, dict):
            colors = PrompterColors.from_dict(colors_data)
        else:
            colors = PrompterColors()

        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        valid_keys.discard('colors')

        filtered = {k: v for k, v in data.items() if k in valid_keys}
        filtered['colors'] = colors

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['colors'] = self.colors.to_dict()
        return result

    def ensure_defaults(self) -> None:
        """Ensure defaults."""
        defaults = PrompterConfig()
        for field_name in defaults.__dataclass_fields__:
            if not hasattr(self, field_name):
                setattr(self, field_name, getattr(defaults, field_name))


@dataclass
class ReplicaMergeConfig:
    """Replica Merge Config class."""
    merge: bool = DEFAULT_REPLICA_MERGE_CONFIG["merge"]
    merge_parallel_replicas: bool = DEFAULT_REPLICA_MERGE_CONFIG[
        "merge_parallel_replicas"
    ]
    respect_existing_separators: bool = DEFAULT_REPLICA_MERGE_CONFIG[
        "respect_existing_separators"
    ]
    merge_gap: int = DEFAULT_REPLICA_MERGE_CONFIG["merge_gap"]
    p_short: float = DEFAULT_REPLICA_MERGE_CONFIG["p_short"]
    p_long: float = DEFAULT_REPLICA_MERGE_CONFIG["p_long"]
    fps: float = DEFAULT_REPLICA_MERGE_CONFIG["fps"]

    def __post_init__(self) -> None:
        """Post init."""
        if not 1 <= self.merge_gap <= 1000:
            raise ValueError(f"merge_gap must be 1-1000, got {self.merge_gap}")
        if not 0.0 <= self.p_short <= 10.0:
            raise ValueError(f"p_short must be 0.0-10.0, got {self.p_short}")
        if not 0.0 <= self.p_long <= 10.0:
            raise ValueError(f"p_long must be 0.0-10.0, got {self.p_long}")
        if not 1.0 <= self.fps <= 120.0:
            raise ValueError(f"fps must be 1.0-120.0, got {self.fps}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplicaMergeConfig':
        """From dict."""
        if not data:
            return cls()

        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportConfig:
    """Export Config class."""
    format_html: bool = DEFAULT_EXPORT_CONFIG["format_html"]
    format_xls: bool = DEFAULT_EXPORT_CONFIG["format_xls"]
    format_docx: bool = DEFAULT_EXPORT_CONFIG["format_docx"]
    format_pdf: bool = DEFAULT_EXPORT_CONFIG["format_pdf"]
    layout_type: str = DEFAULT_EXPORT_CONFIG["layout_type"]
    font_family: str = DEFAULT_EXPORT_CONFIG["font_family"]
    layout_profiles: Dict[str, Dict[str, Any]] = field(
        default_factory=lambda: deepcopy(DEFAULT_EXPORT_CONFIG["layout_profiles"])
    )
    col_tc: bool = DEFAULT_EXPORT_CONFIG["col_tc"]
    col_char: bool = DEFAULT_EXPORT_CONFIG["col_char"]
    col_actor: bool = DEFAULT_EXPORT_CONFIG["col_actor"]
    col_text: bool = DEFAULT_EXPORT_CONFIG["col_text"]
    f_time: int = DEFAULT_EXPORT_CONFIG["f_time"]
    f_char: int = DEFAULT_EXPORT_CONFIG["f_char"]
    f_actor: int = DEFAULT_EXPORT_CONFIG["f_actor"]
    f_text: int = DEFAULT_EXPORT_CONFIG["f_text"]
    bold_time: bool = DEFAULT_EXPORT_CONFIG["bold_time"]
    bold_char: bool = DEFAULT_EXPORT_CONFIG["bold_char"]
    bold_actor: bool = DEFAULT_EXPORT_CONFIG["bold_actor"]
    bold_text: bool = DEFAULT_EXPORT_CONFIG["bold_text"]
    table_width_time: float = DEFAULT_EXPORT_CONFIG["table_width_time"]
    table_width_char: float = DEFAULT_EXPORT_CONFIG["table_width_char"]
    table_width_actor: float = DEFAULT_EXPORT_CONFIG["table_width_actor"]
    use_color: bool = DEFAULT_EXPORT_CONFIG["use_color"]
    soften_colors: bool = DEFAULT_EXPORT_CONFIG["soften_colors"]
    color_softening_level: int = DEFAULT_EXPORT_CONFIG["color_softening_level"]
    highlight_character_only: bool = DEFAULT_EXPORT_CONFIG[
        "highlight_character_only"
    ]
    open_auto: bool = DEFAULT_EXPORT_CONFIG["open_auto"]
    round_time: bool = DEFAULT_EXPORT_CONFIG["round_time"]
    hide_leading_timecode_zeros: bool = DEFAULT_EXPORT_CONFIG[
        "hide_leading_timecode_zeros"
    ]
    time_display: str = DEFAULT_EXPORT_CONFIG["time_display"]
    allow_edit: bool = DEFAULT_EXPORT_CONFIG["allow_edit"]
    highlight_ids_export: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Post init."""
        if self.layout_type == 'Сценарий':
            self.layout_type = 'Сценарий 1'
        if self.layout_type not in EXPORT_LAYOUT_TYPES:
            raise ValueError(
                "layout_type must be 'Таблица', 'Сценарий 1', "
                f"'Сценарий 2' or 'Сценарий 3', got {self.layout_type}"
            )
        self.font_family = str(self.font_family or '').strip()
        if not self.font_family or len(self.font_family) > 100:
            raise ValueError("font_family must contain 1-100 characters")
        if self.time_display not in ['range', 'start']:
            raise ValueError(f"time_display must be 'range' or 'start', got {self.time_display}")
        if self.color_softening_level not in [-2, -1, 0, 1, 2]:
            raise ValueError(
                "color_softening_level must be -2-2, got "
                f"{self.color_softening_level}"
            )
        if not 10 <= self.f_time <= 150:
            raise ValueError(f"f_time must be 10-150, got {self.f_time}")
        if not 10 <= self.f_char <= 150:
            raise ValueError(f"f_char must be 10-150, got {self.f_char}")
        if not 10 <= self.f_actor <= 150:
            raise ValueError(f"f_actor must be 10-150, got {self.f_actor}")
        if not 10 <= self.f_text <= 300:
            raise ValueError(f"f_text must be 10-300, got {self.f_text}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportConfig':
        """From dict."""
        if not data:
            return cls()

        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Actor:
    """Actor class."""
    name: str
    color: str = "#FFFFFF"
    gender: str = ""
    roles: List[str] = field(default_factory=list)


@dataclass
class DialogueLine:
    """Dialogue Line class."""
    id: Any
    s: float  # start time in seconds
    e: float  # end time in seconds
    char: str  # character name
    text: str
    s_raw: str = ""  # original time string
    source_ids: List[Any] = field(default_factory=list)
    source_texts: List[str] = field(default_factory=list)
    parts: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogueLine':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
