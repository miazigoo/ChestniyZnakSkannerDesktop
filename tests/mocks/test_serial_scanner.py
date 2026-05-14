"""Mock-тесты COM/SPP-сканера."""

from __future__ import annotations

import threading
import time
from collections import deque

from chestniy_znak_desktop.scanner.base import ScannerConfig
from chestniy_znak_desktop.scanner.serial_scanner import SerialScanner


class FakeSerial:
    """Fake serial-порт с заранее заданными байтами чтения."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Создает fake-порт с очередью байтов."""

        self._chunks = deque(chunks)
        self.is_open = True

    def read(self, size: int = 1) -> bytes:
        """Возвращает следующий байт или пустой результат."""

        if not self.is_open:
            return b""
        if self._chunks:
            return self._chunks.popleft()
        time.sleep(0.01)
        return b""

    def close(self) -> None:
        """Закрывает fake-порт."""

        self.is_open = False


def test_serial_scanner_reads_code_from_fake_port() -> None:
    """Проверяет чтение готового кода из fake serial-порта."""

    ready = threading.Event()
    received: list[str] = []
    fake = FakeSerial([b"C", b"O", b"D", b"E", b"\r"])

    def serial_factory(**kwargs) -> FakeSerial:  # type: ignore[no-untyped-def]
        """Возвращает fake serial вместо настоящего порта."""

        return fake

    def on_code(code: str) -> None:
        """Запоминает код и будит тестовый поток."""

        received.append(code)
        ready.set()

    scanner = SerialScanner(
        ScannerConfig(port="COM7", timeout_sec=0.01),
        on_code=on_code,
        serial_factory=serial_factory,
    )
    scanner.start()
    assert ready.wait(timeout=1.0)
    scanner.stop()
    assert received == ["CODE"]


def test_serial_scanner_reports_open_error() -> None:
    """Проверяет передачу ошибки открытия порта в callback."""

    ready = threading.Event()
    errors: list[str] = []

    def serial_factory(**kwargs) -> FakeSerial:  # type: ignore[no-untyped-def]
        """Имитирует ошибку открытия serial-порта."""

        raise OSError("port unavailable")

    def on_error(exc: Exception) -> None:
        """Запоминает ошибку scanner worker."""

        errors.append(str(exc))
        ready.set()

    scanner = SerialScanner(
        ScannerConfig(port="COM404", timeout_sec=0.01),
        on_code=lambda code: None,
        on_error=on_error,
        serial_factory=serial_factory,
    )
    scanner.start()
    assert ready.wait(timeout=1.0)
    scanner.stop()
    assert errors == ["port unavailable"]
