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
    code_scanned_from_port = Signal(str, str)
    error_occurred = Signal(str)
    error_occurred_from_port = Signal(str, str)
    started = Signal()
    started_port = Signal(str)
    stopped = Signal()
    stopped_port = Signal(str)

    def __init__(self) -> None:
        """Создает fake worker."""

        super().__init__()
        self.last_config: ScannerConfig | None = None
        self.configs: list[ScannerConfig] = []
        self.active_ports: list[str] = []

    def start_serial(self, config: ScannerConfig) -> None:
        """Запоминает конфиг и публикует старт."""

        self.last_config = config
        self.configs.append(config)
        self.active_ports.append(config.port)
        self.started_port.emit(config.port)

    def stop(self) -> None:
        """Публикует остановку."""

        for port in list(self.active_ports):
            self.stopped_port.emit(port)
        self.active_ports.clear()
        self.stopped.emit()

    def emit_code(self, code: str, port: str | None = None) -> None:
        """Публикует fake-код из конкретного serial-порта."""

        source_port = port or (self.last_config.port if self.last_config else "COM")
        self.code_scanned_from_port.emit(source_port, code)

    def emit_error(self, message: str, port: str | None = None) -> None:
        """Публикует fake-ошибку из конкретного serial-порта."""

        source_port = port or (self.last_config.port if self.last_config else "COM")
        if source_port in self.active_ports:
            self.active_ports.remove(source_port)
        self.error_occurred_from_port.emit(source_port, message)


class FakeHidKeyboardWorker(QObject):
    """Fake HID keyboard scanner worker."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        """Создает fake HID worker."""

        super().__init__()
        self.is_running = False
        self.start_count = 0

    def start(self) -> None:
        """Публикует старт HID worker."""

        self.start_count += 1
        self.is_running = True
        self.started.emit()

    def stop(self) -> None:
        """Публикует остановку HID worker."""

        self.is_running = False
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


def test_scanner_refresh_reselects_usb_serial_after_replug(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет автовыбор нового ttyACM, если старый порт исчез после переподключения."""

    monkeypatch.setattr(
        serial_ports,
        "list_serial_ports",
        lambda: [ScannerPort(device="/dev/ttyACM1", description="SCAN CDC")],
    )
    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=FakeScannerWorker(),
        initial_port="/dev/ttyACM0",
    )

    controller.refresh_ports()

    assert controller.state.selected_port == "/dev/ttyACM1"


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


def test_scanner_controller_autostarts_all_available_serial_ports(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет параллельный запуск USB COM и Bluetooth SPP."""

    monkeypatch.setattr(
        serial_ports,
        "list_serial_ports",
        lambda: [
            ScannerPort(device="/dev/rfcomm0", description="Bluetooth SPP"),
            ScannerPort(device="/dev/ttyACM1", description="SCAN CDC"),
            ScannerPort(
                device="/dev/ttyS0",
                description="Linux system serial port",
                auto_selectable=False,
            ),
        ],
    )
    runtime = _runtime()
    worker = FakeScannerWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=worker,
        initial_port="/dev/ttyACM1",
    )

    controller.refresh_ports()
    controller.start_if_configured()

    assert [config.port for config in worker.configs] == ["/dev/rfcomm0", "/dev/ttyACM1"]
    assert controller.state.active_serial_ports == ["/dev/rfcomm0", "/dev/ttyACM1"]
    assert controller.state.serial_running is True
    assert runtime.snapshot.scanner.port == "COM: /dev/rfcomm0, /dev/ttyACM1"


def test_scanner_controller_retries_serial_after_usb_replug(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет автопереподключение COM/SPP, если ttyACM сменился после USB replug."""

    runtime = _runtime()
    worker = FakeScannerWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=worker,
        initial_port="/dev/ttyACM0",
    )
    controller.start()
    monkeypatch.setattr(
        serial_ports,
        "list_serial_ports",
        lambda: [ScannerPort(device="/dev/ttyACM1", description="SCAN CDC")],
    )

    worker.emit_error("device disconnected", port="/dev/ttyACM0")
    controller._serial_retry_timer.stop()  # noqa: SLF001
    controller._retry_serial()  # noqa: SLF001

    assert worker.last_config is not None
    assert worker.last_config.port == "/dev/ttyACM1"
    assert controller.state.serial_running is True
    assert runtime.snapshot.scanner.status == ScannerStatus.RUNNING


def test_scanner_controller_keeps_hid_when_serial_starts() -> None:
    """Проверяет, что HID и COM/SPP могут работать одновременно."""

    runtime = _runtime()
    worker = FakeScannerWorker()
    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=worker,
        hid_keyboard_worker=hid,
        initial_port="COM5",
    )

    controller.start_hid_keyboard()
    controller.start()

    assert hid.is_running is True
    assert worker.last_config is not None
    assert worker.last_config.port == "COM5"
    assert controller.state.is_running is True
    assert controller.state.serial_running is True
    assert controller.state.hid_running is True
    assert runtime.snapshot.scanner.port == "COM: COM5 | HID keyboard"


def test_scanner_controller_runs_hid_without_com_port() -> None:
    """Проверяет HID-режим без выбранного COM/SPP-порта."""

    runtime = _runtime()
    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=FakeScannerWorker(),
        hid_keyboard_worker=hid,
    )

    controller.start_hid_keyboard()
    controller.start_if_configured()

    assert controller.state.is_running is True
    assert controller.state.status_message == "HID-сканер активен. COM/SPP-порт не выбран."
    assert runtime.snapshot.scanner.status == ScannerStatus.RUNNING
    assert runtime.snapshot.scanner.port == "HID keyboard"


def test_scanner_controller_forwards_hid_scanned_code() -> None:
    """Проверяет проброс HID-кода наружу через общий signal."""

    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=FakeScannerWorker(),
        hid_keyboard_worker=hid,
    )
    received: list[str] = []
    controller.code_scanned.connect(received.append)

    hid.code_scanned.emit("HID-CODE")

    assert received == ["HID-CODE"]


def test_scanner_controller_deduplicates_exact_cross_source_code() -> None:
    """Проверяет подавление точного дубля между COM/SPP и HID."""

    worker = FakeScannerWorker()
    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=worker,
        hid_keyboard_worker=hid,
    )
    received: list[str] = []
    controller.code_scanned.connect(received.append)

    worker.emit_code("CODE")
    hid.code_scanned.emit("CODE")

    assert received == ["CODE"]


def test_scanner_controller_allows_different_cross_source_code() -> None:
    """Проверяет, что разные коды с разных источников не теряются."""

    worker = FakeScannerWorker()
    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=worker,
        hid_keyboard_worker=hid,
    )
    received: list[str] = []
    controller.code_scanned.connect(received.append)

    worker.emit_code("BAD-CODE")
    hid.code_scanned.emit("GOOD-CODE")

    assert received == ["BAD-CODE", "GOOD-CODE"]


def test_scanner_controller_reports_hid_error() -> None:
    """Проверяет отображение ошибки HID worker."""

    runtime = _runtime()
    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=runtime,
        scanner_worker=FakeScannerWorker(),
        hid_keyboard_worker=hid,
    )

    hid.start()
    hid.error_occurred.emit("hook failed")

    assert controller.state.is_running is False
    assert controller.state.status_message == "Ошибка HID-сканера"
    assert controller.state.error_message == "hook failed"
    assert runtime.snapshot.scanner.status == ScannerStatus.ERROR


def test_scanner_controller_retries_hid_after_error() -> None:
    """Проверяет автоперезапуск HID worker после ошибки."""

    hid = FakeHidKeyboardWorker()
    controller = ScannerController(
        runtime_controller=_runtime(),
        scanner_worker=FakeScannerWorker(),
        hid_keyboard_worker=hid,
    )

    controller.start_hid_keyboard()
    hid.error_occurred.emit("device disconnected")
    hid.is_running = False
    controller._retry_hid_keyboard()  # noqa: SLF001

    assert hid.start_count == 2
    assert controller.state.is_running is True


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

    worker.emit_code("CODE")

    assert received == ["CODE"]
