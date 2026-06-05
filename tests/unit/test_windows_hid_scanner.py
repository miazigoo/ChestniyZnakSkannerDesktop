"""Tests for Windows HID scanner source."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from chestniy_znak_desktop.scanner.windows_hid_scanner import WindowsHidScanner  # noqa: E402


class _FakeScanner(QObject):
    """Fake scanner source."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        """Create fake source."""

        super().__init__()
        self.is_running = False
        self.bound_widget: QWidget | None = None

    def bind_root(self, widget: QWidget) -> None:
        """Remember bound root widget."""

        self.bound_widget = widget

    def start(self) -> None:
        """Mark source as running."""

        self.is_running = True
        self.started.emit()

    def stop(self) -> None:
        """Mark source as stopped."""

        self.is_running = False
        self.stopped.emit()


def _qapp() -> QApplication:
    """Return an existing QApplication or create one."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return cast(QApplication, app)


def test_windows_hid_scanner_starts_process_only() -> None:
    """Checks that Windows HID keeps focused-window fallback emergency-only."""

    _qapp()
    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(process_scanner=process, fallback_scanner=fallback)
    root = QWidget()

    scanner.bind_root(root)
    scanner.start()

    assert process.is_running is True
    assert fallback.is_running is False
    assert fallback.bound_widget is root
    assert scanner.is_running is True


def test_windows_hid_scanner_ignores_inactive_fallback_codes() -> None:
    """Checks that fallback cannot emit while the process hook is active."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(process_scanner=process, fallback_scanner=fallback)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    process.code_scanned.emit("010460")
    fallback.code_scanned.emit("010460")

    assert received == ["010460"]


def test_windows_hid_scanner_reports_process_error_without_fallback() -> None:
    """Checks that global hook failure does not enable focused-window scanning."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(
        process_scanner=process,
        fallback_scanner=fallback,
        fallback_emit_delay_ms=0,
    )
    errors: list[str] = []
    scanner.error_occurred.connect(errors.append)
    scanner.start()

    process.error_occurred.emit("hook failed")
    fallback.code_scanned.emit("010460")

    assert errors == ["hook failed"]
    assert fallback.is_running is False
    assert scanner.is_running is True


def test_windows_hid_scanner_ignores_cyrillic_fallback_duplicate() -> None:
    """Checks that fallback layout text does not trigger wrong-layout UI modal."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(process_scanner=process, fallback_scanner=fallback)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    process.code_scanned.emit("010460")
    fallback.code_scanned.emit("йцукен")

    assert received == ["010460"]


def test_windows_hid_scanner_ignores_cyrillic_when_process_hook_is_missing() -> None:
    """Checks that focused-window layout-dependent fallback stays disabled."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(
        process_scanner=process,
        fallback_scanner=fallback,
        fallback_emit_delay_ms=0,
    )
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    process.error_occurred.emit("hook failed")
    fallback.code_scanned.emit("йцукен")

    assert fallback.is_running is False
    assert received == []


def test_windows_hid_scanner_ignores_fallback_even_before_process_arrives() -> None:
    """Checks that focused-window fallback cannot race the primary process hook."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(
        process_scanner=process,
        fallback_scanner=fallback,
        fallback_emit_delay_ms=200,
    )
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    process.error_occurred.emit("hook failed")
    fallback.code_scanned.emit("FALLBACK-CODE")
    process.code_scanned.emit("PROCESS-CODE")

    assert received == ["PROCESS-CODE"]


def test_windows_hid_scanner_reports_when_process_stops() -> None:
    """Checks that unexpected process stop does not enable emergency fallback."""

    process = _FakeScanner()
    fallback = _FakeScanner()
    scanner = WindowsHidScanner(
        process_scanner=process,
        fallback_scanner=fallback,
        fallback_emit_delay_ms=0,
    )
    received: list[str] = []
    errors: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.error_occurred.connect(errors.append)
    scanner.start()

    process.stopped.emit()
    fallback.code_scanned.emit("010460")

    assert fallback.is_running is False
    assert received == []
    assert errors == ["Windows HID process scanner stopped; fallback disabled"]
