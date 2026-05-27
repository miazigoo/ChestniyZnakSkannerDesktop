"""Блокирующий overlay для рабочих экранов."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.i18n import tr


class BlockingOverlay(QWidget):
    """Перекрывает UI, когда работа невозможна без связи или авторизации."""

    retry_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает overlay с текстом причины и кнопкой повторного подключения."""

        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("blockingOverlay")
        self._message_label = QLabel(tr("common.blocked"))
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._retry_button = QPushButton(tr("common.retryConnection"))
        self._retry_button.clicked.connect(self.retry_requested.emit)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self._message_label)
        layout.addWidget(self._retry_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        self.hide()

    def set_blocking(self, is_blocking: bool, message: str) -> None:
        """Показывает или скрывает overlay с причиной блокировки."""

        self._message_label.setText(message or tr("common.actionsBlocked"))
        self.setVisible(is_blocking)
        if is_blocking:
            self.raise_()
