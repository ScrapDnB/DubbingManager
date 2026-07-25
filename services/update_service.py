"""Service for checking application updates on GitHub Releases."""

import os
import platform
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from packaging.version import InvalidVersion, Version

try:
    import requests
except ImportError:
    requests = None


DEFAULT_RELEASES_API_URL = (
    "https://api.github.com/repos/ScrapDnB/DubbingManager/releases"
)
DEFAULT_RELEASES_PAGE_URL = (
    "https://github.com/ScrapDnB/DubbingManager/releases/latest"
)


@dataclass(frozen=True)
class ReleaseAsset:
    """Downloadable GitHub Release asset."""

    name: str
    url: str
    size: int = 0


@dataclass(frozen=True)
class UpdateInfo:
    """Information about the latest available release."""

    current_version: str
    latest_version: str
    release_url: str
    is_update_available: bool
    assets: Tuple[ReleaseAsset, ...] = ()


class UpdateService:
    """Check GitHub Releases for a newer application version."""

    def __init__(
        self,
        api_url: str = DEFAULT_RELEASES_API_URL,
        fallback_url: str = DEFAULT_RELEASES_PAGE_URL,
        timeout: float = 8.0
    ) -> None:
        self.api_url = api_url
        self.fallback_url = fallback_url
        self.timeout = timeout

    def check_for_updates(self, current_version: str) -> UpdateInfo:
        """Return update information from the latest GitHub release."""
        if requests is None:
            raise ImportError("requests not available")
        response = requests.get(
            self.api_url,
            timeout=self.timeout,
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()

        payload = response.json()
        release = self._select_release(payload, current_version)
        latest_version = self._normalize_version(
            str(release.get("tag_name") or release.get("name") or "")
        )
        release_url = str(release.get("html_url") or self.fallback_url)
        assets = self._parse_assets(release)

        if not latest_version:
            latest_version = current_version

        return UpdateInfo(
            current_version=current_version,
            latest_version=latest_version,
            release_url=release_url,
            is_update_available=self.is_newer_version(
                latest_version,
                current_version
            ),
            assets=assets,
        )

    def find_platform_asset(
        self,
        update_info: UpdateInfo,
        system: Optional[str] = None
    ) -> Optional[ReleaseAsset]:
        """Return the release asset matching the current platform."""
        system_name = (system or platform.system()).lower()
        if system_name == "darwin":
            preferred = ("macos", ".dmg")
        elif system_name == "windows":
            preferred = ("windows", ".zip")
        else:
            return None

        for asset in update_info.assets:
            name = asset.name.lower()
            if all(part in name for part in preferred):
                return asset
        return None

    def download_asset(
        self,
        asset: ReleaseAsset,
        destination_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """Download a release asset and return the local path."""
        if requests is None:
            raise ImportError("requests not available")
        target_dir = Path(destination_dir or tempfile.gettempdir())
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / asset.name
        downloaded = 0

        with requests.get(asset.url, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or asset.size or 0)
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total)

        if progress_callback:
            progress_callback(downloaded, downloaded or asset.size)

        return str(target_path)

    def is_source_checkout(self, repo_dir: Optional[str] = None) -> bool:
        """Return whether the app appears to be running from source checkout."""
        if getattr(sys, "frozen", False):
            return False
        return (Path(repo_dir or os.getcwd()) / ".git").exists()

    def install_source_update(self, repo_dir: Optional[str] = None) -> str:
        """Update a source checkout using git pull --ff-only."""
        root = Path(repo_dir or os.getcwd())
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        if status.stdout.strip():
            raise RuntimeError(
                "В рабочей копии есть несохранённые изменения. "
                "Сохраните или закоммитьте их перед автообновлением."
            )

        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return (result.stdout or result.stderr).strip()

    def start_binary_update(
        self,
        asset_path: str,
        app_path: Optional[str] = None,
        executable_path: Optional[str] = None,
        pid: Optional[int] = None
    ) -> str:
        """Start an external updater script for a packaged app."""
        system_name = platform.system().lower()
        if system_name == "darwin":
            script = self._create_macos_update_script(
                asset_path,
                app_path or self._current_macos_app_path(),
                pid or os.getpid(),
            )
            subprocess.Popen(["/bin/sh", script], start_new_session=True)
            return script
        if system_name == "windows":
            script = self._create_windows_update_script(
                asset_path,
                app_path or str(Path(executable_path or sys.executable).parent),
                executable_path or sys.executable,
                pid or os.getpid(),
            )
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script,
                ],
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            return script
        raise RuntimeError("Автоустановка поддерживается только на macOS и Windows.")

    @classmethod
    def is_newer_version(cls, candidate: str, current: str) -> bool:
        """Return whether candidate version is newer than current version."""
        return cls._version_key(candidate) > cls._version_key(current)

    @classmethod
    def _normalize_version(cls, version: str) -> str:
        """Normalize release tags such as v1.4.3 to 1.4.3."""
        return version.strip().lstrip("vV")

    @classmethod
    def _version_key(cls, version: str) -> Version:
        """Return a standards-aware PEP 440 version key."""
        try:
            return Version(cls._normalize_version(version))
        except InvalidVersion:
            return Version("0")

    @classmethod
    def _select_release(
        cls,
        payload: Any,
        current_version: str,
    ) -> Dict[str, Any]:
        """Select the newest release visible to the current update channel."""
        if isinstance(payload, dict):
            return payload
        if not isinstance(payload, list):
            return {}
        try:
            current = Version(cls._normalize_version(current_version))
        except InvalidVersion:
            current = Version("0")
        allow_prerelease = current.is_prerelease
        candidates = []
        for release in payload:
            if not isinstance(release, dict) or release.get("draft"):
                continue
            if release.get("prerelease") and not allow_prerelease:
                continue
            raw_version = str(
                release.get("tag_name") or release.get("name") or ""
            )
            try:
                parsed = Version(cls._normalize_version(raw_version))
            except InvalidVersion:
                continue
            candidates.append((parsed, release))
        return max(candidates, key=lambda item: item[0])[1] if candidates else {}

    @staticmethod
    def _parse_assets(payload: Dict[str, Any]) -> Tuple[ReleaseAsset, ...]:
        """Parse GitHub release assets."""
        result = []
        for asset in payload.get("assets", []):
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if name and url:
                result.append(
                    ReleaseAsset(
                        name=name,
                        url=url,
                        size=int(asset.get("size") or 0),
                    )
                )
        return tuple(result)

    @staticmethod
    def _current_macos_app_path() -> str:
        """Return the current .app bundle path."""
        current = Path(sys.executable).resolve()
        for parent in [current, *current.parents]:
            if parent.suffix == ".app":
                return str(parent)
        raise RuntimeError("Не удалось определить путь к текущему .app.")

    def _create_macos_update_script(
        self,
        dmg_path: str,
        app_path: str,
        pid: int
    ) -> str:
        """Create a shell script that replaces the current macOS app."""
        script_path = Path(tempfile.gettempdir()) / "dubbing_manager_update.sh"
        app_name = Path(app_path).name
        mount_root = Path(tempfile.gettempdir()) / "dubbing_manager_update_mount"
        app = shlex.quote(app_path)
        mounted_app = shlex.quote(str(mount_root / app_name))
        mount = shlex.quote(str(mount_root))
        dmg = shlex.quote(dmg_path)
        staging = shlex.quote(app_path + ".update-new")
        previous = shlex.quote(app_path + ".update-old")
        script = f"""#!/bin/sh
set -e
osascript -e 'display notification "Файлы приложения будут заменены после закрытия Dubbing Manager." with title "Dubbing Manager" subtitle "Обновление началось"' >/dev/null 2>&1 || true
while kill -0 {pid} 2>/dev/null; do
  sleep 1
done
rm -rf {mount} {staging} {previous}
mkdir -p {mount}
hdiutil attach {dmg} -mountpoint {mount} -nobrowse -quiet
trap 'hdiutil detach {mount} -quiet >/dev/null 2>&1 || true' EXIT
ditto {mounted_app} {staging}
mv {app} {previous}
if ! mv {staging} {app}; then
  mv {previous} {app}
  exit 1
fi
rm -rf {previous}
hdiutil detach {mount} -quiet || true
osascript -e 'display notification "Новая версия установлена и сейчас будет запущена." with title "Dubbing Manager" subtitle "Обновление готово"' >/dev/null 2>&1 || true
open {app}
"""
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)
        return str(script_path)

    def _create_windows_update_script(
        self,
        zip_path: str,
        app_dir: str,
        executable_path: str,
        pid: int
    ) -> str:
        """Create a PowerShell script that replaces the current Windows app."""
        script_path = Path(tempfile.gettempdir()) / "dubbing_manager_update.ps1"
        extract_dir = Path(tempfile.gettempdir()) / "dubbing_manager_update_extract"
        def ps_quote(value: str) -> str:
            return "'" + str(value).replace("'", "''") + "'"

        zip_literal = ps_quote(zip_path)
        extract_literal = ps_quote(str(extract_dir))
        app_literal = ps_quote(app_dir)
        executable_literal = ps_quote(executable_path)
        staging_literal = ps_quote(app_dir + ".update-new")
        previous_literal = ps_quote(app_dir + ".update-old")
        script = f"""
$ErrorActionPreference = "Stop"
[void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
[void][System.Reflection.Assembly]::LoadWithPartialName("System.Drawing")
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = "Dubbing Manager"
$notify.BalloonTipText = "Файлы приложения будут заменены после закрытия."
$notify.Visible = $true
$notify.ShowBalloonTip(3000)
Wait-Process -Id {pid} -ErrorAction SilentlyContinue
$extractDir = {extract_literal}
$appDir = {app_literal}
$staging = {staging_literal}
$previous = {previous_literal}
Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $previous -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath {zip_literal} -DestinationPath $extractDir -Force
$source = Join-Path $extractDir "Dubbing Manager"
if (!(Test-Path -LiteralPath $source)) {{
  $source = $extractDir
}}
New-Item -ItemType Directory -Path $staging | Out-Null
Copy-Item -Path (Join-Path $source "*") -Destination $staging -Recurse -Force
Move-Item -LiteralPath $appDir -Destination $previous
try {{
  Move-Item -LiteralPath $staging -Destination $appDir
}} catch {{
  Move-Item -LiteralPath $previous -Destination $appDir
  throw
}}
Remove-Item -LiteralPath $previous -Recurse -Force
$notify.BalloonTipText = "Новая версия установлена и сейчас будет запущена."
$notify.ShowBalloonTip(3000)
Start-Process -FilePath {executable_literal}
"""
        script_path.write_text(script.strip() + "\n", encoding="utf-8")
        return str(script_path)
