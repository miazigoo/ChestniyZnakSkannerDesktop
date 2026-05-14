"""Экран проверки DataMatrix-кода."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.verify_controller import VerifyUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class VerifyScreen(QWidget):
    """Показывает результат проверки кода по скану."""

    def __init__(self) -> None:
        """Создает экран проверки кода с журналом результата."""

        super().__init__()
        self._title = QLabel("Проверка DataMatrix")
        self._status = QLabel("Ожидание скана кода")
        self._scanner_status = QLabel("Сканер: проверяем состояние")
        self._result = QLabel("")
        self._error = QLabel("")
        self._last_code = QLabel("Код: -")
        self._technical_status = QLabel("Статус: -")
        self._order = QLabel("Заказ: -")
        self._device = QLabel("Устройство: -")
        self._warnings = QLabel("")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status)
        layout.addWidget(self._scanner_status)
        layout.addWidget(self._result)
        layout.addWidget(self._error)
        layout.addWidget(self._last_code)
        layout.addWidget(self._technical_status)
        layout.addWidget(self._order)
        layout.addWidget(self._device)
        layout.addWidget(self._warnings)
        layout.addWidget(self._log)

    def apply_state(self, state: VerifyUiState) -> None:
        """Обновляет экран проверки из состояния контроллера."""

        self._status.setText(state.status_message)
        self._result.setText(state.result_message)
        self._error.setText(state.error_message)
        self._last_code.setText(f"Код: {state.last_visible_code or '-'}")
        self._technical_status.setText(f"Статус: {state.technical_status or '-'}")
        self._order.setText(f"Заказ: {state.order_name or '-'}")
        self._device.setText(f"Устройство: {state.device_name or '-'}")
        self._warnings.setText("; ".join(state.warnings))
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для проверки."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(f"Сканер готов: {snapshot.scanner.port}")
            return
        self._scanner_status.setText("Сканер не запущен. Проверка кода заблокирована.")
