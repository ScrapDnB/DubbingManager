"""Controller for project/global settings mutations."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from config.constants import DEFAULT_EXPORT_CONFIG, DEFAULT_PROMPTER_CONFIG


class SettingsController:
    """Apply and persist settings without depending on main-window widgets."""

    def __init__(
        self,
        data_ref: Dict[str, Any],
        global_settings: Dict[str, Any],
        global_settings_service: Any,
    ) -> None:
        self.data_ref = data_ref
        self.global_settings = global_settings
        self.global_settings_service = global_settings_service

    def save_default_export_config(self, config: Dict[str, Any]) -> bool:
        """Save default export settings for future projects."""
        self.global_settings_service.set_default_export_config(config)
        self.global_settings["default_export_config"] = (
            self.global_settings_service.get_default_export_config()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def apply_default_export_config_to_project(self) -> Dict[str, Any]:
        """Apply default export settings to the current project."""
        return self.apply_export_config_to_project(
            self.global_settings_service.get_default_export_config()
        )

    def apply_export_config_to_project(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply export settings to the current project."""
        export_config = deepcopy(DEFAULT_EXPORT_CONFIG)
        export_config.update(deepcopy(config))
        self.data_ref["export_config"] = export_config
        return deepcopy(self.data_ref["export_config"])

    def save_default_prompter_config(self, config: Dict[str, Any]) -> bool:
        """Save default teleprompter settings for future projects."""
        self.global_settings_service.set_default_prompter_config(config)
        self.global_settings["default_prompter_config"] = (
            self.global_settings_service.get_default_prompter_config()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def apply_default_prompter_config_to_project(self) -> Dict[str, Any]:
        """Apply default teleprompter settings to the current project."""
        return self.apply_prompter_config_to_project(
            self.global_settings_service.get_default_prompter_config()
        )

    def apply_prompter_config_to_project(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply teleprompter settings to the current project."""
        self.data_ref["prompter_config"] = deepcopy(config)
        return deepcopy(self.data_ref["prompter_config"])

    def apply_prompter_reaper_ports_to_project(
        self,
        config: Dict[str, Any]
    ) -> tuple[Dict[str, Any], bool]:
        """Apply Reaper sync ports to the current project."""
        prompter_config = deepcopy(
            self.data_ref.get("prompter_config") or DEFAULT_PROMPTER_CONFIG
        )
        changed = False
        for key in ("port_in", "port_out"):
            if key in config and prompter_config.get(key) != config[key]:
                prompter_config[key] = config[key]
                changed = True

        if changed:
            self.data_ref["prompter_config"] = prompter_config
        return deepcopy(prompter_config), changed

    def get_prompter_color_presets(self) -> List[Optional[Dict[str, str]]]:
        """Return global teleprompter color presets."""
        return self.global_settings_service.get_prompter_color_presets()

    def save_prompter_color_preset(
        self,
        index: int,
        colors: Dict[str, str]
    ) -> bool:
        """Save one global teleprompter color preset."""
        self.global_settings_service.set_prompter_color_preset(index, colors)
        self.global_settings["prompter_color_presets"] = (
            self.global_settings_service.get_prompter_color_presets()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def clear_prompter_color_preset(self, index: int) -> bool:
        """Clear one global teleprompter color preset."""
        self.global_settings_service.clear_prompter_color_preset(index)
        self.global_settings["prompter_color_presets"] = (
            self.global_settings_service.get_prompter_color_presets()
        )
        return self.global_settings_service.save_settings(self.global_settings)
