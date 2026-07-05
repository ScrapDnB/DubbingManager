import json
import zipfile
from pathlib import Path

import pytest

from services.project_archive_service import (
    ARCHIVE_FORMAT,
    ARCHIVE_VERSION,
    MANIFEST_MEMBER,
    PROJECT_MEMBER,
    ProjectArchiveError,
    ProjectArchiveService,
)


def _project(source: Path, working_text: Path) -> dict:
    return {
        "project_name": "Тестовый проект",
        "actors": {},
        "global_map": {},
        "episodes": {"1": str(source)},
        "episode_texts": {"1": str(working_text)},
        "video_paths": {"1": "/video/is/not/archived.mov"},
        "loaded_episodes": {"1": [{"text": "runtime cache"}]},
        "project_folder": str(source.parent),
    }


def test_project_archive_round_trip_includes_sources_and_working_texts(tmp_path):
    source = tmp_path / "episode 1.srt"
    source.write_text("1\n00:00:00,000 --> 00:00:01,000\nПривет\n", encoding="utf-8")
    working = tmp_path / "episode_1.json"
    working.write_text(
        json.dumps({"episode": "1", "lines": [{"text": "Привет"}]}),
        encoding="utf-8",
    )
    archive_path = tmp_path / "project.dmproject"
    service = ProjectArchiveService()

    stats = service.export_archive(
        _project(source, working),
        str(archive_path),
        str(tmp_path / "original.json"),
    )

    assert stats == {"sources": 1, "texts": 1, "missing": 0}
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert PROJECT_MEMBER in names
        assert MANIFEST_MEMBER in names
        assert len([name for name in names if name.startswith("sources/")]) == 1
        assert len([name for name in names if name.startswith("texts/")]) == 1
        archived_project = json.loads(archive.read(PROJECT_MEMBER))
        assert "loaded_episodes" not in archived_project

    destination = tmp_path / "imports"
    destination.mkdir()
    imported_path = Path(
        service.import_archive(str(archive_path), str(destination))
    )
    imported = json.loads(imported_path.read_text(encoding="utf-8"))

    assert imported_path.name == "Тестовый_проект.json"
    assert Path(imported["project_folder"]) == imported_path.parent
    assert Path(imported["episodes"]["1"]).read_text(encoding="utf-8") == (
        source.read_text(encoding="utf-8")
    )
    assert json.loads(
        Path(imported["episode_texts"]["1"]).read_text(encoding="utf-8")
    )["episode"] == "1"
    assert imported["video_paths"]["1"] == "/video/is/not/archived.mov"


def test_import_uses_a_new_folder_when_project_folder_already_exists(tmp_path):
    source = tmp_path / "1.srt"
    source.write_text("text", encoding="utf-8")
    working = tmp_path / "1.json"
    working.write_text('{"lines": []}', encoding="utf-8")
    archive_path = tmp_path / "project.dmproject"
    service = ProjectArchiveService()
    service.export_archive(_project(source, working), str(archive_path))
    destination = tmp_path / "imports"
    destination.mkdir()

    first = Path(service.import_archive(str(archive_path), str(destination)))
    second = Path(service.import_archive(str(archive_path), str(destination)))

    assert first.parent.name == "Тестовый_проект"
    assert second.parent.name == "Тестовый_проект_2"


def test_import_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.dmproject"
    manifest = {
        "format": ARCHIVE_FORMAT,
        "version": ARCHIVE_VERSION,
        "project_file": PROJECT_MEMBER,
    }
    project = {
        "project_name": "Unsafe",
        "actors": {},
        "episodes": {},
        "episode_texts": {},
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(MANIFEST_MEMBER, json.dumps(manifest))
        archive.writestr(PROJECT_MEMBER, json.dumps(project))
        archive.writestr("../outside.txt", "bad")

    with pytest.raises(ProjectArchiveError, match="Небезопасный путь"):
        ProjectArchiveService().import_archive(
            str(archive_path),
            str(tmp_path),
        )


def test_import_rejects_regular_zip(tmp_path):
    archive_path = tmp_path / "regular.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("notes.txt", "hello")

    with pytest.raises(ProjectArchiveError, match="описание проекта"):
        ProjectArchiveService().import_archive(
            str(archive_path),
            str(tmp_path),
        )
