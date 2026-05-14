"""Контроллер общего runtime-состояния приложения."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.connection_monitor import ConnectionMonitor
from chestniy_znak_desktop.runtime.state_models import (
    ConnectionState,
    RuntimeSnapshot,
    ScannerState,
    ScannerStatus,
)


class RuntimeController(QObject):
    """Агрегирует состояние связи, сессии и сканера для UI."""

    snapshot_changed = Signal(RuntimeSnapshot)
    blocking_changed = Signal(bool, str)

    def __init__(
        self,
        app_state: AppState,
        connection_monitor: ConnectionMonitor,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер и подписывает его на runtime-сервисы."""

        super().__init__(parent)
        self._app_state = app_state
        self._connection_monitor = connection_monitor
        self._last_blocking = app_state.snapshot.is_blocking
        self._last_blocking_message = ""
        self._connection_monitor.state_changed.connect(self.set_connection_state)

    @property
    def snapshot(self) -> RuntimeSnapshot:
        """Возвращает текущий общий снимок состояния."""

        return self._app_state.snapshot

    def start(self) -> None:
        """Запускает runtime-сервисы приложения."""

        self._connection_monitor.start()
        self._emit_snapshot()

    def stop(self) -> None:
        """Останавливает runtime-сервисы приложения."""

        self._connection_monitor.stop()
        self._emit_snapshot()

    def retry_connection(self) -> None:
        """Запрашивает немедленное переподключение WebSocket."""

        self._connection_monitor.retry_now()

    def set_connection_state(self, state: ConnectionState) -> None:
        """Обновляет состояние backend-соединения."""

        self._app_state.connection = state
        self._emit_snapshot()

    def set_authenticated_user(self, user_name: str) -> None:
        """Помечает сессию как авторизованную."""

        self._app_state.set_authenticated_user(user_name)
        self._emit_snapshot()

    def clear_session(self) -> None:
        """Сбрасывает состояние пользовательской сессии."""

        self._app_state.clear_user()
        self._emit_snapshot()

    def set_scanner_running(self, port: str) -> None:
        """Помечает сканер как работающий на указанном порту."""

        self._app_state.scanner = ScannerState(
            status=ScannerStatus.RUNNING,
            port=port,
            message=f"Сканер подключен: {port}",
        )
        self._emit_snapshot()

    def set_scanner_error(self, message: str) -> None:
        """Помечает сканер как ошибочный."""

        self._app_state.scanner = ScannerState(
            status=ScannerStatus.ERROR,
            port=self._app_state.scanner.port,
            message=message,
        )
        self._emit_snapshot()

    def set_scanner_stopped(self) -> None:
        """Помечает сканер как остановленный."""

        self._app_state.scanner = ScannerState()
        self._emit_snapshot()

    def _emit_snapshot(self) -> None:
        """Публикует снимок состояния и изменение блокировки UI."""

        snapshot = self._app_state.snapshot
        self.snapshot_changed.emit(snapshot)
        blocking_message = self._blocking_message(snapshot)
        if (
            snapshot.is_blocking != self._last_blocking
            or blocking_message != self._last_blocking_message
        ):
            self._last_blocking = snapshot.is_blocking
            self._last_blocking_message = blocking_message
            self.blocking_changed.emit(snapshot.is_blocking, blocking_message)

    @staticmethod
    def _blocking_message(snapshot: RuntimeSnapshot) -> str:
        """Возвращает текст причины блокировки рабочих экранов."""

        if not snapshot.session.is_authenticated:
            return "Требуется авторизация оператора"
        if snapshot.connection.is_blocking:
            return snapshot.connection.message
        return ""
