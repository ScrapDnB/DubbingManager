"""UI controllers with lazy compatibility exports."""

from importlib import import_module

__all__ = [
    'ActorController',
    'EpisodeController',
    'ExportController',
    'GlobalActorController',
    'ImportController',
    'ProjectController',
    'ReaperExportController',
    'SettingsController',
]


def __getattr__(name):
    module_names = {
        "ActorController": "actor_controller",
        "EpisodeController": "episode_controller",
        "ExportController": "export_controller",
        "GlobalActorController": "global_actor_controller",
        "ImportController": "import_controller",
        "ProjectController": "project_controller",
        "ReaperExportController": "reaper_export_controller",
        "SettingsController": "settings_controller",
    }
    module_name = module_names.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(f"ui.controllers.{module_name}"), name)
