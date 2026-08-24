"""Tests for routing OS project-open requests between app instances."""

from uuid import uuid4

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from ui.project_open_router import ProjectOpenRouter


def _app() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def _drain_until(predicate, timeout_ms: int = 1_000) -> None:
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    poll = QTimer()
    poll.timeout.connect(lambda: loop.quit() if predicate() else None)
    poll.start(10)
    timer.start(timeout_ms)
    loop.exec()


def test_second_router_does_not_claim_existing_listener():
    _app()
    server_name = f"dm-test-{uuid4().hex[:16]}"
    primary = ProjectOpenRouter(server_name)
    secondary = ProjectOpenRouter(server_name)
    try:
        assert primary.start_listener() is True
        assert secondary.start_listener() is False
        primary.close()
        assert secondary.start_listener() is True
    finally:
        secondary.close()
        primary.close()


def test_project_path_is_forwarded_to_primary_instance(tmp_path):
    _app()
    path = tmp_path / "Маршрутизируемый проект.dub"
    path.write_text("{}", encoding="utf-8")
    server_name = f"dm-test-{uuid4().hex[:16]}"
    primary = ProjectOpenRouter(server_name)
    secondary = ProjectOpenRouter(server_name)
    received: list[str] = []
    primary.projectOpenRequested.connect(received.append)
    try:
        assert primary.start_listener()
        assert secondary.forward_project(str(path))
        _drain_until(lambda: bool(received))
        assert received == [str(path.resolve())]
    finally:
        secondary.close()
        primary.close()


def test_router_rejects_non_project_and_missing_files(tmp_path):
    _app()
    router = ProjectOpenRouter(f"dm-test-{uuid4().hex[:16]}")
    assert router.forward_project(str(tmp_path / "missing.dub")) is False
    text_file = tmp_path / "notes.txt"
    text_file.write_text("notes", encoding="utf-8")
    assert router.forward_project(str(text_file)) is False
