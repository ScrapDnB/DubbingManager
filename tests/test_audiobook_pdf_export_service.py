from pathlib import Path

from services.audiobook_document_service import AudiobookDocumentService
from services.audiobook_pdf_export_service import AudiobookPdfExportService
from services.pdf_export_service import PdfExportService


class _Renderer:
    def __init__(self):
        self.calls = []

    def render_html_to_pdf(self, html, path):
        self.calls.append((html, path))
        Path(path).write_bytes(b"%PDF-test")


def _fixture():
    document = AudiobookDocumentService().create_document("book.pdf", [
        (
            "Глава 1",
            "<!DOCTYPE html><html><body><h1>Глава 1</h1>"
            '<p><span data-dm-character="Герой" '
            'data-dm-actor="actor-1">Реплика.</span></p></body></html>',
        ),
        (
            "Глава 2",
            "<!DOCTYPE html><html><body><h1>Глава 2</h1>"
            "<p>Текст.</p></body></html>",
        ),
    ])
    project = {
        "project_name": "Тестовая книга",
        "actors": {
            "actor-1": {"name": "Актёр", "color": "#aabbcc"}
        },
        "global_map": {"Герой": "actor-1"},
        "character_aliases": {"Герой": ["Саша"]},
    }
    return project, document


def test_build_html_keeps_markup_legend_and_selected_chapter_order():
    project, document = _fixture()
    service = AudiobookPdfExportService(_Renderer())

    output = service.build_html(
        document, project, ["Глава 2", "Глава 1"], studio_layout=True
    )

    assert "Тестовая книга" in output
    assert "Роли и актёры" in output
    assert "Герой" in output and "Актёр" in output and "Саша" in output
    assert "Герой: " in output
    assert output.index("Глава 1") < output.index("Глава 2")
    assert output.count(PdfExportService.PAGE_BREAK_MARKER) == 1


def test_export_combined_and_separate_files(tmp_path):
    project, document = _fixture()
    renderer = _Renderer()
    service = AudiobookPdfExportService(renderer)

    combined = service.export_combined(
        document, project, ["Глава 2"], str(tmp_path / "book")
    )
    separate = service.export_separate(
        document, project, ["Глава 1", "Глава 2"], str(tmp_path / "chapters")
    )

    assert combined.name == "book.pdf" and combined.exists()
    assert [path.name for path in separate] == ["Глава 1.pdf", "Глава 2.pdf"]
    assert all(path.exists() for path in separate)
    assert len(renderer.calls) == 3
