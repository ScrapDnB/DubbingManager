"""Contract tests for the feature-oriented QML backend."""

from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication, Qt

from core.commands import ReplaceMappingValueCommand
from services.project_service import ProjectService
from ui.qml_backend import ProjectSession
from ui.qml_backend.models import DictListModel
from ui.qml_backend.features.update_bridge import UpdateBridge
from services.update_service import UpdateInfo


def _app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_project_session_owns_state_and_executes_domain_command():
    _app()
    service = ProjectService()
    project_data = {"settings": {"enabled": False}}
    session = ProjectSession(service, project_data)
    domains = []
    session.domainChanged.connect(domains.append)

    session.current_episode = "2"
    session.execute(ReplaceMappingValueCommand(
        project_data,
        "settings",
        {"enabled": True},
        "Update settings",
    ), "settings")

    assert session.data is project_data
    assert session.current_episode == "2"
    assert session.data["settings"] == {"enabled": True}
    assert service.is_dirty is True
    assert session.undo_stack.can_undo() is True
    assert domains == ["settings"]


def test_project_session_replaces_project_without_copying():
    _app()
    session = ProjectSession(ProjectService(), {"project_name": "One"})
    replacement = {"project_name": "Two"}

    session.replace_project(replacement, "Pilot")

    assert session.data is replacement
    assert session.current_episode == "Pilot"


def test_dict_list_model_get_returns_copy_and_handles_bounds():
    model = DictListModel({"name": Qt.UserRole + 1})
    model.set_rows([{"name": "Alice"}])

    row = model.get(0)
    row["name"] = "Changed"

    assert model.get(0) == {"name": "Alice"}
    assert model.get(-1) == {}
    assert model.get(1) == {}


def test_update_bridge_distinguishes_current_update_and_forced_install(monkeypatch):
    _app()
    bridge = UpdateBridge()
    info = UpdateInfo(
        current_version="1.7.1",
        latest_version="1.8.0",
        release_url="https://example.test/release",
        is_update_available=True,
    )
    bridge._service.check_for_updates = Mock(return_value=info)

    def run_now(operation, completed):
        completed(operation(lambda _current, _total: None))
        bridge._busy = False
        return True

    monkeypatch.setattr(bridge, "_start_task", run_now)

    assert bridge.check(False)
    assert bridge.checked
    assert bridge.updateAvailable
    assert bridge.canInstall
    assert bridge.latestVersion == "1.8.0"

    current = UpdateInfo(
        current_version="1.7.1",
        latest_version="1.7.1",
        release_url="https://example.test/release",
        is_update_available=False,
    )
    bridge._service.check_for_updates.return_value = current
    assert bridge.check(True)
    assert bridge.forceInstall
    assert bridge.canInstall
    assert "переустановлена" in bridge.status
