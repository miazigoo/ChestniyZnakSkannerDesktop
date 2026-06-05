"""Qt-адаптер для событий сканера."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.scanner.base import ScannerConfig
from chestniy_znak_desktop.scanner.serial_scanner import SerialScanner


class ScannerWorker(QObject):
    """Передает считанные сканером коды в Qt signal."""

    code_scanned = Signal(str)
    code_scanned_from_port = Signal(str, str)
    error_occurred = Signal(str)
    error_occurred_from_port = Signal(str, str)
    started = Signal()
    started_port = Signal(str)
    stopped = Signal()
    stopped_port = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Создает worker без активного подключения к сканеру."""

        super().__init__(parent)
        self._scanners: dict[str, SerialScanner] = {}

    def emit_code(self, code: str) -> None:
        """Публикует строку кода для UI и сервисов."""

        self.code_scanned.emit(code)

    def start_serial(self, config: ScannerConfig) -> None:
        """Запускает чтение COM/SPP-сканера с указанными настройками."""

        if config.port in self._scanners:
            return
        port = config.port

        def on_code(code: str) -> None:
            self._emit_code(port, code)

        def on_error(exc: Exception) -> None:
            self._emit_error(port, exc)

        def on_started() -> None:
            self._emit_started(port)

        scanner = SerialScanner(
            config=config,
            on_code=on_code,
            on_error=on_error,
            on_started=on_started,
        )
        self._scanners[port] = scanner
        scanner.start()

    def stop(self) -> None:
        """Останавливает все активные serial-источники сканов."""

        if not self._scanners:
            return
        for port, scanner in list(self._scanners.items()):
            scanner.stop()
            self._scanners.pop(port, None)
            self.stopped_port.emit(port)
        self.stopped.emit()

    def _emit_code(self, port: str, code: str) -> None:
        """Публикует код с привязкой к serial-порту."""

        self.code_scanned_from_port.emit(port, code)
        self.code_scanned.emit(code)

    def _emit_started(self, port: str) -> None:
        """Публикует старт конкретного serial-порта."""

        self.started_port.emit(port)
        self.started.emit()

    def _emit_error(self, port: str, exc: Exception) -> None:
        """Публикует ошибку конкретного serial-порта."""

        message = str(exc)
        self._scanners.pop(port, None)
        self.error_occurred_from_port.emit(port, message)
        self.error_occurred.emit(message)
        if not self._scanners:
            self.stopped.emit()
