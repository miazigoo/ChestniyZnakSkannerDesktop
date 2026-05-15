"""HID keyboard wedge источник сканов."""

from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

from chestniy_znak_desktop.domain.scanner_normalizer import GS


class HidKeyboardScanner(QObject):
    """Собирает быстрые HID-клавиатурные события в строку сканера."""

    code_scanned = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        idle_flush_ms: int = 250,
        dedupe_window_ms: int = 750,
        parent: QObject | None = None,
    ) -> None:
        """Создает HID-источник сканов поверх event filter виджетов окна."""

        super().__init__(parent)
        self._idle_flush_ms = idle_flush_ms
        self._dedupe_window_sec = dedupe_window_ms / 1000
        self._buffer: list[str] = []
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0
        self._is_running = False
        self._root_widget: QWidget | None = None
        self._filtered_widgets: set[QWidget] = set()
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._flush_buffer)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_widget_filters)

    @property
    def is_running(self) -> bool:
        """Возвращает `True`, если HID-источник установлен на виджеты окна."""

        return self._is_running

    def bind_root(self, widget: QWidget) -> None:
        """Привязывает HID-источник к корневому окну приложения."""

        self._root_widget = widget
        if self._is_running:
            self._refresh_widget_filters()

    def start(self) -> None:
        """Устанавливает Qt event filter для HID keyboard scanner."""

        if self._is_running:
            return
        self._is_running = True
        self._refresh_widget_filters()
        self._refresh_timer.start()
        self.started.emit()

    def stop(self) -> None:
        """Удаляет Qt event filter и очищает текущий буфер."""

        if not self._is_running:
            return
        self._refresh_timer.stop()
        self._remove_widget_filters()
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
        if self._is_gs_key(key_event):
            self._buffer.append(GS)
            self._idle_timer.start(self._idle_flush_ms)
            return True
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
        if text == GS:
            self._buffer.append(GS)
            self._idle_timer.start(self._idle_flush_ms)
            return True
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
    def _is_gs_key(key_event: QKeyEvent) -> bool:
        """Проверяет HID-ввод ASCII GS через типичную комбинацию Ctrl+]."""

        return key_event.key() == Qt.Key.Key_BracketRight and bool(
            key_event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )

    @staticmethod
    def _is_editable_widget(watched: QObject) -> bool:
        """Проверяет, что пользователь сейчас редактирует поле формы."""

        widget = watched if isinstance(watched, QWidget) else None
        return isinstance(
            widget,
            (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox),
        )

    def _refresh_widget_filters(self) -> None:
        """Устанавливает фильтр на корневой виджет и его дочерние виджеты."""

        if self._root_widget is None:
            return
        widgets = {self._root_widget, *self._root_widget.findChildren(QWidget)}
        for widget in widgets - self._filtered_widgets:
            widget.installEventFilter(self)
        for widget in self._filtered_widgets - widgets:
            widget.removeEventFilter(self)
        self._filtered_widgets = widgets

    def _remove_widget_filters(self) -> None:
        """Удаляет фильтр со всех ранее зарегистрированных виджетов."""

        for widget in list(self._filtered_widgets):
            widget.removeEventFilter(self)
        self._filtered_widgets.clear()
