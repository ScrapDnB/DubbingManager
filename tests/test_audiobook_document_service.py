"""Tests for canonical audiobook document storage."""

import json

from services.audiobook_document_service import AudiobookDocumentService
from services.script_text_service import ScriptTextService
from services.project_service import ProjectService


def _document():
    return AudiobookDocumentService().create_document("book.pdf", [(
        "Глава 1",
        "<html><body><h1>Глава 1</h1><p>Текст <span "
        'data-dm-character="Герой" data-dm-actor="actor-1">героя</span>.'
        "</p></body></html>",
    )])


def test_structured_document_round_trip_preserves_blocks_and_markup():
    service = AudiobookDocumentService()
    document = _document()

    assert service.chapter_titles(document) == ["Глава 1"]
    lines = service.lines(document, "Глава 1")
    assert [line["char"] for line in lines] == ["Автор", "Автор", "Герой", "Автор"]
    assert lines[2]["text"] == "героя"
    rendered = service.chapter_to_html(
        document["chapters"][0], {"actor-1": "#aabbcc"}
    )
    assert 'data-dm-character="Герой"' in rendered
    assert "background-color:#aabbcc" in rendered
    assert "#aabbcc" not in json.dumps(document)


def test_script_text_view_is_derived_without_persisted_working_text():
    data = {
        "project_kind": "audiobook",
        "audiobook_document": _document(),
        "episode_working_texts": {},
    }

    lines = ScriptTextService().load_episode_lines(data, "Глава 1")

    assert any(line["char"] == "Герой" for line in lines)
    assert data["episode_working_texts"] == {}


def test_audiobook_line_edits_change_only_canonical_document():
    script = ScriptTextService()
    data = {
        "project_kind": "audiobook",
        "audiobook_document": _document(),
        "episode_working_texts": {},
    }
    line = next(
        item for item in script.load_episode_lines(data, "Глава 1")
        if item["char"] == "Герой"
    )

    assert script.update_line_text(
        data, "Глава 1", line["working_id"], "новая реплика"
    )
    assert script.update_line_character(
        data, "Глава 1", line["working_id"], "Другой герой"
    )

    updated = script.load_episode_lines(data, "Глава 1")
    assert any(
        item["char"] == "Другой герой" and item["text"] == "новая реплика"
        for item in updated
    )
    assert data["episode_working_texts"] == {}


def test_document_is_plain_serializable_data():
    encoded = json.dumps(_document(), ensure_ascii=False)
    assert "Глава 1" in encoded
    assert "героя" in encoded


def test_dub_file_embeds_document_without_duplicate_text_fields(tmp_path):
    service = ProjectService()
    data = service.create_new_project("Книга")
    data.update({
        "project_kind": "audiobook",
        "episodes": {"Глава 1": "book.pdf"},
        "audiobook_document": _document(),
    })
    path = tmp_path / "book.dub"

    assert service.save_project_as(data, str(path))

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert "героя" in json.dumps(stored["audiobook_document"], ensure_ascii=False)
    assert stored["episode_working_texts"] == {}
    assert "book_chapters" not in stored
    assert "audiobook_source" not in stored
    assert "audiobook_chapter_order" not in stored


def test_html_round_trip_keeps_run_ids_and_explicit_adjacent_boundaries():
    service = AudiobookDocumentService()
    chapter = service.chapter_from_html("Глава", '<p><span data-dm-run-id="a">Первый</span><span data-dm-run-id="b"> второй</span></p>')
    for _ in range(3):
        chapter = service.chapter_from_html("Глава", service.chapter_to_html(chapter))
    assert [(r["id"], r["text"]) for r in chapter["blocks"][0]["runs"]] == [("a", "Первый"), ("b", " второй")]


def test_nested_partial_markup_keeps_unselected_text_and_deduplicates_ids():
    service = AudiobookDocumentService()
    chapter = service.chapter_from_html("Глава", '<p><span data-dm-run-id="a" data-dm-character="Макс" data-dm-actor="actor-1">до <span data-dm-run-id="b" data-dm-character="Автор" data-dm-actor="">выделение</span> после</span></p><p><span data-dm-run-id="a">Другой абзац</span></p>')
    runs = [r for b in chapter["blocks"] for r in b["runs"]]
    assert [r["text"] for r in runs] == ["до ", "выделение", " после", "Другой абзац"]
    assert [r["character"] for r in runs] == ["Макс", "Автор", "Макс", "Автор"]
    assert "actor_id" not in runs[1]
    assert len({r["id"] for r in runs}) == len(runs)


def test_line_breaks_survive_manuscript_conversion():
    service = AudiobookDocumentService()
    chapter = service.chapter_from_html("Глава", '<p><span data-dm-run-id="line">Один<br>Два</span></p>')
    assert chapter["blocks"][0]["runs"][0]["text"] == "Один\nДва"
    restored = service.chapter_from_html("Глава", service.chapter_to_html(chapter))
    assert restored == chapter


def test_imported_duplicate_run_ids_are_unique_across_chapters():
    service = AudiobookDocumentService()
    document = service.create_document("book.txt", [("Первая", '<p><span data-dm-run-id="same">Один</span></p>'), ("Вторая", '<p><span data-dm-run-id="same">Два</span></p>')])
    ids = [r["id"] for c in document["chapters"] for b in c["blocks"] for r in b["runs"]]
    assert len(set(ids)) == 2
    assert document["source"]["type"] == "txt"
