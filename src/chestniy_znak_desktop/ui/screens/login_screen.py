"""Экран авторизации оператора."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthUiState


class LoginScreen(QWidget):
    """Экран входа по токену авторизации."""

    def __init__(self) -> None:
        """Создает экран ожидания скана авторизационного токена."""

        super().__init__()
        self._title_label = QLabel("Вход по токену")
        self._status_label = QLabel("Ожидание токена авторизации")
        self._error_label = QLabel("")
        self._scan_hint = QLabel("Сканируйте QR-токен авторизации подключенным сканером")
        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addWidget(self._scan_hint)
        layout.addStretch(1)

    def apply_state(self, state: AuthUiState) -> None:
        """Обновляет экран из состояния контроллера авторизации."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
