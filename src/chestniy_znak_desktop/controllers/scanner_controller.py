"""Контроллер COM/SPP-сканера."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from PySide6.QtCore import QObject, QTimer, Signal

from chestniy_znak_desktop.domain.scanner_normalizer import visible
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.scanner.base import ScannerConfig, ScannerPort
from chestniy_znak_desktop.scanner.scanner_worker import ScannerWorker
from chestniy_znak_desktop.scanner import serial_ports

logger = logging.getLogger(__name__)
SOURCE_DEDUPE_WINDOW_SEC = 0.75
HID_RETRY_DELAY_MS = 2_000
SERIAL_RETRY_DELAY_MS = 2_000
SCAN_LOG_PREFIX_LEN = 8
SCAN_LOG_SUFFIX_LEN = 4


def _scan_log_preview(code: str) -> str:
    """Return a non-sensitive scan preview for logs."""

    printable = visible(code)
    if len(printable) <= SCAN_LOG_PREFIX_LEN + SCAN_LOG_SUFFIX_LEN:
        return "<short>"
    return f"{printable[:SCAN_LOG_PREFIX_LEN]}...{printable[-SCAN_LOG_SUFFIX_LEN:]}"


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
    serial_running: bool = False
    active_serial_ports: list[str] = field(default_factory=list)
    hid_running: bool = False
    hid_devices: list[str] = field(default_factory=list)
    status_message: str = field(default_factory=lambda: tr("settings.scanner.notRunning"))
    error_message: str = ""


class ScannerController(QObject):
    """Управляет serial-сканером и публикует готовые коды."""

    state_changed = Signal(ScannerUiState)
    code_scanned = Signal(str)
    code_scanned_at = Signal(str, float, int)

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
        self._active_serial_ports: set[str] = set()
        self._hid_running = False
        self._serial_autostart_requested = False
        self._hid_autostart_requested = False
        self._last_emitted_code = ""
        self._last_emitted_source = ""
        self._last_emitted_at = 0.0
        self._serial_retry_timer = QTimer(self)
        self._serial_retry_timer.setSingleShot(True)
        self._serial_retry_timer.setInterval(SERIAL_RETRY_DELAY_MS)
        self._serial_retry_timer.timeout.connect(self._retry_serial)
        self._hid_retry_timer = QTimer(self)
        self._hid_retry_timer.setSingleShot(True)
        self._hid_retry_timer.setInterval(HID_RETRY_DELAY_MS)
        self._hid_retry_timer.timeout.connect(self._retry_hid_keyboard)
        self._state = ScannerUiState(
            selected_port=initial_port,
            baudrate=initial_baudrate,
        )
        serial_code_from_port = getattr(self._scanner_worker, "code_scanned_from_port", None)
        if serial_code_from_port is not None:
            serial_code_from_port.connect(self._emit_serial_code_from_port)
        else:
            self._scanner_worker.code_scanned.connect(self._emit_serial_code)
        serial_error_from_port = getattr(self._scanner_worker, "error_occurred_from_port", None)
        if serial_error_from_port is not None:
            serial_error_from_port.connect(self._on_serial_port_error)
        else:
            self._scanner_worker.error_occurred.connect(self._on_scanner_error)
        serial_started_port = getattr(self._scanner_worker, "started_port", None)
        if serial_started_port is not None:
            serial_started_port.connect(self._on_serial_port_started)
        else:
            self._scanner_worker.started.connect(self._on_scanner_started)
        serial_stopped_port = getattr(self._scanner_worker, "stopped_port", None)
        if serial_stopped_port is not None:
            serial_stopped_port.connect(self._on_serial_port_stopped)
        else:
            self._scanner_worker.stopped.connect(self._on_scanner_stopped)
        if self._hid_keyboard_worker is not None:
            hid_code_scanned_at = getattr(self._hid_keyboard_worker, "code_scanned_at", None)
            if hid_code_scanned_at is not None:
                hid_code_scanned_at.connect(self._emit_hid_code_at)
            else:
                self._hid_keyboard_worker.code_scanned.connect(self._emit_hid_code)
            self._hid_keyboard_worker.started.connect(self._on_hid_keyboard_started)
            self._hid_keyboard_worker.stopped.connect(self._on_hid_keyboard_stopped)
            hid_error = getattr(self._hid_keyboard_worker, "error_occurred", None)
            if hid_error is not None:
                hid_error.connect(self._on_hid_keyboard_error)

    @property
    def state(self) -> ScannerUiState:
        """Возвращает текущее состояние сканера."""

        return self._state

    def refresh_ports(self) -> None:
        """Обновляет список доступных COM/SPP-портов."""

        ports = serial_ports.list_serial_ports()
        selected_port = self._state.selected_port
        known_devices = {port.device for port in ports}
        if ports and (
            not selected_port or (selected_port not in known_devices and not self._serial_running)
        ):
            selected_port = self._auto_selected_port(ports)
        self._set_state(
            ScannerUiState(
                ports=ports,
                selected_port=selected_port,
                baudrate=self._state.baudrate,
                is_running=self._state.is_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
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
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
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
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=self._state.status_message,
                error_message=self._state.error_message,
            )
        )

    def start(self) -> None:
        """Запускает чтение выбранного COM/SPP-порта."""

        if self._state.selected_port in self._active_serial_ports:
            return
        if not self._state.selected_port:
            if self._hid_keyboard_worker is not None:
                self.start_hid_keyboard()
                return
            self._on_scanner_error(tr("settings.scanner.choosePort"))
            return
        self._serial_autostart_requested = True
        self._serial_retry_timer.stop()
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._state.is_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=tr(
                    "settings.scanner.startingCom",
                    port=self._state.selected_port,
                ),
            )
        )
        self._scanner_worker.start_serial(
            ScannerConfig(
                port=self._state.selected_port,
                baudrate=self._state.baudrate,
            )
        )

    def start_if_configured(self) -> None:
        """Автоматически запускает все доступные COM/SPP-порты."""

        ports_to_start = self._serial_ports_for_autostart()
        if ports_to_start:
            self._serial_autostart_requested = True
            self._serial_retry_timer.stop()
            self._set_state(
                ScannerUiState(
                    ports=self._state.ports,
                    selected_port=self._state.selected_port,
                    baudrate=self._state.baudrate,
                    is_running=self._state.is_running,
                    serial_running=self._serial_running,
                    active_serial_ports=self._active_serial_port_list(),
                    hid_running=self._hid_running,
                    hid_devices=self._hid_device_paths(),
                    status_message=tr("settings.scanner.startingComPorts"),
                )
            )
            for port in ports_to_start:
                self._start_serial_port(port)
            return
        if self._hid_running:
            self._publish_running_state(
                status_message=tr("settings.scanner.hidActiveNoPort"),
            )
            return
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port="",
                baudrate=self._state.baudrate,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=tr("settings.scanner.notSelected"),
            )
        )

    def stop(self) -> None:
        """Останавливает чтение сканера."""

        self._serial_autostart_requested = False
        self._serial_retry_timer.stop()
        self._scanner_worker.stop()
        self.stop_hid_keyboard()

    def start_hid_keyboard(self) -> None:
        """Запускает HID keyboard wedge источник сканов."""

        if self._hid_keyboard_worker is None:
            return
        self._hid_autostart_requested = True
        self._hid_retry_timer.stop()
        if self._hid_running:
            return
        self._hid_keyboard_worker.start()

    def stop_hid_keyboard(self) -> None:
        """Останавливает HID keyboard wedge источник сканов."""

        self._hid_autostart_requested = False
        self._hid_retry_timer.stop()
        if self._hid_keyboard_worker is None:
            return
        self._hid_keyboard_worker.stop()

    def _emit_serial_code(self, code: str) -> None:
        """Публикует serial-код с логированием источника."""

        self._emit_code_from_source("serial", code)

    def _emit_serial_code_from_port(self, port: str, code: str) -> None:
        """Публикует serial-код с логированием конкретного COM/SPP-порта."""

        self._emit_code_from_source(f"serial:{port}", code)

    def _emit_hid_code(self, code: str) -> None:
        """Публикует HID-код с логированием источника."""

        self._emit_code_from_source("hid", code)

    def _emit_hid_code_at(self, code: str, scanner_emitted_at: float, event_age_ms: int) -> None:
        """Публикует HID-код вместе с диагностикой задержки reader -> UI."""

        self._emit_code_from_source(
            "hid",
            code,
            scanner_emitted_at=scanner_emitted_at,
            event_age_ms=event_age_ms,
        )

    def _emit_code_from_source(
        self,
        source: str,
        code: str,
        *,
        scanner_emitted_at: float | None = None,
        event_age_ms: int = 0,
    ) -> None:
        """Публикует код из одного источника, подавляя точный дубль другого источника."""

        normalized = (code or "").strip()
        if not normalized:
            return
        now = time.monotonic()
        if (
            normalized == self._last_emitted_code
            and source != self._last_emitted_source
            and now - self._last_emitted_at < SOURCE_DEDUPE_WINDOW_SEC
        ):
            logger.info(
                (
                    "Scanner duplicate source scan dropped source=%s previous_source=%s "
                    "code_len=%s code_preview=%r"
                ),
                source,
                self._last_emitted_source,
                len(normalized),
                _scan_log_preview(normalized),
            )
            return
        signal_delay_ms = 0
        if scanner_emitted_at is not None:
            signal_delay_ms = max(0, int((time.monotonic() - scanner_emitted_at) * 1000))
        logger.info(
            (
                "Scanner code received source=%s signal_delay_ms=%s event_age_ms=%s "
                "code_len=%s code_preview=%r"
            ),
            source,
            signal_delay_ms,
            event_age_ms,
            len(normalized),
            _scan_log_preview(normalized),
        )
        self._last_emitted_code = normalized
        self._last_emitted_source = source
        self._last_emitted_at = now
        self.code_scanned_at.emit(
            normalized,
            scanner_emitted_at if scanner_emitted_at is not None else now,
            event_age_ms,
        )
        self.code_scanned.emit(normalized)

    def _on_scanner_started(self) -> None:
        """Обрабатывает успешный старт worker."""

        self._serial_running = True
        if self._state.selected_port:
            self._active_serial_ports.add(self._state.selected_port)
        self._publish_running_state(
            status_message=tr("settings.scanner.started", port=self._state.selected_port)
        )

    def _on_serial_port_started(self, port: str) -> None:
        """Обрабатывает успешный старт конкретного COM/SPP-порта."""

        self._active_serial_ports.add(port)
        self._serial_running = True
        self._publish_running_state(
            status_message=tr(
                "settings.scanner.comActive",
                ports=", ".join(self._active_serial_port_list()),
            )
        )

    def _on_hid_keyboard_started(self) -> None:
        """Обрабатывает старт HID keyboard wedge источника."""

        self._hid_running = True
        self._hid_retry_timer.stop()
        self._publish_running_state(status_message=tr("settings.scanner.hidActive"))

    def _on_hid_keyboard_stopped(self) -> None:
        """Обрабатывает остановку HID keyboard wedge источника."""

        self._hid_running = False
        if self._hid_autostart_requested:
            self._schedule_hid_retry("HID-сканер остановлен")
            return
        self._publish_running_state(status_message=tr("settings.scanner.hidStopped"))

    def _on_hid_keyboard_error(self, message: str) -> None:
        """Обрабатывает ошибку HID keyboard wedge источника."""

        self._hid_running = False
        if self._hid_autostart_requested:
            self._schedule_hid_retry(message)
            return
        if self._serial_running:
            self._runtime_controller.set_scanner_running(self._runtime_port_label())
        else:
            self._runtime_controller.set_scanner_error(message)
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._serial_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=tr("settings.scanner.hidErrorStatus"),
                error_message=message,
            )
        )

    def _schedule_hid_retry(self, message: str) -> None:
        """Планирует повторный запуск HID-сканера без ручного вмешательства."""

        if self._hid_keyboard_worker is None or self._hid_retry_timer.isActive():
            return
        status_message = tr(
            "settings.scanner.hidRetry",
            seconds=HID_RETRY_DELAY_MS // 1000,
        )
        if self._serial_running:
            self._runtime_controller.set_scanner_running(self._runtime_port_label())
        else:
            self._runtime_controller.set_scanner_error(f"{message}. Идет автоподключение.")
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._serial_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=status_message,
                error_message=message,
            )
        )
        self._hid_retry_timer.start()

    def _schedule_serial_retry(self, message: str) -> None:
        """Планирует повторный запуск COM/SPP после переподключения USB."""

        if self._serial_retry_timer.isActive():
            return
        status_message = tr(
            "settings.scanner.serialRetry",
            seconds=SERIAL_RETRY_DELAY_MS // 1000,
        )
        if self._serial_running or self._hid_running:
            self._runtime_controller.set_scanner_running(self._runtime_port_label())
        else:
            self._runtime_controller.set_scanner_error(f"{message}. Идет автоподключение.")
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._serial_running or self._hid_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=status_message,
                error_message=message,
            )
        )
        self._serial_retry_timer.start()

    def _retry_hid_keyboard(self) -> None:
        """Повторно запускает HID-источник, если он должен быть активен."""

        if (
            self._hid_keyboard_worker is None
            or self._hid_running
            or not self._hid_autostart_requested
        ):
            return
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._serial_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=tr("settings.scanner.retryHid"),
                error_message=self._state.error_message,
            )
        )
        self._hid_keyboard_worker.start()

    def _retry_serial(self) -> None:
        """Повторно запускает serial-источник, переобнаруживая ttyACM/ttyUSB."""

        if not self._serial_autostart_requested:
            return
        self.refresh_ports()
        ports_to_start = self._serial_ports_for_autostart()
        if not ports_to_start:
            self._schedule_serial_retry("COM/SPP-порт сканера не найден")
            return
        for port in ports_to_start:
            self._start_serial_port(port)

    def _publish_running_state(self, status_message: str) -> None:
        """Публикует агрегированное состояние COM/SPP и HID источников."""

        is_running = self._serial_running or self._hid_running
        runtime_port = self._runtime_port_label() if is_running else ""
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
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=status_message,
                error_message=self._state.error_message,
            )
        )

    def _on_scanner_stopped(self) -> None:
        """Обрабатывает остановку worker."""

        self._serial_running = False
        self._active_serial_ports.clear()
        message = (
            tr("settings.scanner.hidActive")
            if self._hid_running
            else tr("settings.scanner.stopped")
        )
        self._publish_running_state(status_message=message)

    def _on_serial_port_stopped(self, port: str) -> None:
        """Обрабатывает остановку одного COM/SPP-порта."""

        self._active_serial_ports.discard(port)
        self._serial_running = bool(self._active_serial_ports)
        message = (
            tr("settings.scanner.comStopped", port=port)
            if self._serial_running or self._hid_running
            else tr("settings.scanner.stopped")
        )
        self._publish_running_state(status_message=message)

    def _on_scanner_error(self, message: str) -> None:
        """Обрабатывает ошибку чтения serial-порта."""

        self._serial_running = False
        self._active_serial_ports.clear()
        if self._serial_autostart_requested:
            self._schedule_serial_retry(message)
            return
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
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=(
                    tr("settings.scanner.hidActiveComStopped")
                    if self._hid_running
                    else tr("settings.scanner.errorStatus")
                ),
                error_message=message,
            )
        )

    def _on_serial_port_error(self, port: str, message: str) -> None:
        """Обрабатывает ошибку чтения одного COM/SPP-порта."""

        self._active_serial_ports.discard(port)
        self._serial_running = bool(self._active_serial_ports)
        if self._serial_autostart_requested:
            self._schedule_serial_retry(f"{port}: {message}")
            return
        if self._serial_running or self._hid_running:
            self._runtime_controller.set_scanner_running(self._runtime_port_label())
        else:
            self._runtime_controller.set_scanner_error(message)
        self._set_state(
            ScannerUiState(
                ports=self._state.ports,
                selected_port=self._state.selected_port,
                baudrate=self._state.baudrate,
                is_running=self._serial_running or self._hid_running,
                serial_running=self._serial_running,
                active_serial_ports=self._active_serial_port_list(),
                hid_running=self._hid_running,
                hid_devices=self._hid_device_paths(),
                status_message=(
                    tr("settings.scanner.serialErrorPort", port=port)
                    if not self._serial_running
                    else tr("settings.scanner.comDisconnected", port=port)
                ),
                error_message=message,
            )
        )

    def _set_state(self, state: ScannerUiState) -> None:
        """Сохраняет и публикует состояние сканера."""

        self._state = state
        self.state_changed.emit(state)

    def _hid_device_paths(self) -> list[str]:
        """Возвращает список HID-устройств, которые читает текущий worker."""

        if self._hid_keyboard_worker is None:
            return []
        device_paths = getattr(self._hid_keyboard_worker, "device_paths", None)
        if device_paths is None:
            device_path = getattr(self._hid_keyboard_worker, "device_path", "")
            return [str(device_path)] if device_path else []
        return [str(path) for path in device_paths]

    def _start_serial_port(self, port: str) -> None:
        """Запускает один COM/SPP-порт, если он еще не активен."""

        if not port or port in self._active_serial_ports:
            return
        self._scanner_worker.start_serial(
            ScannerConfig(
                port=port,
                baudrate=self._state.baudrate,
            )
        )

    def _serial_ports_for_autostart(self) -> list[str]:
        """Возвращает все доступные serial-порты, которые можно держать активными."""

        candidates = [port.device for port in self._state.ports if port.auto_selectable]
        if self._state.selected_port and self._state.selected_port not in candidates:
            candidates.insert(0, self._state.selected_port)
        return [
            port for port in _ordered_unique(candidates) if port not in self._active_serial_ports
        ]

    def _active_serial_port_list(self) -> list[str]:
        """Возвращает активные COM/SPP-порты в стабильном порядке."""

        known_order = [port.device for port in self._state.ports]
        return sorted(
            self._active_serial_ports,
            key=lambda port: (
                known_order.index(port) if port in known_order else len(known_order),
                port,
            ),
        )

    def _runtime_port_label(self) -> str:
        """Возвращает краткое описание активных источников для status bar."""

        sources: list[str] = []
        if self._serial_running:
            sources.append("COM: " + ", ".join(self._active_serial_port_list()))
        if self._hid_running:
            sources.append("HID keyboard")
        return " | ".join(sources)

    @staticmethod
    def _auto_selected_port(ports: list[ScannerPort]) -> str:
        """Возвращает порт для автоподстановки, пропуская системные ttyS."""

        for port in ports:
            if port.auto_selectable:
                return port.device
        return ""


def _ordered_unique(values: list[str]) -> list[str]:
    """Возвращает список без дублей с сохранением порядка."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
