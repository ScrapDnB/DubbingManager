from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.verify_macos_sdk import sdk_major, verify_sdk


def test_sdk_major_reads_vtool_output():
    assert sdk_major("platform MACOS\n    minos 13.0\n      sdk 26.4\n") == 26
    assert sdk_major("no build version") is None


def test_verify_sdk_rejects_compatibility_build(monkeypatch):
    monkeypatch.setattr(
        "scripts.verify_macos_sdk.subprocess.run",
        Mock(return_value=Mock(stdout="platform MACOS\n sdk 15.5\n")),
    )

    with pytest.raises(RuntimeError, match="SDK 15"):
        verify_sdk(Path("Dubbing Manager"))


def test_verify_sdk_accepts_current_build(monkeypatch):
    run = Mock(return_value=Mock(stdout="platform MACOS\n sdk 26.1\n"))
    monkeypatch.setattr("scripts.verify_macos_sdk.subprocess.run", run)

    verify_sdk(Path("Dubbing Manager"))

    run.assert_called_once()
