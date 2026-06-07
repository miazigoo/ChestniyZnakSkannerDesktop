"""Виджет текущей пользовательской сессии."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from chestniy_znak_desktop.i18n import tr
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
        self._snapshot: RuntimeSnapshot | None = None
        self.setObjectName("userSessionPanel")
        self.setFixedHeight(124)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._user_label = QLabel(tr("session.operatorNone"))
        self._user_label.setObjectName("sessionUser")
        self._connection_label = QLabel(tr("session.backendUnknown"))
        self._connection_label.setObjectName("sessionMeta")
        self._scanner_label = QLabel(tr("session.scannerStopped"))
        self._scanner_label.setObjectName("sessionMeta")
        self._logout_button = QPushButton(tr("session.logout"))
        self._logout_button.setObjectName("sessionLogout")
        self._logout_button.clicked.connect(self.logout_requested.emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        layout.addWidget(self._user_label)
        layout.addWidget(self._connection_label)
        layout.addWidget(self._scanner_label)
        layout.addWidget(self._logout_button)

    def apply_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет отображение сессии из общего runtime snapshot."""

        self._snapshot = snapshot
        self._user_label.setText(self._format_user(snapshot))
        self._connection_label.setText(self._format_connection(snapshot))
        self._scanner_label.setText(self._format_scanner(snapshot))
        self._logout_button.setEnabled(snapshot.session.is_authenticated)

    @staticmethod
    def _format_user(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку текущего оператора."""

        if snapshot.session.status == SessionStatus.AUTHENTICATED:
            user = snapshot.session.user_name
            if snapshot.session.plant_name:
                user = f"{user} / {snapshot.session.plant_name}"
            elif snapshot.session.plant_id:
                plant = tr("session.plant", plant_id=snapshot.session.plant_id[:8])
                user = f"{user} / {plant}"
            return tr("session.operator", user=user)
        return tr("session.operatorNone")

    @staticmethod
    def _format_connection(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку состояния backend-связи."""

        if snapshot.connection.status == ConnectionStatus.CONNECTED:
            return tr("session.backendConnected")
        return tr("session.backend", message=snapshot.connection.message)

    @staticmethod
    def _format_scanner(snapshot: RuntimeSnapshot) -> str:
        """Форматирует строку состояния сканера."""

        if snapshot.scanner.status == ScannerStatus.RUNNING:
            return tr("session.scannerPort", port=snapshot.scanner.port)
        if snapshot.scanner.status == ScannerStatus.ERROR:
            return tr("session.scannerError", message=snapshot.scanner.message)
        return tr("session.scannerStopped")

    def retranslate(self) -> None:
        """Переотрисовывает данные сессии после смены языка."""

        self._logout_button.setText(tr("session.logout"))
        if self._snapshot is None:
            self._user_label.setText(tr("session.operatorNone"))
            self._connection_label.setText(tr("session.backendUnknown"))
            self._scanner_label.setText(tr("session.scannerStopped"))
            return
        self.apply_snapshot(self._snapshot)
