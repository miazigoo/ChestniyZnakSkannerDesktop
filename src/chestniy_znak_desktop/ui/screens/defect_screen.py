"""Экран отправки кода в брак."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.defect_controller import DefectUiState


class DefectScreen(QWidget):
    """Показывает результат сценария брака по скану."""

    def __init__(self) -> None:
        """Создает экран брака с журналом результата."""

        super().__init__()
        self._title = QLabel("Брак")
        self._status = QLabel("Ожидание скана кода")
        self._result = QLabel("")
        self._error = QLabel("")
        self._last_code = QLabel("Код: -")
        self._order = QLabel("Заказ: -")
        self._device = QLabel("Устройство: -")
        self._removed_box = QLabel("")
        self._warnings = QLabel("")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status)
        layout.addWidget(self._result)
        layout.addWidget(self._error)
        layout.addWidget(self._last_code)
        layout.addWidget(self._order)
        layout.addWidget(self._device)
        layout.addWidget(self._removed_box)
        layout.addWidget(self._warnings)
        layout.addWidget(self._log)

    def apply_state(self, state: DefectUiState) -> None:
        """Обновляет экран брака из состояния контроллера."""

        self._status.setText(state.status_message)
        self._result.setText(state.result_message)
        self._error.setText(state.error_message)
        self._last_code.setText(f"Код: {state.last_visible_code or '-'}")
        self._order.setText(f"Заказ: {state.order_name or '-'}")
        self._device.setText(f"Устройство: {state.device_name or '-'}")
        self._removed_box.setText(state.removed_box_message)
        self._warnings.setText("; ".join(state.warnings))
        self._log.setPlainText("\n".join(state.log))
