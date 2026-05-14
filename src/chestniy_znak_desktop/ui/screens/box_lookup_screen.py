"""Экран поиска коробки по скану."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.box_lookup_controller import BoxLookupUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class BoxLookupScreen(QWidget):
    """Показывает результат поиска коробки по SSCC или ID."""

    reset_requested = Signal()

    def __init__(self) -> None:
        """Создает экран поиска коробки."""

        super().__init__()
        self._title = QLabel("Поиск коробки")
        self._status = QLabel("Сканируйте штрихкод коробки")
        self._scanner_status = QLabel("Сканер: проверяем состояние")
        self._error = QLabel("")
        self._last_code = QLabel("Последний скан: -")
        self._found = QLabel("Коробка: -")
        self._reset_button = QPushButton("Сбросить статус")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._reset_button.clicked.connect(self.reset_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status)
        layout.addWidget(self._scanner_status)
        layout.addWidget(self._error)
        layout.addWidget(self._last_code)
        layout.addWidget(self._found)
        layout.addWidget(self._reset_button)
        layout.addWidget(self._log)

    def apply_state(self, state: BoxLookupUiState) -> None:
        """Обновляет экран поиска из состояния контроллера."""

        self._status.setText(state.status_message)
        self._error.setText(state.error_message)
        self._last_code.setText(f"Последний скан: {state.last_scanned_code or '-'}")
        self._found.setText(f"Коробка: {state.found_box_summary or '-'}")
        self._reset_button.setEnabled(not state.is_busy)
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для поиска."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(f"Сканер готов: {snapshot.scanner.port}")
            return
        self._scanner_status.setText("Сканер не запущен. Поиск коробки заблокирован.")
