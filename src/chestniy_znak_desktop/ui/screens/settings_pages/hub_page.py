"""Главная страница раздела настроек."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.ui.screens.settings_pages.common import create_page_header
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


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
        self.setObjectName("settingsPage")
        header = create_page_header(
            title="Настройки",
            subtitle="Группы параметров приложения, оборудования, интерфейса и звуков.",
            icon_name=VectorIconName.SETTINGS,
            icon_color="#66d2c7",
        )
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self._button("Основные", self.app_requested.emit), 0, 0)
        grid.addWidget(self._button("Сканер", self.scanner_requested.emit), 0, 1)
        grid.addWidget(self._button("Принтер", self.printer_requested.emit), 1, 0)
        grid.addWidget(self._button("Тема", self.theme_requested.emit), 1, 1)
        grid.addWidget(self._button("Звук", self.sound_requested.emit), 2, 0, 1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addLayout(grid)
        layout.addStretch(1)

    @staticmethod
    def _button(title: str, callback: Callable[[], None]) -> QPushButton:
        """Создает кнопку перехода в группу настроек."""

        button = QPushButton(title)
        button.setObjectName("settingsHubButton")
        button.clicked.connect(callback)
        return button
