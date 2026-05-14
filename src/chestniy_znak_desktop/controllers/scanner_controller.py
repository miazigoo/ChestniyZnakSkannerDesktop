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
        initial_port: str = "",
        initial_baudrate: int = 9600,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер сканера."""

        super().__init__(parent)
        self._runtime_controller = runtime_controller
        self._scanner_worker = scanner_worker or ScannerWorker()
        self._state = ScannerUiState(
            selected_port=initial_port,
            baudrate=initial_baudrate,
        )
        self._scanner_worker.code_scanned.connect(self.code_scanned.emit)
        self._scanner_worker.error_occurred.connect(self._on_scanner_error)
        self._scanner_worker.started.connect(self._on_scanner_started)
        self._scanner_worker.stopped.connect(self._on_scanner_stopped)

    @property
    def state(self) -> ScannerUiState:
        """Возвращает текущее состояние сканера."""

        return self._state

    def refresh_ports(self) -> None:
        """Обновляет список доступных COM/SPP-портов."""

        ports = serial_ports.list_serial_ports()
        selected_port = self._state.selected_port
        if not selected_port and ports:
            selected_port = ports[0].device
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

        if self._state.is_running:
            return
        if not self._state.selected_port:
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

    def stop(self) -> None:
        """Останавливает чтение сканера."""

        self._scanner_worker.stop()

    def _on_scanner_started(self) -> None:
        """Обрабатывает успешный старт worker."""

        self._runtime_controller.set_scanner_running(self._state.selected_port)
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=True,
                status_message=f"Сканер запущен: {self._state.selected_port}",
            )
        )

    def _on_scanner_stopped(self) -> None:
        """Обрабатывает остановку worker."""

        self._runtime_controller.set_scanner_stopped()
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=False,
                status_message="Сканер остановлен",
            )
        )

    def _on_scanner_error(self, message: str) -> None:
        """Обрабатывает ошибку чтения serial-порта."""

        self._runtime_controller.set_scanner_error(message)
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=False,
                status_message="Ошибка сканера",
                error_message=message,
            )
        )

    def _set_state(self, state: ScannerUiState) -> None:
        """Сохраняет и публикует состояние сканера."""

        self._state = state
        self.state_changed.emit(state)
