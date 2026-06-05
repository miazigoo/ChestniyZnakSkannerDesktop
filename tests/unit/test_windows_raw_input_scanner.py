"""Tests for Windows Raw Input scanner source."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from chestniy_znak_desktop.domain.scanner_normalizer import GS  # noqa: E402
from chestniy_znak_desktop.scanner.windows_raw_input_scanner import (  # noqa: E402
    WindowsRawInputScanner,
)
from PySide6.QtCore import QObject, Signal  # noqa: E402


class _FakeFallbackScanner(QObject):
    """Fake low-level HID fallback scanner."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        """Create fake fallback scanner."""

        super().__init__()
        self.is_running = False

    def start(self) -> None:
        """Mark fallback as running."""

        self.is_running = True
        self.started.emit()

    def stop(self) -> None:
        """Mark fallback as stopped."""

        self.is_running = False
        self.stopped.emit()


def test_windows_raw_input_restores_missing_0104_prefix() -> None:
    """Checks Raw Input emits repaired scanner input."""

    scanner = WindowsRawInputScanner()
    received: list[str] = []
    scanner.code_scanned.connect(received.append)

    scanner._emit_code(1, f"630626190739215SERIAL{GS}93ABCD", source="raw")  # noqa: SLF001

    assert received == [f"0104630626190739215SERIAL{GS}93ABCD"]


def test_windows_raw_input_drops_malformed_gs1_like_code() -> None:
    """Checks Raw Input does not forward broken 01-prefixed chunks."""

    scanner = WindowsRawInputScanner()
    received: list[str] = []
    scanner.code_scanned.connect(received.append)

    scanner._emit_code(  # noqa: SLF001
        1,
        f"010463030626173739215BROKEN{GS}93ABCD",
        source="raw",
    )

    assert received == []


def test_windows_raw_input_forwards_fallback_codes() -> None:
    """Checks keyboard hook fallback can still feed scans when Raw Input is silent."""

    fallback = _FakeFallbackScanner()
    scanner = WindowsRawInputScanner(fallback_scanner=fallback)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)

    fallback.code_scanned.emit(f"0104630626190739215SERIAL{GS}93ABCD")

    assert received == [f"0104630626190739215SERIAL{GS}93ABCD"]
