"""Core data models."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)


def _validate_hex_color(color: str, field_name: str) -> None:
    """Validate hex color."""
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError(f"Invalid hex color for {field_name}: {color}")


@dataclass
class PrompterColors:
    """Prompter Colors class."""
    bg: str = "#000000"
    active_text: str = "#FFFFFF"
    inactive_text: str = "#444444"
    tc: str = "#888888"
    actor: str = "#AAAAAA"
    header_bg: str = "#111111"
    header_text: str = "#00FF00"

    def __post_init__(self) -> None:
        """Post init."""
        _validate_hex_color(self.bg, "bg")
        _validate_hex_color(self.active_text, "active_text")
        _validate_hex_color(self.inactive_text, "inactive_text")
        _validate_hex_color(self.tc, "tc")
        _validate_hex_color(self.actor, "actor")
        _validate_hex_color(self.header_bg, "header_bg")
        _validate_hex_color(self.header_text, "header_text")

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
    """Prompter Config class."""
    f_tc: int = 20
    f_char: int = 24
    f_actor: int = 18
    f_text: int = 36
    focus_ratio: float = 0.5
    is_mirrored: bool = False
    show_header: bool = False
    port_in: int = 8000
    port_out: int = 9000
    sync_in: bool = True
    sync_out: bool = False
    reaper_offset_enabled: bool = False
    reaper_offset_seconds: float = -2.0
    key_prev: str = "Left"
    key_next: str = "Right"
    scroll_smoothness_slider: int = 18
    colors: PrompterColors = field(default_factory=PrompterColors)

    def __post_init__(self) -> None:
        """Post init."""
        if not 10 <= self.f_tc <= 150:
            raise ValueError(f"f_tc must be 10-150, got {self.f_tc}")
        if not 10 <= self.f_char <= 150:
            raise ValueError(f"f_char must be 10-150, got {self.f_char}")
        if not 10 <= self.f_actor <= 150:
            raise ValueError(f"f_actor must be 10-150, got {self.f_actor}")
        if not 10 <= self.f_text <= 300:
            raise ValueError(f"f_text must be 10-300, got {self.f_text}")
        if not 0.0 <= self.focus_ratio <= 1.0:
            raise ValueError(f"focus_ratio must be 0.0-1.0, got {self.focus_ratio}")
        if not 1024 <= self.port_in <= 65535:
            raise ValueError(f"port_in must be 1024-65535, got {self.port_in}")
        if not 1024 <= self.port_out <= 65535:
            raise ValueError(f"port_out must be 1024-65535, got {self.port_out}")
        if not 0 <= self.scroll_smoothness_slider <= 100:
            raise ValueError(f"scroll_smoothness_slider must be 0-100, got {self.scroll_smoothness_slider}")

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
    merge: bool = True
    merge_gap: int = 5
    p_short: float = 0.5
    p_long: float = 2.0
    fps: float = 25.0

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
    layout_type: str = 'Таблица'
    col_tc: bool = True
    col_char: bool = True
    col_actor: bool = True
    col_text: bool = True
    f_time: int = 21
    f_char: int = 20
    f_actor: int = 14
    f_text: int = 30
    use_color: bool = True
    open_auto: bool = True
    round_time: bool = False
    time_display: str = 'range'
    allow_edit: bool = True
    highlight_ids_export: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Post init."""
        if self.layout_type not in ['Таблица', 'Сценарий']:
            raise ValueError(f"layout_type must be 'Таблица' or 'Сценарий', got {self.layout_type}")
        if self.time_display not in ['range', 'start']:
            raise ValueError(f"time_display must be 'range' or 'start', got {self.time_display}")
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
    roles: List[str] = field(default_factory=list)


@dataclass
class DialogueLine:
    """Dialogue Line class."""
    id: int
    s: float  # start time in seconds
    e: float  # end time in seconds
    char: str  # character name
    text: str
    s_raw: str = ""  # original time string
    source_ids: List[int] = field(default_factory=list)
    source_texts: List[str] = field(default_factory=list)
    parts: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogueLine':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
