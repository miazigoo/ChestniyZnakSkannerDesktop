"""Контроллер COM/SPP-сканера."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.scanner.base import ScannerConfig, ScannerPort
from chestniy_znak_desktop.scanner.scanner_worker import ScannerWorker
from chestniy_znak_desktop.scanner import serial_ports


class ScannerWorkerProtocol(Protocol):
    """Контракт worker-слоя сканера для контроллера."""

    code_scanned: Any
    error_occurred: Any
    started: Any
    stopped: Any

    def start_serial(self, config: ScannerConfig) -> None:
        """Запускает чтение serial-порта."""

    def stop(self) -> None:
        """Останавливает чтение serial-порта."""


class HidKeyboardWorkerProtocol(Protocol):
    """Контракт HID keyboard wedge источника сканов."""

    code_scanned: Any
    started: Any
    stopped: Any

    def start(self) -> None:
        """Запускает чтение HID-клавиатурных событий."""

    def stop(self) -> None:
        """Останавливает чтение HID-клавиатурных событий."""


@dataclass(frozen=True, slots=True)
class ScannerUiState:
    """Состояние UI-настроек сканера."""

    ports: list[ScannerPort] = field(default_factory=list)
    selected_port: str = ""
    baudrate: int = 9600
    is_running: bool = False
    status_message: str = "Сканер не запущен"
    error_message: str = ""


class ScannerController(QObject):
    """Управляет serial-сканером и публикует готовые коды."""

    state_changed = Signal(ScannerUiState)
    code_scanned = Signal(str)

    def __init__(
        self,
        runtime_controller: RuntimeController,
        scanner_worker: ScannerWorkerProtocol | None = None,
        hid_keyboard_worker: HidKeyboardWorkerProtocol | None = None,
        initial_port: str = "",
        initial_baudrate: int = 9600,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер сканера."""

        super().__init__(parent)
        self._runtime_controller = runtime_controller
        self._scanner_worker = scanner_worker or ScannerWorker()
        self._hid_keyboard_worker = hid_keyboard_worker
        self._serial_running = False
        self._hid_running = False
        self._state = ScannerUiState(
            selected_port=initial_port,
            baudrate=initial_baudrate,
        )
        self._scanner_worker.code_scanned.connect(self.code_scanned.emit)
        self._scanner_worker.error_occurred.connect(self._on_scanner_error)
        self._scanner_worker.started.connect(self._on_scanner_started)
        self._scanner_worker.stopped.connect(self._on_scanner_stopped)
        if self._hid_keyboard_worker is not None:
            self._hid_keyboard_worker.code_scanned.connect(self.code_scanned.emit)
            self._hid_keyboard_worker.started.connect(self._on_hid_keyboard_started)
            self._hid_keyboard_worker.stopped.connect(self._on_hid_keyboard_stopped)

    @property
    def state(self) -> ScannerUiState:
        """Возвращает текущее состояние сканера."""

        return self._state

    def refresh_ports(self) -> None:
        """Обновляет список доступных COM/SPP-портов."""

        ports = serial_ports.list_serial_ports()
        selected_port = self._state.selected_port
        if not selected_port and ports:
            selected_port = self._auto_selected_port(ports)
        self._set_state(
            ScannerUiState(
                ports=ports,
                selected_port=selected_port,
                baudrate=self._state.baudrate,
                is_running=self._state.is_running,
                status_message=self._state.status_message,
                error_message="",
            )
        )

    def set_selected_port(self, port: str) -> None:
        """Сохраняет выбранный порт без запуска сканера."""

        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=port,
                baudrate=self._state.baudrate,
                is_running=self._state.is_running,
                status_message=self._state.status_message,
                error_message=self._state.error_message,
            )
        )

    def set_baudrate(self, baudrate: int) -> None:
        """Сохраняет скорость serial-порта."""

        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=baudrate,
                is_running=self._state.is_running,
                status_message=self._state.status_message,
                error_message=self._state.error_message,
            )
        )

    def start(self) -> None:
        """Запускает чтение выбранного COM/SPP-порта."""

        if self._serial_running:
            return
        if not self._state.selected_port:
            if self._hid_keyboard_worker is not None:
                self.start_hid_keyboard()
                return
            self._on_scanner_error("Выберите COM/SPP-порт сканера")
            return
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=False,
                status_message="Запускаем сканер...",
            )
        )
        self._scanner_worker.start_serial(
            ScannerConfig(
                port=self._state.selected_port,
                baudrate=self._state.baudrate,
            )
        )

    def start_if_configured(self) -> None:
        """Автоматически запускает сканер, если порт уже выбран."""

        if self._state.selected_port:
            self.start()
            return
        if self._hid_running:
            self._publish_running_state(
                status_message="HID-сканер активен. COM/SPP-порт не выбран.",
            )
            return
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port="",
                baudrate=self._state.baudrate,
                status_message="Сканер не выбран. Настройте COM/SPP-порт.",
            )
        )

    def stop(self) -> None:
        """Останавливает чтение сканера."""

        self._scanner_worker.stop()
        self.stop_hid_keyboard()

    def start_hid_keyboard(self) -> None:
        """Запускает HID keyboard wedge источник сканов."""

        if self._hid_keyboard_worker is None or self._hid_running:
            return
        self._hid_keyboard_worker.start()

    def stop_hid_keyboard(self) -> None:
        """Останавливает HID keyboard wedge источник сканов."""

        if self._hid_keyboard_worker is None:
            return
        self._hid_keyboard_worker.stop()

    def _on_scanner_started(self) -> None:
        """Обрабатывает успешный старт worker."""

        self._serial_running = True
        self._publish_running_state(status_message=f"Сканер запущен: {self._state.selected_port}")

    def _on_hid_keyboard_started(self) -> None:
        """Обрабатывает старт HID keyboard wedge источника."""

        self._hid_running = True
        self._publish_running_state(status_message="HID-сканер активен")

    def _on_hid_keyboard_stopped(self) -> None:
        """Обрабатывает остановку HID keyboard wedge источника."""

        self._hid_running = False
        self._publish_running_state(status_message="HID-сканер остановлен")

    def _publish_running_state(self, status_message: str) -> None:
        """Публикует агрегированное состояние COM/SPP и HID источников."""

        is_running = self._serial_running or self._hid_running
        if self._serial_running:
            runtime_port = self._state.selected_port
        elif self._hid_running:
            runtime_port = "HID keyboard"
        else:
            runtime_port = ""
        if is_running:
            self._runtime_controller.set_scanner_running(runtime_port)
        else:
            self._runtime_controller.set_scanner_stopped()
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=is_running,
                status_message=status_message,
                error_message=self._state.error_message,
            )
        )

    def _on_scanner_stopped(self) -> None:
        """Обрабатывает остановку worker."""

        self._serial_running = False
        message = "HID-сканер активен" if self._hid_running else "Сканер остановлен"
        self._publish_running_state(status_message=message)

    def _on_scanner_error(self, message: str) -> None:
        """Обрабатывает ошибку чтения serial-порта."""

        self._serial_running = False
        if self._hid_running:
            self._runtime_controller.set_scanner_running("HID keyboard")
        else:
            self._runtime_controller.set_scanner_error(message)
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._hid_running,
                status_message=(
                    "HID-сканер активен. COM/SPP не запущен."
                    if self._hid_running
                    else "Ошибка сканера"
                ),
                error_message=message,
            )
        )

    def _set_state(self, state: ScannerUiState) -> None:
        """Сохраняет и публикует состояние сканера."""

        self._state = state
        self.state_changed.emit(state)

    @staticmethod
    def _auto_selected_port(ports: list[ScannerPort]) -> str:
        """Возвращает порт для автоподстановки, пропуская системные ttyS."""

        for port in ports:
            if port.auto_selectable:
                return port.device
        return ""
