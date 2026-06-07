"""Главная страница раздела настроек."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.i18n import tr
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
            title=tr("settings.hub.title"),
            subtitle=tr("settings.hub.subtitle"),
            icon_name=VectorIconName.SETTINGS,
            icon_color="#66d2c7",
        )
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(
            self._button(
                tr("settings.hub.app"),
                tr("settings.hub.appHint"),
                self.app_requested.emit,
            ),
            0,
            0,
        )
        grid.addWidget(
            self._button(
                tr("settings.hub.scanner"),
                tr("settings.hub.scannerHint"),
                self.scanner_requested.emit,
            ),
            0,
            1,
        )
        grid.addWidget(
            self._button(
                tr("settings.hub.printer"),
                tr("settings.hub.printerHint"),
                self.printer_requested.emit,
            ),
            1,
            0,
        )
        grid.addWidget(
            self._button(
                tr("settings.hub.theme"),
                tr("settings.hub.themeHint"),
                self.theme_requested.emit,
            ),
            1,
            1,
        )
        grid.addWidget(
            self._button(
                tr("settings.hub.sound"),
                tr("settings.hub.soundHint"),
                self.sound_requested.emit,
            ),
            2,
            0,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addLayout(grid)
        layout.addStretch(1)

    @staticmethod
    def _button(title: str, hint: str, callback: Callable[[], None]) -> QPushButton:
        """Создает кнопку перехода в группу настроек."""

        button = QPushButton(f"{title}\n{hint}")
        button.setObjectName("settingsHubButton")
        button.setToolTip(hint)
        button.clicked.connect(callback)
        return button
