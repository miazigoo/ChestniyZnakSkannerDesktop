"""Экран авторизации оператора."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class LoginScreen(QWidget):
    """Экран входа по токену авторизации."""

    def __init__(self) -> None:
        """Создает экран ожидания скана авторизационного токена."""

        super().__init__()
        self._title_label = QLabel("Вход по токену")
        self._status_label = QLabel("Ожидание токена авторизации")
        self._error_label = QLabel("")
        self._token_preview = QLabel("Последний скан: -")
        self._scan_hint = QLabel("Сканируйте QR-токен авторизации подключенным сканером")
        self._scanner_label = QLabel("Сканер: проверяем состояние")
        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addWidget(self._token_preview)
        layout.addWidget(self._scan_hint)
        layout.addWidget(self._scanner_label)
        layout.addStretch(1)

    def apply_state(self, state: AuthUiState) -> None:
        """Обновляет экран из состояния контроллера авторизации."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._token_preview.setText(f"Последний скан: {state.token_preview or '-'}")

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для входа."""

        if snapshot.scanner.is_running:
            self._scanner_label.setText(f"Сканер готов: {snapshot.scanner.port}")
            return
        self._scanner_label.setText("Сканер не запущен. Вход невозможен без сканера.")
