"""Check the deployment target of Python or every Mach-O in a macOS bundle."""

from __future__ import annotations

import argparse
import plistlib
import re
import subprocess
from pathlib import Path


MACHO_MAGIC = {
    bytes.fromhex(value)
    for value in (
        "feedface", "cefaedfe", "feedfacf", "cffaedfe",
        "cafebabe", "bebafeca", "cafebabf", "bfbafeca",
    )
}
MINIMUM_PATTERN = re.compile(r"^\s*minos\s+(\d+(?:\.\d+){0,2})\s*$", re.MULTILINE)
LEGACY_MINIMUM_PATTERN = re.compile(
    r"^\s*cmd LC_VERSION_MIN_MACOSX\s*$"
    r"(?:(?!^\s*cmd\s).)*?^\s*version\s+(\d+(?:\.\d+){0,2})\s*$",
    re.MULTILINE | re.DOTALL,
)


def version_tuple(value: str) -> tuple[int, int, int]:
    parts = tuple(int(part) for part in value.split("."))
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"Некорректная версия macOS: {value}")
    return parts + (0,) * (3 - len(parts))


def verify_binary(binary: Path, maximum: str = "13.0") -> None:
    result = subprocess.run(
        ["xcrun", "vtool", "-show-build", str(binary)],
        check=True, capture_output=True, text=True,
    )
    versions = MINIMUM_PATTERN.findall(result.stdout) + LEGACY_MINIMUM_PATTERN.findall(result.stdout)
    if not versions:
        raise RuntimeError(f"Не удалось определить минимальную macOS для {binary}")
    # A universal binary can report a different minimum for each architecture.
    actual = max(versions, key=version_tuple)
    if version_tuple(actual) > version_tuple(maximum):
        raise RuntimeError(f"{binary}: требуется macOS {actual}, целевая версия — {maximum}")


def verify_path(path: Path, maximum: str = "13.0") -> int:
    version_tuple(maximum)
    if path.is_file():
        verify_binary(path, maximum)
        return 1
    if not path.is_dir():
        raise RuntimeError(f"Путь не найден: {path}")

    plist_path = path / "Contents" / "Info.plist"
    if plist_path.is_file():
        with plist_path.open("rb") as source:
            minimum = plistlib.load(source).get("LSMinimumSystemVersion")
        if not minimum or version_tuple(minimum) > version_tuple(maximum):
            raise RuntimeError(f"{plist_path}: несовместимое LSMinimumSystemVersion={minimum}")

    checked: set[Path] = set()
    failures = []
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved in checked:
            continue
        with candidate.open("rb") as source:
            if source.read(4) not in MACHO_MAGIC:
                continue
        checked.add(resolved)
        try:
            verify_binary(candidate, maximum)
        except (RuntimeError, subprocess.CalledProcessError) as error:
            failures.append(str(error))

    if not checked:
        raise RuntimeError(f"Mach-O файлы не найдены: {path}")
    if failures:
        raise RuntimeError("Несовместимые компоненты:\n" + "\n".join(failures))
    return len(checked)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--python-library", action="store_true")
    parser.add_argument("--maximum-minos", default="13.0")
    args = parser.parse_args()
    if args.python_library == (args.path is not None):
        parser.error("Укажите путь либо --python-library")
    try:
        path = args.path
        if args.python_library:
            from PyInstaller.depend.bindepend import get_python_library_path

            path = get_python_library_path()
            if path is None:
                raise RuntimeError("Не удалось найти библиотеку Python")
        count = verify_path(Path(path), args.maximum_minos)
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error)
        if args.python_library:
            print("Создайте отдельное окружение на совместимом Python из python.org; см. .github/BUILD.md.")
        return 1
    print(f"Минимальная macOS не выше {args.maximum_minos}: проверено Mach-O файлов — {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
