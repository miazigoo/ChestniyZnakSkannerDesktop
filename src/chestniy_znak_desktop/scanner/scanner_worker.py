"""Qt-адаптер для событий сканера."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.scanner.base import ScannerConfig
from chestniy_znak_desktop.scanner.serial_scanner import SerialScanner


class ScannerWorker(QObject):
    """Передает считанные сканером коды в Qt signal."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """Создает worker без активного подключения к сканеру."""

        super().__init__(parent)
        self._scanner: SerialScanner | None = None

    def emit_code(self, code: str) -> None:
        """Публикует строку кода для UI и сервисов."""

        self.code_scanned.emit(code)

    def start_serial(self, config: ScannerConfig) -> None:
        """Запускает чтение COM/SPP-сканера с указанными настройками."""

        self.stop()
        self._scanner = SerialScanner(
            config=config,
            on_code=self.code_scanned.emit,
            on_error=lambda exc: self.error_occurred.emit(str(exc)),
            on_started=self.started.emit,
        )
        self._scanner.start()

    def stop(self) -> None:
        """Останавливает активный источник сканов."""

        if self._scanner is None:
            return
        self._scanner.stop()
        self._scanner = None
        self.stopped.emit()
