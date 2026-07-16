"""Compatibility import for the Widgets-era controller module."""

from services.reaper_export_service import ReaperExportService


class ReaperExportController(ReaperExportService):
    """Backward-compatible name used by the existing Widgets interface."""
