"""Small HID keyboard scanner probe for timing and suffix diagnostics."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

LOG_PATH = Path.cwd() / "hid_scan_probe.log"
IDLE_FLUSH_MS = 1200
GS = "\x1d"


@dataclass(slots=True)
class KeySample:
    at: float
    key: int
    text: str
    modifiers: int
    autorepeat: bool


class HidProbe(QObject):
    """Captures keyboard events and groups them into scanner payloads."""

    def __init__(self, output: QPlainTextEdit) -> None:
        super().__init__()
        self._output = output
        self._buffer: list[str] = []
        self._samples: list[KeySample] = []
        self._scan_count = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(IDLE_FLUSH_MS)
        self._timer.timeout.connect(lambda: self._flush("idle"))
        LOG_PATH.write_text("", encoding="utf-8")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return False
        if not isinstance(event, QKeyEvent):
            return False

        now = time.monotonic()
        text = event.text()
        sample = KeySample(
            at=now,
            key=int(event.key()),
            text=text,
            modifiers=self._modifier_value(event.modifiers()),
            autorepeat=event.isAutoRepeat(),
        )
        self._samples.append(sample)
        self._log_key(sample)

        if event.isAutoRepeat():
            return True
        if self._is_gs_key(event):
            self._buffer.append(GS)
            self._timer.start()
            return True
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab}:
            self._flush(f"terminator key={int(event.key())} text={text!r}")
            return True
        if text in {"\r", "\n", "\t"}:
            self._flush(f"terminator text={text!r}")
            return True
        if len(text) == 1 and text.isprintable():
            self._buffer.append(text)
            self._timer.start()
            return True
        return True

    def _flush(self, reason: str) -> None:
        if not self._buffer:
            return
        now = time.monotonic()
        payload = "".join(self._buffer)
        samples = self._samples
        self._buffer = []
        self._samples = []
        self._timer.stop()

        self._scan_count += 1
        first_at = samples[0].at if samples else now
        last_at = samples[-1].at if samples else now
        gaps = [round((right.at - left.at) * 1000, 1) for left, right in zip(samples, samples[1:])]
        max_gap = max(gaps) if gaps else 0.0
        starts = payload.count("010")
        line = (
            f"SCAN {self._scan_count}: reason={reason}; len={len(payload)}; "
            f"duration_ms={(last_at - first_at) * 1000:.1f}; "
            f"flush_delay_ms={(now - last_at) * 1000:.1f}; max_gap_ms={max_gap}; "
            f"gs={payload.count(GS)}; starts_010={starts}; payload={payload!r}"
        )
        self._write(line)

    def _log_key(self, sample: KeySample) -> None:
        line = (
            f"KEY t={sample.at:.6f} key={sample.key} text={sample.text!r} "
            f"mods={sample.modifiers} autorepeat={sample.autorepeat}"
        )
        self._write(line, to_console=False)

    def _write(self, line: str, *, to_console: bool = True) -> None:
        if to_console:
            print(line, flush=True)
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
        self._output.appendPlainText(line)

    @staticmethod
    def _is_gs_key(event: QKeyEvent) -> bool:
        return event.key() == Qt.Key.Key_BracketRight and bool(
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )

    @staticmethod
    def _modifier_value(modifiers: Qt.KeyboardModifier) -> int:
        try:
            return int(modifiers.value)
        except AttributeError:
            return int(modifiers)


def main() -> int:
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("HID scan probe")
    layout = QVBoxLayout(window)
    label = QLabel(
        "Focus this window, scan codes, then send the log/output. "
        f"Idle flush: {IDLE_FLUSH_MS} ms. Log: {LOG_PATH}"
    )
    output = QPlainTextEdit()
    output.setReadOnly(True)
    layout.addWidget(label)
    layout.addWidget(output)
    probe = HidProbe(output)
    window.installEventFilter(probe)
    app.installEventFilter(probe)
    window.resize(1100, 650)
    window.show()
    output.appendPlainText("Ready. Click/focus this window and start scanning.")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
