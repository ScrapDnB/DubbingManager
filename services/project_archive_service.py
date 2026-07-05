"""Portable project archive import and export."""

from __future__ import annotations

import json
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional


ARCHIVE_FORMAT = "dubbing-manager-project"
ARCHIVE_VERSION = 1
PROJECT_MEMBER = "project.json"
MANIFEST_MEMBER = "manifest.json"
MAX_ARCHIVE_FILES = 10_000
MAX_UNCOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024


class ProjectArchiveError(ValueError):
    """Raised when a project archive is invalid or unsafe."""


class ProjectArchiveService:
    """Create and unpack portable project archives."""

    def export_archive(
        self,
        project_data: Dict[str, Any],
        archive_path: str,
        project_path: Optional[str] = None,
    ) -> Dict[str, int]:
        """Write project metadata, sources and working texts into one archive."""
        destination = Path(archive_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = deepcopy(project_data)
        payload.pop("loaded_episodes", None)

        source_members: Dict[str, str] = {}
        text_members: Dict[str, str] = {}
        missing = 0

        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            for episode, raw_path in payload.get("episodes", {}).items():
                source = self._resolve_path(payload, raw_path, project_path)
                if not source or not source.is_file():
                    missing += 1
                    continue
                member = self._member_name("sources", str(episode), source)
                archive.write(source, member)
                source_members[str(episode)] = member
                payload["episodes"][episode] = member

            for episode, raw_path in payload.get("episode_texts", {}).items():
                source = self._resolve_path(payload, raw_path, project_path)
                if not source or not source.is_file():
                    missing += 1
                    continue
                member = self._member_name("texts", str(episode), source)
                archive.write(source, member)
                text_members[str(episode)] = member
                payload["episode_texts"][episode] = member

            # Imported projects use the extraction folder as their portable root.
            payload["project_folder"] = "."
            archive.writestr(
                PROJECT_MEMBER,
                json.dumps(payload, ensure_ascii=False, indent=4),
            )
            archive.writestr(
                MANIFEST_MEMBER,
                json.dumps(
                    {
                        "format": ARCHIVE_FORMAT,
                        "version": ARCHIVE_VERSION,
                        "project_file": PROJECT_MEMBER,
                        "sources": source_members,
                        "texts": text_members,
                    },
                    ensure_ascii=False,
                    indent=4,
                ),
            )

        return {
            "sources": len(source_members),
            "texts": len(text_members),
            "missing": missing,
        }

    def import_archive(
        self,
        archive_path: str,
        destination_parent: str,
    ) -> str:
        """Extract a project archive into a new folder and return its JSON path."""
        archive_file = Path(archive_path)
        destination_root = Path(destination_parent)
        if not destination_root.is_dir():
            raise ProjectArchiveError("Папка импорта не существует.")

        with zipfile.ZipFile(archive_file, "r") as archive:
            infos = archive.infolist()
            self._validate_archive(infos)
            manifest = self._read_json_member(archive, MANIFEST_MEMBER)
            if (
                manifest.get("format") != ARCHIVE_FORMAT
                or manifest.get("version") != ARCHIVE_VERSION
                or manifest.get("project_file") != PROJECT_MEMBER
            ):
                raise ProjectArchiveError(
                    "Это не поддерживаемый архив Dubbing Manager."
                )

            payload = self._read_json_member(archive, PROJECT_MEMBER)
            self._validate_project_payload(payload)
            folder = self._unique_folder(
                destination_root,
                self._safe_name(payload.get("project_name") or archive_file.stem),
            )
            folder.mkdir()

            try:
                for info in infos:
                    if info.is_dir():
                        continue
                    target = folder / info.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source, target.open("wb") as out:
                        while chunk := source.read(1024 * 1024):
                            out.write(chunk)

                project_path = folder / PROJECT_MEMBER
                imported = self._read_json_file(project_path)
                imported["project_folder"] = str(folder.resolve())
                for mapping_name in ("episodes", "episode_texts"):
                    mapping = imported.get(mapping_name, {})
                    for episode, relative_path in mapping.items():
                        if self._is_archive_member(relative_path):
                            mapping[episode] = str(
                                (folder / relative_path).resolve()
                            )

                project_name = self._safe_name(
                    imported.get("project_name") or "project"
                )
                final_project_path = folder / f"{project_name}.json"
                final_project_path.write_text(
                    json.dumps(imported, ensure_ascii=False, indent=4),
                    encoding="utf-8",
                )
                project_path.unlink()
                (folder / MANIFEST_MEMBER).unlink(missing_ok=True)
                return str(final_project_path)
            except Exception:
                self._remove_partial_tree(folder)
                raise

    def _resolve_path(
        self,
        project_data: Dict[str, Any],
        raw_path: Any,
        project_path: Optional[str],
    ) -> Optional[Path]:
        if not raw_path:
            return None
        path = Path(str(raw_path)).expanduser()
        if path.is_absolute():
            return path
        project_folder = project_data.get("project_folder")
        if project_folder:
            return Path(project_folder).expanduser() / path
        if project_path:
            return Path(project_path).resolve().parent / path
        return path.resolve()

    def _member_name(self, folder: str, episode: str, source: Path) -> str:
        safe_episode = self._safe_name(episode)
        safe_filename = self._safe_name(source.stem) + source.suffix.lower()
        return f"{folder}/episode_{safe_episode}_{safe_filename}"

    def _validate_archive(self, infos: list[zipfile.ZipInfo]) -> None:
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ProjectArchiveError("В архиве слишком много файлов.")
        total_size = sum(info.file_size for info in infos)
        if total_size > MAX_UNCOMPRESSED_SIZE:
            raise ProjectArchiveError("Архив слишком большой после распаковки.")

        names = {info.filename for info in infos}
        if PROJECT_MEMBER not in names or MANIFEST_MEMBER not in names:
            raise ProjectArchiveError("В архиве отсутствует описание проекта.")
        for info in infos:
            if not self._is_archive_member(info.filename):
                raise ProjectArchiveError(
                    f"Небезопасный путь внутри архива: {info.filename}"
                )

    def _is_archive_member(self, name: Any) -> bool:
        if not isinstance(name, str) or not name:
            return False
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            return False
        if name in {PROJECT_MEMBER, MANIFEST_MEMBER}:
            return True
        return len(path.parts) >= 2 and path.parts[0] in {"sources", "texts"}

    def _read_json_member(
        self,
        archive: zipfile.ZipFile,
        member: str,
    ) -> Dict[str, Any]:
        try:
            value = json.loads(archive.read(member).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectArchiveError(
                f"Некорректный JSON внутри архива: {member}"
            ) from exc
        if not isinstance(value, dict):
            raise ProjectArchiveError(f"{member} должен содержать объект.")
        return value

    def _read_json_file(self, path: Path) -> Dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ProjectArchiveError("Некорректный файл проекта.")
        return value

    def _validate_project_payload(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload.get("project_name"), str):
            raise ProjectArchiveError("В архиве отсутствует имя проекта.")
        if not isinstance(payload.get("actors"), dict):
            raise ProjectArchiveError("В архиве повреждён список актёров.")
        if not isinstance(payload.get("episodes"), dict):
            raise ProjectArchiveError("В архиве повреждён список серий.")
        if not isinstance(payload.get("episode_texts", {}), dict):
            raise ProjectArchiveError("В архиве повреждён список текстов.")

    def _safe_name(self, value: str) -> str:
        safe = re.sub(r"[^\w.-]+", "_", str(value).strip(), flags=re.UNICODE)
        return safe.strip("._") or "project"

    def _unique_folder(self, parent: Path, name: str) -> Path:
        candidate = parent / name
        index = 2
        while candidate.exists():
            candidate = parent / f"{name}_{index}"
            index += 1
        return candidate

    def _remove_partial_tree(self, folder: Path) -> None:
        if not folder.exists():
            return
        for path in sorted(folder.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        folder.rmdir()
