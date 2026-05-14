"""Mock-тесты runtime controller."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.state_models import ConnectionState, ConnectionStatus


class FakeConnectionMonitor(QObject):
    """Fake WebSocket monitor для проверки RuntimeController."""

    state_changed = Signal(ConnectionState)

    def __init__(self) -> None:
        """Создает fake monitor со счетчиками вызовов."""

        super().__init__()
        self.started = False
        self.stopped = False
        self.retry_count = 0

    def start(self) -> None:
        """Фиксирует запуск fake monitor."""

        self.started = True

    def stop(self) -> None:
        """Фиксирует остановку fake monitor."""

        self.stopped = True

    def retry_now(self) -> None:
        """Фиксирует запрос немедленного reconnect."""

        self.retry_count += 1


def test_runtime_controller_updates_connection_state() -> None:
    """Проверяет передачу состояния связи в AppState."""

    app_state = AppState(config=AppConfig())
    app_state.set_authenticated_user("Operator")
    monitor = FakeConnectionMonitor()
    controller = RuntimeController(app_state=app_state, connection_monitor=monitor)

    monitor.state_changed.emit(ConnectionState(status=ConnectionStatus.CONNECTED, message="ok"))

    assert controller.snapshot.connection.is_connected is True
    assert controller.snapshot.is_blocking is False


def test_runtime_controller_updates_scanner_state() -> None:
    """Проверяет обновление состояния сканера."""

    app_state = AppState(config=AppConfig())
    monitor = FakeConnectionMonitor()
    controller = RuntimeController(app_state=app_state, connection_monitor=monitor)

    controller.set_scanner_running("COM7")

    assert controller.snapshot.scanner.is_running is True
    assert controller.snapshot.scanner.port == "COM7"


def test_runtime_controller_delegates_lifecycle() -> None:
    """Проверяет делегирование start/stop/retry в monitor."""

    app_state = AppState(config=AppConfig())
    monitor = FakeConnectionMonitor()
    controller = RuntimeController(app_state=app_state, connection_monitor=monitor)

    controller.start()
    controller.retry_connection()
    controller.stop()

    assert monitor.started is True
    assert monitor.stopped is True
    assert monitor.retry_count == 1
