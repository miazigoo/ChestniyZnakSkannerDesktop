"""Виджет статуса runtime-состояния."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class RuntimeStatusBar(QWidget):
    """Показывает состояние связи, сессии и сканера."""

    def __init__(self) -> None:
        """Создает компактную статусную панель."""

        super().__init__()
        self._connection_label = QLabel("Связь: остановлена")
        self._session_label = QLabel("Сессия: неизвестно")
        self._scanner_label = QLabel("Сканер: остановлен")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.addWidget(self._connection_label)
        layout.addStretch(1)
        layout.addWidget(self._session_label)
        layout.addStretch(1)
        layout.addWidget(self._scanner_label)

    def update_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет тексты панели из runtime snapshot."""

        self._connection_label.setText(f"Связь: {snapshot.connection.message}")
        user = snapshot.session.user_name or snapshot.session.status.value
        self._session_label.setText(f"Сессия: {user}")
        scanner = snapshot.scanner.port or snapshot.scanner.status.value
        self._scanner_label.setText(f"Сканер: {scanner}")
