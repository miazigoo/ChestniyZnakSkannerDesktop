"""Виджет статуса runtime-состояния."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from chestniy_znak_desktop import __version__
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class RuntimeStatusBar(QWidget):
    """Показывает состояние связи, сессии и сканера."""

    def __init__(self) -> None:
        """Создает компактную статусную панель."""

        super().__init__()
        self._snapshot: RuntimeSnapshot | None = None
        self._connection_label = QLabel(tr("runtime.connectionStopped"))
        self._session_label = QLabel(tr("runtime.sessionUnknown"))
        self._scanner_label = QLabel(tr("runtime.scannerStopped"))
        self._version_label = QLabel(tr("runtime.version", version=__version__))
        for label in (
            self._connection_label,
            self._session_label,
            self._scanner_label,
            self._version_label,
        ):
            label.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.addWidget(self._connection_label)
        layout.addStretch(1)
        layout.addWidget(self._session_label)
        layout.addStretch(1)
        layout.addWidget(self._scanner_label)
        layout.addStretch(1)
        layout.addWidget(self._version_label)

    def update_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет тексты панели из runtime snapshot."""

        self._snapshot = snapshot
        self._connection_label.setText(
            tr("runtime.connection", message=snapshot.connection.message)
        )
        user = snapshot.session.user_name or snapshot.session.status.value
        if snapshot.session.plant_name:
            user = f"{user} / {snapshot.session.plant_name}"
        elif snapshot.session.plant_id:
            user = f"{user} / {tr('session.plant', plant_id=snapshot.session.plant_id[:8])}"
        self._session_label.setText(tr("runtime.session", user=user))
        scanner = snapshot.scanner.port or snapshot.scanner.status.value
        self._scanner_label.setText(tr("runtime.scanner", scanner=scanner))

    def retranslate(self) -> None:
        """Переотрисовывает статусы после смены языка."""

        self._version_label.setText(tr("runtime.version", version=__version__))
        if self._snapshot is None:
            self._connection_label.setText(tr("runtime.connectionStopped"))
            self._session_label.setText(tr("runtime.sessionUnknown"))
            self._scanner_label.setText(tr("runtime.scannerStopped"))
            return
        self.update_snapshot(self._snapshot)
