from services.audiobook_document_service import AudiobookDocumentService
from services.audiobook_review_service import (
    AudiobookReviewService,
    REVIEW_ALL,
    REVIEW_IGNORED,
    REVIEW_ISSUES,
    REVIEW_UNASSIGNED,
    REVIEW_UNMARKED_DIALOGUE,
)


def _project_and_document():
    document = AudiobookDocumentService().create_document("book.pdf", [(
        "Глава 1",
        "<!DOCTYPE html><html><body><h1>Глава 1</h1>"
        "<p>— Кто здесь?</p>"
        '<p><span data-dm-character="Герой">Это я.</span></p>'
        '<p><span data-dm-character="Друг">Привет.</span></p>'
        "<p>Авторский текст.</p></body></html>",
    )])
    project = {
        "actors": {"actor-1": {"name": "Актёр"}},
        "global_map": {"Друг": "actor-1"},
        "episode_actor_map": {},
        "character_aliases": {"Герой": ["Саша", "капитан"]},
    }
    return project, document


def test_review_queue_finds_unmarked_dialogue_and_role_without_actor():
    project, document = _project_and_document()
    service = AudiobookReviewService()

    rows = service.rows(document, project)
    issues = service.filtered_rows(rows, REVIEW_ISSUES)

    assert [row["kind"] for row in issues] == [
        REVIEW_UNMARKED_DIALOGUE,
        REVIEW_UNASSIGNED,
    ]
    assert service.filtered_rows(rows, REVIEW_UNASSIGNED, "Саша")[0][
        "character"
    ] == "Герой"
    assert len(service.filtered_rows(rows, REVIEW_ALL)) == 4


def test_ignored_review_items_leave_active_queue_and_can_be_filtered():
    project, document = _project_and_document()
    service = AudiobookReviewService()
    rows = service.rows(document, project)
    ignored_id = next(
        row["itemId"] for row in rows
        if row["kind"] == REVIEW_UNMARKED_DIALOGUE
    )

    updated = service.rows(document, project, [ignored_id])

    assert len(service.filtered_rows(updated, REVIEW_ISSUES)) == 1
    assert service.filtered_rows(updated, REVIEW_IGNORED)[0][
        "itemId"
    ] == ignored_id
