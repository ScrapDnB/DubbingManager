"""QML backend for About information and application updates."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Optional

import PySide6
from PySide6.QtCore import QObject, Property, QThread, QUrl, Signal, Slot, qVersion
from PySide6.QtGui import QDesktopServices, QGuiApplication

from config import APP_VERSION
from services.update_service import UpdateInfo, UpdateService


class _UpdateWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, operation: Callable[[Callable[[int, int], None]], Any]) -> None:
        super().__init__()
        self._operation = operation
        self._cancelled = False

    @Slot()
    def run(self) -> None:
        try:
            result = self._operation(self._report_progress)
            if not self._cancelled:
                self.completed.emit(result)
        except Exception as exc:
            if self._cancelled:
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    def _report_progress(self, current: int, total: int) -> None:
        if self._cancelled:
            raise RuntimeError("Скачивание обновления отменено")
        self.progress.emit(int(current), int(total))


class UpdateBridge(QObject):
    """Expose the existing update service without any Widgets dependency."""

    changed = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = UpdateService()
        self._info: Optional[UpdateInfo] = None
        self._busy = False
        self._checked = False
        self._force_install = False
        self._progress = 0
        self._progress_total = 0
        self._status = "Обновления ещё не проверялись"
        self._thread: Optional[QThread] = None
        self._worker: Optional[_UpdateWorker] = None
        self._source_root = str(Path(__file__).resolve().parents[3])

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return APP_VERSION

    @Property(str, constant=True)
    def pythonVersion(self) -> str:
        return ".".join(str(value) for value in sys.version_info[:3])

    @Property(str, constant=True)
    def qtVersion(self) -> str:
        return qVersion()

    @Property(str, constant=True)
    def pysideVersion(self) -> str:
        return PySide6.__version__

    @Property(str, constant=True)
    def githubUrl(self) -> str:
        return "https://github.com/ScrapDnB/DubbingManager/"

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=changed)
    def checked(self) -> bool:
        return self._checked

    @Property(bool, notify=changed)
    def updateAvailable(self) -> bool:
        return bool(self._info and self._info.is_update_available)

    @Property(bool, notify=changed)
    def canInstall(self) -> bool:
        return bool(self._info and (self.updateAvailable or self._force_install))

    @Property(bool, notify=changed)
    def forceInstall(self) -> bool:
        return self._force_install

    @Property(str, notify=changed)
    def latestVersion(self) -> str:
        return self._info.latest_version if self._info else ""

    @Property(str, notify=changed)
    def releaseUrl(self) -> str:
        return self._info.release_url if self._info else ""

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(int, notify=changed)
    def progress(self) -> int:
        return self._progress

    @Property(int, notify=changed)
    def progressTotal(self) -> int:
        return self._progress_total

    @Property(bool, constant=True)
    def sourceCheckout(self) -> bool:
        return self._service.is_source_checkout(self._source_root)

    @Slot(bool, result=bool)
    def check(self, force_install: bool = False) -> bool:
        if self._busy:
            return False
        self._force_install = bool(force_install)
        self._status = "Проверяю GitHub Releases..."
        return self._start_task(
            lambda _progress: self._service.check_for_updates(APP_VERSION),
            self._check_completed,
        )

    @Slot(result=bool)
    def install(self) -> bool:
        if self._busy or not self._info:
            return False
        if self._service.is_source_checkout(self._source_root):
            self._status = "Обновляю исходники..."
            return self._start_task(
                lambda _progress: self._service.install_source_update(
                    self._source_root
                ),
                self._source_install_completed,
            )
        if not getattr(sys, "frozen", False):
            self._status = "Автоустановка недоступна для этого запуска"
            self.changed.emit()
            self.openReleasePage()
            return False
        asset = self._service.find_platform_asset(self._info)
        if asset is None:
            self._status = "Для этой платформы нет готового файла"
            self.changed.emit()
            self.openReleasePage()
            return False
        self._status = f"Скачиваю {asset.name}..."
        self._progress = 0
        self._progress_total = int(asset.size or 0)
        return self._start_task(
            lambda progress: self._service.download_asset(
                asset, progress_callback=progress
            ),
            self._binary_download_completed,
        )

    @Slot()
    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._status = "Отменяю операцию..."
            self.changed.emit()

    @Slot()
    def openReleasePage(self) -> None:
        url = self.releaseUrl or self._service.fallback_url
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def openGithub(self) -> None:
        QDesktopServices.openUrl(QUrl(self.githubUrl))

    def _start_task(
        self,
        operation: Callable[[Callable[[int, int], None]], Any],
        completed: Callable[[Any], None],
    ) -> bool:
        self._busy = True
        self.changed.emit()
        thread = QThread(self)
        worker = _UpdateWorker(operation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.completed.connect(completed)
        worker.cancelled.connect(self._task_cancelled)
        worker.failed.connect(self._task_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._task_finished)
        self._thread, self._worker = thread, worker
        thread.start()
        return True

    @Slot(object)
    def _check_completed(self, info: UpdateInfo) -> None:
        self._info = info
        self._checked = True
        if info.is_update_available:
            self._status = (
                f"Доступна версия {info.latest_version}; установлена "
                f"{info.current_version}"
            )
        elif self._force_install:
            self._status = f"Версия {info.current_version} будет переустановлена"
        else:
            self._status = f"Установлена актуальная версия {info.current_version}"
        self.changed.emit()

    @Slot(object)
    def _source_install_completed(self, output: Any) -> None:
        details = str(output or "Репозиторий уже актуален")
        self._status = f"Исходники обновлены. Перезапустите программу. {details}"
        self.statusRequested.emit("Исходники обновлены; требуется перезапуск")
        self.changed.emit()

    @Slot(object)
    def _binary_download_completed(self, path: Any) -> None:
        try:
            self._status = "Запускаю внешний установщик..."
            self.changed.emit()
            self._service.start_binary_update(str(path))
            QGuiApplication.quit()
        except Exception as exc:
            self._task_failed(str(exc))

    @Slot(int, int)
    def _on_progress(self, current: int, total: int) -> None:
        self._progress = current
        self._progress_total = total
        self.changed.emit()

    @Slot(str)
    def _task_failed(self, message: str) -> None:
        self._status = f"Ошибка обновления: {message}"
        self.errorRequested.emit(self._status)
        self.changed.emit()

    @Slot()
    def _task_cancelled(self) -> None:
        self._status = "Операция отменена"
        self.changed.emit()

    @Slot()
    def _task_finished(self) -> None:
        self._busy = False
        self._thread = None
        self._worker = None
        self.changed.emit()
