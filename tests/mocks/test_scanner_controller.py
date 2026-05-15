"""Mock-тесты контроллера сканера."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.controllers.scanner_controller import ScannerController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.state_models import ScannerStatus
from chestniy_znak_desktop.scanner.base import ScannerConfig, ScannerPort
from chestniy_znak_desktop.scanner import serial_ports
from tests.mocks.test_runtime_controller import FakeConnectionMonitor


class FakeScannerWorker(QObject):
    """Fake scanner worker без реального serial-порта."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        """Создает fake worker."""

        super().__init__()
        self.last_config: ScannerConfig | None = None

    def start_serial(self, config: ScannerConfig) -> None:
        """Запоминает конфиг и публикует старт."""

        self.last_config = config
        self.started.emit()

    def stop(self) -> None:
        """Публикует остановку."""

        self.stopped.emit()


def _runtime() -> RuntimeController:
    """Создает runtime controller для тестов."""

    return RuntimeController(
        app_state=AppState(config=AppConfig()),
        connection_monitor=FakeConnectionMonitor(),
    )


def test_scanner_refresh_selects_first_port(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Проверяет обновление списка портов и выбор первого порта."""

    monkeypatch.setattr(
        serial_ports,
        "list_serial_ports",
        lambda: [ScannerPort(device="COM7", description="Bluetooth SPP")],
    )
    controller = ScannerController(
        runtime_controller=_runtime(), scanner_worker=FakeScannerWorker()
    )

    controller.refresh_ports()

    assert controller.state.selected_port == "COM7"
    assert controller.state.ports[0].title == "COM7 - Bluetooth SPP"


def test_scanner_refresh_skips_manual_only_ports(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет, что системные ttyS не выбираются автоматически."""

    monkeypatch.setattr(
        serial_ports,
        "list_serial_ports",
        lambda: [
            ScannerPort(
                device="/dev/ttyS3",
                description="Linux system serial port",
                auto_selectable=False,
            )
        ],
    )
    controller = ScannerController(
        runtime_controller=_runtime(), scanner_worker=FakeScannerWorker()
    )

    controller.refresh_ports()

    assert controller.state.selected_port == ""
    assert controller.state.ports[0].device == "/dev/ttyS3"


def test_scanner_controller_start_updates_runtime() -> None:
    """Проверяет запуск сканера и runtime status."""

    runtime = _runtime()
    worker = FakeScannerWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=worker,
        initial_port="COM7",
        initial_baudrate=115200,
    )

    controller.start()

    assert worker.last_config is not None
    assert worker.last_config.port == "COM7"
    assert worker.last_config.baudrate == 115200
    assert controller.state.is_running is True
    assert runtime.snapshot.scanner.status == ScannerStatus.RUNNING


def test_scanner_controller_autostarts_configured_port() -> None:
    """Проверяет автозапуск выбранного COM/SPP-порта."""

    runtime = _runtime()
    worker = FakeScannerWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=worker,
        initial_port="COM8",
    )

    controller.start_if_configured()

    assert worker.last_config is not None
    assert worker.last_config.port == "COM8"
    assert runtime.snapshot.scanner.status == ScannerStatus.RUNNING


def test_scanner_controller_autostart_without_port_reports_setup() -> None:
    """Проверяет понятный статус автозапуска без выбранного порта."""

    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=FakeScannerWorker(),
    )

    controller.start_if_configured()

    assert controller.state.status_message == "Сканер не выбран. Настройте COM/SPP-порт."
    assert controller.state.is_running is False


def test_scanner_controller_reports_missing_port() -> None:
    """Проверяет ошибку запуска без выбранного порта."""

    runtime = _runtime()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=FakeScannerWorker(),
    )

    controller.start()

    assert controller.state.error_message == "Выберите COM/SPP-порт сканера"
    assert runtime.snapshot.scanner.status == ScannerStatus.ERROR


def test_scanner_controller_stop_updates_runtime() -> None:
    """Проверяет остановку сканера."""

    runtime = _runtime()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=FakeScannerWorker(),
        initial_port="COM7",
    )

    controller.start()
    controller.stop()

    assert controller.state.is_running is False
    assert runtime.snapshot.scanner.status == ScannerStatus.STOPPED


def test_scanner_controller_forwards_scanned_code() -> None:
    """Проверяет проброс кода наружу через signal."""

    worker = FakeScannerWorker()
    controller = ScannerController(runtime_controller=_runtime(), scanner_worker=worker)
    received: list[str] = []
    controller.code_scanned.connect(received.append)

    worker.code_scanned.emit("CODE")

    assert received == ["CODE"]
