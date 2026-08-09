"""Per-layout profiles for montage-sheet appearance settings."""

from copy import deepcopy
from typing import Any, Dict

from config.constants import (
    DEFAULT_EXPORT_CONFIG,
    EXPORT_LAYOUT_PROFILE_KEYS,
    EXPORT_LAYOUT_TYPES,
)


def normalize_layout_type(value: Any) -> str:
    """Return a supported montage layout name."""
    if value == "Сценарий":
        return "Сценарий 1"
    value = str(value or "")
    return value if value in EXPORT_LAYOUT_TYPES else "Таблица"


def _flat_profile(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: deepcopy(config.get(key, DEFAULT_EXPORT_CONFIG[key]))
        for key in EXPORT_LAYOUT_PROFILE_KEYS
    }


def hydrate_layout_profile(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize profiles and expose the active one through flat legacy keys."""
    result = deepcopy(DEFAULT_EXPORT_CONFIG)
    if isinstance(config, dict):
        result.update(deepcopy(config))
    active_layout = normalize_layout_type(result.get("layout_type"))
    result["layout_type"] = active_layout

    source_profiles = config.get("layout_profiles") if isinstance(config, dict) else None
    has_profiles = isinstance(source_profiles, dict) and bool(source_profiles)
    legacy_profile = _flat_profile(result)
    profiles: Dict[str, Dict[str, Any]] = {}
    for layout_type in EXPORT_LAYOUT_TYPES:
        profile = (
            deepcopy(DEFAULT_EXPORT_CONFIG["layout_profiles"][layout_type])
            if has_profiles
            else deepcopy(legacy_profile)
        )
        source_profile = (
            source_profiles.get(layout_type) if has_profiles else None
        )
        if isinstance(source_profile, dict):
            for key in EXPORT_LAYOUT_PROFILE_KEYS:
                if key in source_profile:
                    profile[key] = deepcopy(source_profile[key])
        profiles[layout_type] = profile

    result["layout_profiles"] = profiles
    result.update(deepcopy(profiles[active_layout]))
    return result


def sync_active_layout_profile(config: Dict[str, Any]) -> Dict[str, Any]:
    """Write the active flat appearance values back into its profile."""
    result = deepcopy(config)
    profiles = result.get("layout_profiles")
    if not isinstance(profiles, dict) or not profiles:
        return result
    active_layout = normalize_layout_type(result.get("layout_type"))
    normalized_profiles = deepcopy(profiles)
    profile = deepcopy(
        normalized_profiles.get(
            active_layout,
            DEFAULT_EXPORT_CONFIG["layout_profiles"][active_layout],
        )
    )
    for key in EXPORT_LAYOUT_PROFILE_KEYS:
        if key in result:
            profile[key] = deepcopy(result[key])
    normalized_profiles[active_layout] = profile
    result["layout_profiles"] = normalized_profiles
    return result


def set_layout_profile_option(
    config: Dict[str, Any], key: str, value: Any
) -> Dict[str, Any]:
    """Update one option, preserving and hydrating per-layout appearance."""
    result = hydrate_layout_profile(config)
    active_layout = result["layout_type"]

    if key == "layout_type":
        next_layout = normalize_layout_type(value)
        result["layout_type"] = next_layout
        result.update(deepcopy(result["layout_profiles"][next_layout]))
        return result

    result[key] = deepcopy(value)
    if key in EXPORT_LAYOUT_PROFILE_KEYS:
        result["layout_profiles"][active_layout][key] = deepcopy(value)
    return result
