"""Release-safety tests for the persisted .dub schema."""

from copy import deepcopy
import json

import pytest

from config.constants import APP_VERSION, PROJECT_VERSION
from services.audiobook_document_service import AudiobookDocumentService
from services.project_service import ProjectService, ProjectValidationError
from services.script_text_service import ScriptTextService


def _audiobook_project(service: ProjectService, source_path: str) -> dict:
    document = AudiobookDocumentService().create_document(source_path, [
        (
            "Пролог",
            "<!DOCTYPE html><html><body><h1>Пролог</h1>"
            '<p><span data-dm-character="Автор">Начало книги.</span></p>'
            "</body></html>",
        ),
        (
            "Глава 1",
            "<!DOCTYPE html><html><body>"
            '<p><span data-dm-character="Герой">Первая реплика.</span></p>'
            "</body></html>",
        ),
    ])
    data = service.create_new_project("Аудиокнига")
    data.update({
        "project_kind": "audiobook",
        "episodes": {"Пролог": "audiobook", "Глава 1": "audiobook"},
        "audiobook_document": document,
    })
    return data


def test_future_project_version_is_rejected_without_changing_current_path(tmp_path):
    service = ProjectService()
    service.current_project_path = str(tmp_path / "already-open.dub")
    data = service.create_new_project("Из будущего")
    data["metadata"]["format_version"] = "99.0"
    path = tmp_path / "future.dub"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ProjectValidationError, match="более новой версии"):
        service.load_project(str(path))

    assert service.current_project_path == str(tmp_path / "already-open.dub")


def test_non_object_project_root_has_a_clear_validation_error(tmp_path):
    path = tmp_path / "array.dub"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ProjectValidationError, match="Корень файла проекта"):
        ProjectService().load_project(str(path))


def test_unpublished_legacy_audiobook_format_is_rejected(tmp_path):
    service = ProjectService()
    data = service.create_new_project("Старая книга")
    data.update({
        "project_kind": "audiobook",
        "audiobook_document": {},
        "book_chapters": {"Глава 1": "<p>Текст</p>"},
    })
    path = tmp_path / "legacy-book.dub"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ProjectValidationError, match="импортируйте PDF заново"):
        service.load_project(str(path))


@pytest.mark.parametrize("damage", [
    "duplicate_run_id",
    "chapter_mismatch",
    "duplicate_working_text",
    "non_string_text",
])
def test_invalid_audiobook_never_replaces_existing_project(tmp_path, damage):
    service = ProjectService()
    data = _audiobook_project(service, str(tmp_path / "Книга.pdf"))
    path = tmp_path / "book.dub"
    path.write_text("previous valid contents", encoding="utf-8")

    chapters = data["audiobook_document"]["chapters"]
    runs = [
        run
        for chapter in chapters
        for block in chapter["blocks"]
        for run in block["runs"]
    ]
    if damage == "duplicate_run_id":
        runs[-1]["id"] = runs[0]["id"]
    elif damage == "chapter_mismatch":
        data["episodes"].pop("Глава 1")
    elif damage == "duplicate_working_text":
        data["episode_working_texts"]["Пролог"] = {"lines": []}
    else:
        runs[0]["text"] = 123

    assert service.save_project(data, str(path)) is False
    assert path.read_text(encoding="utf-8") == "previous valid contents"
    assert not (tmp_path / "book.dub.tmp").exists()


def test_audiobook_is_autonomous_and_stable_across_save_load_cycles(tmp_path):
    service = ProjectService()
    source = tmp_path / "Исходники" / "Книга.pdf"
    data = _audiobook_project(service, str(source))
    original_document = deepcopy(data["audiobook_document"])
    path = tmp_path / "Проект аудиокниги.dub"

    for _ in range(5):
        assert service.save_project(data, str(path))
        data = service.load_project(str(path))
        assert data["audiobook_document"] == original_document
        assert data["episode_texts"] == {}
        assert data["episode_working_texts"] == {}

    assert not source.exists()
    lines = ScriptTextService().load_episode_lines(data, "Глава 1")
    assert [line["text"] for line in lines] == ["Первая реплика."]
    assert data["metadata"]["format_version"] == PROJECT_VERSION
    assert data["metadata"]["app_version"] == APP_VERSION


def test_audiobook_backup_is_a_complete_openable_project(tmp_path):
    service = ProjectService()
    service.current_project_path = str(tmp_path / "book.dub")
    data = _audiobook_project(service, str(tmp_path / "missing.pdf"))

    assert service.create_backup(data, "before_edit")
    backup = service.list_backups()[0]
    assert backup.suffix == ".dub_backup"

    loaded = ProjectService().load_project(str(backup))
    assert loaded["audiobook_document"] == data["audiobook_document"]
    assert ScriptTextService().load_episode_lines(loaded, "Пролог")


def test_failed_atomic_replace_preserves_previous_project(monkeypatch, tmp_path):
    service = ProjectService()
    path = tmp_path / "project.dub"
    original = service.create_new_project("До сбоя")
    assert service.save_project(original, str(path))
    previous_bytes = path.read_bytes()

    changed = service.create_new_project("Не должно попасть в файл")
    monkeypatch.setattr(
        "services.project_service.os.replace",
        lambda *_args: (_ for _ in ()).throw(OSError("disk failure")),
    )

    assert service.save_project(changed, str(path)) is False
    assert path.read_bytes() == previous_bytes
    assert not (tmp_path / "project.dub.tmp").exists()


def test_failed_backup_replace_leaves_no_partial_backup(monkeypatch, tmp_path):
    service = ProjectService()
    service.current_project_path = str(tmp_path / "project.dub")
    data = service.create_new_project("Проект")
    monkeypatch.setattr(
        "services.project_service.os.replace",
        lambda *_args: (_ for _ in ()).throw(OSError("disk failure")),
    )

    assert service.create_backup(data) is False
    backup_dir = tmp_path / ".backups"
    assert not list(backup_dir.glob("*.dub_backup"))
    assert not list(backup_dir.glob("*.tmp"))
