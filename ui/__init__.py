"""UI package with lazy compatibility exports.

Importing a QML backend submodule must not initialize the Widgets interface.
"""

from importlib import import_module

__all__ = [
    'MainWindow',
    'TeleprompterWindow',
]


def __getattr__(name):
    modules = {
        "MainWindow": ("ui.main_window", "MainWindow"),
        "TeleprompterWindow": ("ui.teleprompter", "TeleprompterWindow"),
    }
    if name not in modules:
        raise AttributeError(name)
    module_name, attribute = modules[name]
    return getattr(import_module(module_name), attribute)
