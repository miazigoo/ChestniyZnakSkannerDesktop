"""COM/SPP-реализация сканера на pyserial."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol

import serial

from chestniy_znak_desktop.scanner.base import ScannerConfig
from chestniy_znak_desktop.scanner.scan_assembler import ScanAssembler, ScanAssemblerConfig


class SerialLike(Protocol):
    """Минимальный контракт serial-объекта для чтения сканера."""

    is_open: bool

    def read(self, size: int = 1) -> bytes:
        """Читает байты из serial-порта."""

    def close(self) -> None:
        """Закрывает serial-порт."""


SerialFactory = Callable[..., SerialLike]


class SerialScanner:
    """Читает DataMatrix-строки из serial-порта."""

    def __init__(
        self,
        config: ScannerConfig,
        on_code: Callable[[str], None],
        on_error: Callable[[Exception], None] | None = None,
        serial_factory: SerialFactory | None = None,
    ) -> None:
        """Создает сканер с callback для готовых кодов."""

        self._config = config
        self._on_code = on_code
        self._on_error = on_error
        self._serial_factory = serial_factory or serial.Serial
        self._assembler = ScanAssembler(
            ScanAssemblerConfig(
                encoding=config.encoding,
                idle_flush_sec=config.idle_flush_sec,
                dedupe_window_sec=config.dedupe_window_sec,
                terminators=config.terminators,
            )
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._serial: SerialLike | None = None

    def start(self) -> None:
        """Запускает фоновое чтение serial-порта."""

        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="SerialScanner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает фоновое чтение и закрывает порт."""

        self._stop_event.set()
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        """Открывает порт и читает байты до терминатора строки."""

        try:
            self._serial = self._serial_factory(
                port=self._config.port,
                baudrate=self._config.baudrate,
                timeout=self._config.timeout_sec,
            )
            while not self._stop_event.is_set():
                chunk = self._serial.read(1)
                if chunk:
                    self._emit_codes(self._assembler.feed(chunk))
                    continue
                code = self._assembler.flush_if_idle()
                if code is not None:
                    self._on_code(code)
        except Exception as exc:  # pragma: no cover - защитный слой вокруг внешнего порта.
            if not self._stop_event.is_set() and self._on_error is not None:
                self._on_error(exc)

    def _emit_codes(self, codes: list[str]) -> None:
        """Передает готовые коды подписчику сканера."""

        for code in codes:
            self._on_code(code)
