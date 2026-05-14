"""Экран диагностики приложения."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class DiagnosticsScreen(QWidget):
    """Показывает runtime-состояние, конфигурацию и последние логи."""

    logs_refresh_requested = Signal()

    def __init__(self) -> None:
        """Создает экран диагностики."""

        super().__init__()
        self._title = QLabel("Диагностика")
        self._status = QLabel("Диагностика готова")
        self._error = QLabel("")
        self._config = QLabel("")
        self._runtime = QLabel("")
        self._log_path = QLabel("")
        self._refresh_button = QPushButton("Обновить логи")
        self._refresh_button.clicked.connect(self.logs_refresh_requested.emit)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status)
        layout.addWidget(self._error)
        layout.addWidget(self._config)
        layout.addWidget(self._runtime)
        layout.addWidget(self._log_path)
        layout.addWidget(self._refresh_button)
        layout.addWidget(self._log_view)

    def apply_state(self, state: DiagnosticsUiState) -> None:
        """Обновляет статическую диагностику и логи."""

        self._status.setText(state.status_message)
        self._error.setText(state.error_message)
        self._config.setText(
            (
                f"Backend: {state.api_base_url}\n"
                f"WebSocket: {state.websocket_url}\n"
                f"Device ID: {state.device_id}\n"
                f"Data dir: {state.data_dir}"
            )
        )
        self._log_path.setText(f"Лог: {state.log_file}")
        self._log_view.setPlainText(state.log_text)

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет runtime-состояние приложения."""

        self._runtime.setText(
            (
                f"Связь: {snapshot.connection.status.value} | {snapshot.connection.message}\n"
                f"Сессия: {snapshot.session.status.value} | {snapshot.session.user_name or '-'}\n"
                f"Сканер: {snapshot.scanner.status.value} | "
                f"{snapshot.scanner.port or '-'} | {snapshot.scanner.message}"
            )
        )
