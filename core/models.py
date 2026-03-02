"""Модели данных с использованием dataclass"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class PrompterColors:
    """Цветовая схема телесуфлёра"""
    bg: str = "#000000"
    active_text: str = "#FFFFFF"
    inactive_text: str = "#444444"
    tc: str = "#888888"
    actor: str = "#AAAAAA"
    header_bg: str = "#111111"
    header_text: str = "#00FF00"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrompterColors':
        """Создание из словаря с обратной совместимостью"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
    
    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class PrompterConfig:
    """Конфигурация телесуфлёра"""
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrompterConfig':
        """Создание из словаря с обратной совместимостью"""
        if not data:
            return cls()
        
        # Обрабатываем вложенные цвета
        colors_data = data.get('colors', {})
        if isinstance(colors_data, dict):
            colors = PrompterColors.from_dict(colors_data)
        else:
            colors = PrompterColors()
        
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        valid_keys.discard('colors')  # Обрабатываем отдельно
        
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        filtered['colors'] = colors
        
        return cls(**filtered)
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['colors'] = self.colors.to_dict()
        return result
    
    def ensure_defaults(self) -> None:
        """Гарантирует наличие всех ключей для обратной совместимости"""
        defaults = PrompterConfig()
        for field_name in defaults.__dataclass_fields__:
            if not hasattr(self, field_name):
                setattr(self, field_name, getattr(defaults, field_name))


@dataclass
class ReplicaMergeConfig:
    """Конфигурация объединения реплик"""
    merge: bool = True
    merge_gap: int = 5
    p_short: float = 0.5
    p_long: float = 2.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReplicaMergeConfig':
        """Создание из словаря с обратной совместимостью"""
        if not data:
            return cls()

        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportConfig:
    """Конфигурация экспорта"""
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
    allow_edit: bool = True
    highlight_ids_export: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportConfig':
        """Создание из словаря с обратной совместимостью"""
        if not data:
            return cls()

        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Actor:
    """Данные актёра"""
    name: str
    color: str = "#FFFFFF"
    roles: List[str] = field(default_factory=list)


@dataclass
class DialogueLine:
    """Строка диалога из ASS файла"""
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