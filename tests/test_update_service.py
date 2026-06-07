"""Tests for GitHub update checks."""

from unittest.mock import Mock, patch

import pytest

from services.update_service import ReleaseAsset, UpdateInfo, UpdateService


def test_is_newer_version_compares_numeric_parts():
    assert UpdateService.is_newer_version("1.10.0", "1.9.9") is True
    assert UpdateService.is_newer_version("v1.4.3", "1.4.3") is False
    assert UpdateService.is_newer_version("1.4.2", "1.4.3") is False


def test_check_for_updates_reads_latest_github_release():
    response = Mock()
    response.json.return_value = {
        "tag_name": "v1.4.4",
        "html_url": "https://example.test/release",
        "assets": [{
            "name": "Dubbing_Manager_macOS.dmg",
            "browser_download_url": "https://example.test/app.dmg",
            "size": 123,
        }],
    }
    response.raise_for_status.return_value = None

    with patch("services.update_service.requests.get", return_value=response) as get:
        info = UpdateService(timeout=1.0).check_for_updates("1.4.3")

    get.assert_called_once()
    assert info.current_version == "1.4.3"
    assert info.latest_version == "1.4.4"
    assert info.release_url == "https://example.test/release"
    assert info.is_update_available is True
    assert info.assets == (
        ReleaseAsset(
            "Dubbing_Manager_macOS.dmg",
            "https://example.test/app.dmg",
            123,
        ),
    )


def test_check_for_updates_handles_missing_tag_as_current_version():
    response = Mock()
    response.json.return_value = {}
    response.raise_for_status.return_value = None

    with patch("services.update_service.requests.get", return_value=response):
        info = UpdateService().check_for_updates("1.4.3")

    assert info.latest_version == "1.4.3"
    assert info.is_update_available is False


def test_find_platform_asset_selects_current_platform_asset():
    info = UpdateInfo(
        current_version="1.4.3",
        latest_version="1.4.4",
        release_url="https://example.test/release",
        is_update_available=True,
        assets=(
            ReleaseAsset("Dubbing_Manager_Windows.zip", "https://example.test/win"),
            ReleaseAsset("Dubbing_Manager_macOS.dmg", "https://example.test/mac"),
        ),
    )
    service = UpdateService()

    assert service.find_platform_asset(info, "Darwin").url == "https://example.test/mac"
    assert service.find_platform_asset(info, "Windows").url == "https://example.test/win"
    assert service.find_platform_asset(info, "Linux") is None


def test_install_source_update_requires_clean_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    status = Mock(stdout=" M file.py\n")

    with patch("services.update_service.subprocess.run", return_value=status):
        with pytest.raises(RuntimeError):
            UpdateService().install_source_update(str(repo))


def test_install_source_update_runs_git_pull_when_clean(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    status = Mock(stdout="")
    pull = Mock(stdout="Already up to date.\n", stderr="")

    with patch(
        "services.update_service.subprocess.run",
        side_effect=[status, pull]
    ) as run:
        output = UpdateService().install_source_update(str(repo))

    assert output == "Already up to date."
    assert run.call_args_list[0].args[0] == ["git", "status", "--porcelain"]
    assert run.call_args_list[1].args[0] == ["git", "pull", "--ff-only"]


def test_create_macos_update_script_contains_expected_paths(tmp_path):
    service = UpdateService()
    script = service._create_macos_update_script(
        str(tmp_path / "update.dmg"),
        "/Applications/Dubbing Manager.app",
        123,
    )

    content = open(script, encoding="utf-8").read()
    assert "hdiutil attach" in content
    assert "ditto" in content
    assert "/Applications/Dubbing Manager.app" in content


def test_create_windows_update_script_contains_expected_paths(tmp_path):
    service = UpdateService()
    script = service._create_windows_update_script(
        str(tmp_path / "update.zip"),
        "C:\\Apps\\Dubbing Manager",
        "C:\\Apps\\Dubbing Manager\\Dubbing Manager.exe",
        123,
    )

    content = open(script, encoding="utf-8").read()
    assert "Expand-Archive" in content
    assert "Copy-Item -Path" in content
    assert "Start-Process" in content
