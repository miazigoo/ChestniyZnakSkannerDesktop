"""Главная страница раздела настроек."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class SettingsHubPage(QWidget):
    """Показывает группы настроек отдельными пунктами меню."""

    app_requested = Signal()
    scanner_requested = Signal()
    printer_requested = Signal()
    theme_requested = Signal()
    sound_requested = Signal()

    def __init__(self) -> None:
        """Создает список групп настроек."""

        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Настройки"))
        layout.addWidget(self._button("Основные", self.app_requested.emit))
        layout.addWidget(self._button("Сканер", self.scanner_requested.emit))
        layout.addWidget(self._button("Принтер", self.printer_requested.emit))
        layout.addWidget(self._button("Тема", self.theme_requested.emit))
        layout.addWidget(self._button("Звук", self.sound_requested.emit))
        layout.addStretch(1)

    @staticmethod
    def _button(title: str, callback: Callable[[], None]) -> QPushButton:
        """Создает кнопку перехода в группу настроек."""

        button = QPushButton(title)
        button.clicked.connect(callback)
        return button
