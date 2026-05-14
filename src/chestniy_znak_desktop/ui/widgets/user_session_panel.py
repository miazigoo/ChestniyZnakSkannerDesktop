"""Виджет текущей пользовательской сессии."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.runtime.state_models import (
    ConnectionStatus,
    RuntimeSnapshot,
    ScannerStatus,
    SessionStatus,
)


class UserSessionPanel(QWidget):
    """Показывает оператора, связь, сканер и кнопку выхода."""

    logout_requested = Signal()

    def __init__(self) -> None:
        """Создает компактный блок сессии для рабочего экрана."""

        super().__init__()
        self.setObjectName("userSessionPanel")
        self._user_label = QLabel("Оператор: нет сессии")
        self._user_label.setObjectName("sessionUser")
        self._connection_label = QLabel("Backend: неизвестно")
        self._connection_label.setObjectName("sessionMeta")
        self._scanner_label = QLabel("Сканер: остановлен")
        self._scanner_label.setObjectName("sessionMeta")
        self._logout_button = QPushButton("Выйти")
        self._logout_button.setObjectName("sessionLogout")
        self._logout_button.clicked.connect(self.logout_requested.emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.addWidget(self._user_label)
        layout.addWidget(self._connection_label)
        layout.addWidget(self._scanner_label)
        layout.addWidget(self._logout_button)

    def apply_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет отображение сессии из общего runtime snapshot."""

        self._user_label.setText(self._format_user(snapshot))
        self._connection_label.setText(self._format_connection(snapshot))
        self._scanner_label.setText(self._format_scanner(snapshot))
        self._logout_button.setEnabled(snapshot.session.is_authenticated)

    @staticmethod
    def _format_user(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку текущего оператора."""

        if snapshot.session.status == SessionStatus.AUTHENTICATED:
            return f"Оператор: {snapshot.session.user_name}"
        return "Оператор: нет сессии"

    @staticmethod
    def _format_connection(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку состояния backend-связи."""

        if snapshot.connection.status == ConnectionStatus.CONNECTED:
            return "Backend: подключен"
        return f"Backend: {snapshot.connection.message}"

    @staticmethod
    def _format_scanner(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку состояния сканера."""

        if snapshot.scanner.status == ScannerStatus.RUNNING:
            return f"Сканер: {snapshot.scanner.port}"
        if snapshot.scanner.status == ScannerStatus.ERROR:
            return f"Сканер: ошибка - {snapshot.scanner.message}"
        return "Сканер: остановлен"
