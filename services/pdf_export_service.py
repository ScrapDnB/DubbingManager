"""PDF export service based on Qt's text document renderer."""

import os
from typing import Optional

from PySide6.QtCore import QCoreApplication, QMarginsF
from PySide6.QtGui import (
    QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument,
)


class PdfExportService:
    """Render montage-sheet HTML into a PDF file."""

    _qt_app: Optional[QGuiApplication] = None

    def _ensure_qapplication(self) -> None:
        """Create a GUI application for standalone/headless service usage."""
        instance = QCoreApplication.instance()
        if isinstance(instance, QGuiApplication):
            return
        if instance is not None:
            raise RuntimeError(
                "PDF export requires QGuiApplication, but QCoreApplication "
                "is already running"
            )
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        PdfExportService._qt_app = QGuiApplication([])

    def render_html_to_pdf(self, html: str, save_path: str) -> None:
        """Render HTML into an A4 portrait PDF."""
        self._ensure_qapplication()

        writer = QPdfWriter(save_path)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setPageMargins(
            QMarginsF(12.0, 12.0, 12.0, 12.0),
            QPageLayout.Millimeter
        )
        writer.setResolution(96)

        document = QTextDocument()
        document.setHtml(html)
        document.print_(writer)
