"""Экран авторизации оператора."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthUiState


class LoginScreen(QWidget):
    """Экран входа по токену авторизации."""

    token_submitted = Signal(str)

    def __init__(self) -> None:
        """Создает поля ввода токена и кнопку входа."""

        super().__init__()
        self._title_label = QLabel("Вход по токену")
        self._status_label = QLabel("Ожидание токена авторизации")
        self._error_label = QLabel("")
        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText("Сканируйте или вставьте токен авторизации")
        self._token_input.returnPressed.connect(self._submit_token)
        self._submit_button = QPushButton("Войти")
        self._submit_button.clicked.connect(self._submit_token)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addWidget(self._token_input)
        layout.addWidget(self._submit_button)
        layout.addStretch(1)

    def apply_state(self, state: AuthUiState) -> None:
        """Обновляет экран из состояния контроллера авторизации."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._submit_button.setEnabled(not state.is_submitting)
        self._token_input.setEnabled(not state.is_submitting)

    def _submit_token(self) -> None:
        """Отправляет введенный токен подписчикам экрана."""

        self.token_submitted.emit(self._token_input.text().strip())
