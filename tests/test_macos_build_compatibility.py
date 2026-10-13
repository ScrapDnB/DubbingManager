from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.verify_macos_compatibility import verify_binary, verify_path


def mock_build_info(monkeypatch, output):
    run = Mock(return_value=Mock(stdout=output))
    monkeypatch.setattr("scripts.verify_macos_compatibility.subprocess.run", run)
    return run


def test_modern_sdk_with_old_deployment_target_is_compatible(monkeypatch):
    mock_build_info(monkeypatch, "cmd LC_BUILD_VERSION\n minos 13.0\n sdk 26.4\n tool LD\n version 1267.0\n")
    verify_binary(Path("app"))


def test_homebrew_python_target_is_rejected(monkeypatch):
    mock_build_info(monkeypatch, "cmd LC_BUILD_VERSION\n minos 26.0\n sdk 26.4\n")
    with pytest.raises(RuntimeError, match="требуется macOS 26.0"):
        verify_binary(Path("Python"))


def test_all_universal_architectures_are_checked(monkeypatch):
    mock_build_info(monkeypatch, "minos 13.0\n sdk 26.0\nminos 14.0\n sdk 26.0\n")
    with pytest.raises(RuntimeError, match="требуется macOS 14.0"):
        verify_binary(Path("universal"))


def test_legacy_load_command_is_supported(monkeypatch):
    mock_build_info(monkeypatch, "cmd LC_VERSION_MIN_MACOSX\n version 10.15\n sdk 11.0\n")
    verify_binary(Path("legacy"))


def test_unknown_minimum_fails_closed(monkeypatch):
    mock_build_info(monkeypatch, "sdk 26.4\n")
    with pytest.raises(RuntimeError, match="Не удалось определить"):
        verify_binary(Path("unknown"))


def test_nested_binary_is_checked_and_symlinks_are_deduplicated(monkeypatch, tmp_path):
    binary = tmp_path / "Contents" / "Frameworks" / "Python"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(bytes.fromhex("cffaedfe") + b"test")
    (binary.parent / "Python-link").symlink_to(binary)
    (tmp_path / "resources.txt").write_text("not a binary")
    run = mock_build_info(monkeypatch, "minos 13.0\n sdk 26.4\n")
    assert verify_path(tmp_path) == 1
    run.assert_called_once()
    mock_build_info(monkeypatch, "minos 26.0\n sdk 26.4\n")
    with pytest.raises(RuntimeError, match="Python.*требуется macOS 26.0"):
        verify_path(tmp_path)


def test_empty_bundle_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="Mach-O файлы не найдены"):
        verify_path(tmp_path)


def test_plist_minimum_is_checked(tmp_path):
    import plistlib

    contents = tmp_path / "Contents"
    contents.mkdir()
    with (contents / "Info.plist").open("wb") as target:
        plistlib.dump({"LSMinimumSystemVersion": "26.0"}, target)
    with pytest.raises(RuntimeError, match="LSMinimumSystemVersion=26.0"):
        verify_path(tmp_path)
