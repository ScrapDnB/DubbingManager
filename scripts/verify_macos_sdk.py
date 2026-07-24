"""Verify that a Mach-O executable was linked against a recent macOS SDK."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


SDK_PATTERN = re.compile(r"\bsdk\s+(\d+)(?:\.(\d+))?")


def sdk_major(build_info: str) -> int | None:
    match = SDK_PATTERN.search(build_info)
    return int(match.group(1)) if match else None


def verify_sdk(executable: Path, minimum_major: int = 26) -> None:
    result = subprocess.run(
        ["xcrun", "vtool", "-show-build", str(executable)],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = sdk_major(result.stdout)
    if actual is None:
        raise RuntimeError(f"Не удалось определить SDK для {executable}")
    if actual < minimum_major:
        raise RuntimeError(
            f"{executable} связан с SDK {actual}, требуется SDK {minimum_major}+. "
            "Переустановите PyInstaller из исходников текущим Xcode."
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--minimum-major", type=int, default=26)
    args = parser.parse_args()
    verify_sdk(args.executable, args.minimum_major)
    print(f"SDK {args.minimum_major}+ подтверждён: {args.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
