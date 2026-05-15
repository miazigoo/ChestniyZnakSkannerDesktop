"""HID keyboard wedge источник сканов."""

from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)


class HidKeyboardScanner(QObject):
    """Собирает быстрые HID-клавиатурные события в строку сканера."""

    code_scanned = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        qt_app: QApplication,
        idle_flush_ms: int = 250,
        dedupe_window_ms: int = 750,
        parent: QObject | None = None,
    ) -> None:
        """Создает HID-источник сканов поверх глобального event filter Qt."""

        super().__init__(parent)
        self._qt_app = qt_app
        self._idle_flush_ms = idle_flush_ms
        self._dedupe_window_sec = dedupe_window_ms / 1000
        self._buffer: list[str] = []
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0
        self._is_running = False
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._flush_buffer)

    @property
    def is_running(self) -> bool:
        """Возвращает `True`, если HID-источник установлен в QApplication."""

        return self._is_running

    def start(self) -> None:
        """Устанавливает Qt event filter для HID keyboard scanner."""

        if self._is_running:
            return
        self._qt_app.installEventFilter(self)
        self._is_running = True
        self.started.emit()

    def stop(self) -> None:
        """Удаляет Qt event filter и очищает текущий буфер."""

        if not self._is_running:
            return
        self._qt_app.removeEventFilter(self)
        self._idle_timer.stop()
        self._buffer.clear()
        self._is_running = False
        self.stopped.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Перехватывает печатные клавиши сканера и терминаторы."""

        if not self._is_running or event.type() != QEvent.Type.KeyPress:
            return False
        if self._is_editable_widget(watched):
            return False
        key_event = event
        if not isinstance(key_event, QKeyEvent) or key_event.isAutoRepeat():
            return False
        text = key_event.text()
        if key_event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Tab,
        }:
            had_buffer = bool(self._buffer)
            self._flush_buffer()
            return had_buffer
        if not text or text in {"\r", "\n", "\t"}:
            return False
        if len(text) != 1 or not text.isprintable():
            return False
        self._buffer.append(text)
        self._idle_timer.start(self._idle_flush_ms)
        return True

    def _flush_buffer(self) -> None:
        """Публикует накопленный HID-код, если буфер не пустой."""

        if not self._buffer:
            return
        code = "".join(self._buffer).strip()
        self._buffer.clear()
        if not code:
            return
        now = time.monotonic()
        if (
            code == self._last_emitted_code
            and now - self._last_emitted_at < self._dedupe_window_sec
        ):
            return
        self._last_emitted_code = code
        self._last_emitted_at = now
        self.code_scanned.emit(code)

    @staticmethod
    def _is_editable_widget(watched: QObject) -> bool:
        """Проверяет, что пользователь сейчас редактирует поле формы."""

        widget = watched if isinstance(watched, QWidget) else QApplication.focusWidget()
        return isinstance(
            widget,
            (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox),
        )
