"""Route OS requests to open project files to the primary running instance."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QEventLoop,
    QLockFile,
    QObject,
    QStandardPaths,
    QTimer,
    Signal,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app_startup import is_project_file


logger = logging.getLogger(__name__)

PROJECT_OPEN_CONNECT_TIMEOUT_MS = 750
PROJECT_OPEN_WRITE_TIMEOUT_MS = 1_500


def default_server_name() -> str:
    """Return a stable, per-user local-server name."""
    user_identity = f"{Path.home().resolve()}:{getattr(os, 'getuid', lambda: '')()}"
    digest = hashlib.sha256(user_identity.encode("utf-8")).hexdigest()[:16]
    return f"dubbing-manager-project-open-{digest}"


class ProjectOpenRouter(QObject):
    """Receive and forward project-open requests without banning extra windows."""

    projectOpenRequested = Signal(str)

    def __init__(
        self,
        server_name: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name or default_server_name()
        self._server = QLocalServer(self)
        # UserAccessOption makes a second listener replace the first one on
        # Qt's macOS backend. The socket already lives in the user's private
        # temporary directory there; retain the ACL option on other platforms.
        if sys.platform != "darwin":
            self._server.setSocketOptions(QLocalServer.UserAccessOption)
        self._server.newConnection.connect(self._accept_connections)
        lock_digest = hashlib.sha256(
            self._server_name.encode("utf-8")
        ).hexdigest()[:20]
        lock_root = Path(
            QStandardPaths.writableLocation(QStandardPaths.TempLocation)
        )
        self._ownership_lock = QLockFile(
            str(lock_root / f"dubbing-manager-router-{lock_digest}.lock")
        )
        self._clients: set[QLocalSocket] = set()
        self._owns_listener = False

    @property
    def owns_listener(self) -> bool:
        return self._owns_listener

    def start_listener(self) -> bool:
        """Become the receiver, returning False when one is already active."""
        if self._owns_listener:
            return True
        if not self._ownership_lock.tryLock(0):
            return False

        # A crashed process can leave a Unix-domain socket behind.
        QLocalServer.removeServer(self._server_name)
        if self._server.listen(self._server_name):
            self._owns_listener = True
            return True
        logger.warning(
            "Could not start project-open listener %s: %s",
            self._server_name,
            self._server.errorString(),
        )
        self._ownership_lock.unlock()
        return False

    def forward_project(self, path: str) -> bool:
        """Send a project path to the active receiver."""
        project_path = self._validated_path(path)
        if project_path is None:
            return False

        socket = QLocalSocket()
        connect_loop = QEventLoop()
        connect_timeout = QTimer()
        connect_timeout.setSingleShot(True)
        socket.connected.connect(connect_loop.quit)
        connect_timeout.timeout.connect(connect_loop.quit)
        socket.connectToServer(self._server_name)
        if socket.state() != QLocalSocket.ConnectedState:
            connect_timeout.start(PROJECT_OPEN_CONNECT_TIMEOUT_MS)
            connect_loop.exec()
        if socket.state() != QLocalSocket.ConnectedState:
            socket.abort()
            return False

        payload = json.dumps(
            {"command": "open", "path": str(project_path)},
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        if socket.write(payload) != len(payload):
            socket.abort()
            return False
        socket.flush()
        if socket.bytesToWrite() and not socket.waitForBytesWritten(
            PROJECT_OPEN_WRITE_TIMEOUT_MS
        ):
            socket.abort()
            return False
        socket.disconnectFromServer()
        return True

    def close(self) -> None:
        for socket in tuple(self._clients):
            socket.abort()
        self._clients.clear()
        if self._server.isListening():
            self._server.close()
        if self._owns_listener:
            QLocalServer.removeServer(self._server_name)
            self._ownership_lock.unlock()
        self._owns_listener = False

    def _accept_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            self._clients.add(socket)
            socket.readyRead.connect(lambda client=socket: self._read_client(client))
            socket.disconnected.connect(
                lambda client=socket: self._discard_client(client)
            )

    def _read_client(self, socket: QLocalSocket) -> None:
        while socket.canReadLine():
            raw_message = bytes(socket.readLine()).decode("utf-8", errors="replace")
            try:
                message = json.loads(raw_message)
            except (TypeError, ValueError):
                logger.warning("Ignored malformed project-open request")
                continue
            if message.get("command") != "open":
                continue
            project_path = self._validated_path(message.get("path"))
            if project_path is not None:
                self.projectOpenRequested.emit(str(project_path))
        socket.write(b"OK\n")
        socket.flush()

    def _discard_client(self, socket: QLocalSocket) -> None:
        self._clients.discard(socket)
        socket.deleteLater()

    @staticmethod
    def _validated_path(value: object) -> Path | None:
        if not isinstance(value, str) or not is_project_file(value):
            return None
        path = Path(value).expanduser()
        try:
            if not path.is_file():
                return None
            return path.resolve()
        except OSError:
            return None
