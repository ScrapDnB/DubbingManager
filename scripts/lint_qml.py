"""Run the qmllint bundled with the installed PySide6 package."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import PySide6


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    qml_root = project_root / "qml"
    executable_name = "qmllint.exe" if sys.platform.startswith("win") else "qmllint"
    qmllint = Path(PySide6.__file__).resolve().parent / executable_name
    if not qmllint.is_file():
        print(f"Could not find qmllint at {qmllint}", file=sys.stderr)
        return 2

    qml_files = sorted(str(path) for path in qml_root.rglob("*.qml"))
    result = subprocess.run(
        [str(qmllint), "-I", str(qml_root), *qml_files],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
    else:
        print(f"QML syntax check passed for {len(qml_files)} files")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
