"""Windows HID scanner source."""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from chestniy_znak_desktop.scanner.hid_keyboard_scanner import HidKeyboardScanner
from chestniy_znak_desktop.scanner.hid_process_worker import (
    DEFAULT_HID_IDLE_FLUSH_MS,
    HidProcessScanner,
)

logger = logging.getLogger(__name__)


class WindowsHidScanner(QObject):
    """Captures Windows HID keyboard wedge scans through the global hook only."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        process_scanner: HidProcessScanner | None = None,
        fallback_scanner: HidKeyboardScanner | None = None,
        dedupe_window_ms: int = 750,
        idle_flush_ms: int = DEFAULT_HID_IDLE_FLUSH_MS,
        fallback_emit_delay_ms: int | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create Windows HID source without focused-window fallback emission."""

        super().__init__(parent)
        self._process_scanner = process_scanner or HidProcessScanner(idle_flush_ms=idle_flush_ms)
        self._fallback_scanner = fallback_scanner
        self._dedupe_window_sec = dedupe_window_ms / 1000
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0
        self._is_running = False
        self._process_scanner.code_scanned.connect(self._emit_process_code)
        self._process_scanner.error_occurred.connect(self._on_process_error)
        self._process_scanner.stopped.connect(self._on_process_stopped)
        _ = fallback_emit_delay_ms
        if self._fallback_scanner is not None:
            self._fallback_scanner.code_scanned.connect(self._emit_fallback_code)

    @property
    def is_running(self) -> bool:
        """Return True while the Windows process hook is active."""

        return self._is_running

    def bind_root(self, widget: QWidget) -> None:
        """Keep API compatibility; focused-window fallback is disabled."""

        if self._fallback_scanner is not None:
            self._fallback_scanner.bind_root(widget)

    def start(self) -> None:
        """Start the global hook."""

        if self._is_running:
            return
        self._is_running = True
        self._process_scanner.start()
        self.started.emit()

    def stop(self) -> None:
        """Stop Windows HID capture."""

        if not self._is_running:
            return
        self._is_running = False
        self._process_scanner.stop()
        if self._fallback_scanner is not None:
            self._fallback_scanner.stop()
        self.stopped.emit()

    def _emit_process_code(self, code: str) -> None:
        """Emit process-hook scanner code."""

        self._emit_code(code)

    def _emit_code(self, code: str) -> None:
        """Emit a scanner code once within the dedupe window."""

        now = time.monotonic()
        if (
            code == self._last_emitted_code
            and now - self._last_emitted_at < self._dedupe_window_sec
        ):
            return
        self._last_emitted_code = code
        self._last_emitted_at = now
        self.code_scanned.emit(code)

    def _emit_fallback_code(self, code: str) -> None:
        """Ignore focused-window fallback scans."""

        logger.warning("Windows HID focused-window fallback scan ignored: %r", code)

    def _on_process_error(self, message: str) -> None:
        """Report process hook errors without enabling focused-window fallback."""

        if self._is_running:
            logger.error("Windows HID process scanner failed; fallback disabled: %s", message)
            self.error_occurred.emit(message)
            return
        self.error_occurred.emit(message)

    def _on_process_stopped(self) -> None:
        """Report unexpected process hook stop without enabling fallback."""

        if not self._is_running:
            return
        self._is_running = False
        message = "Windows HID process scanner stopped; fallback disabled"
        logger.error("%s", message)
        self.error_occurred.emit(message)
        self.stopped.emit()
