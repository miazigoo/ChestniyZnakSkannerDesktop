"""Главный рабочий экран desktop-клиента."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen
from chestniy_znak_desktop.ui.screens.defect_screen import DefectScreen
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen
from chestniy_znak_desktop.ui.widgets.user_session_panel import UserSessionPanel


class MainScreen(QWidget):
    """Содержит рабочую навигацию после авторизации."""

    logout_requested = Signal()

    def __init__(self) -> None:
        """Создает навигацию и регистрирует рабочие экраны."""

        super().__init__()
        self._stack = QStackedWidget()
        self._session_panel = UserSessionPanel()
        self._packing_screen = PackingScreen()
        self._boxes_screen = BoxesScreen()
        self._defect_screen = DefectScreen()
        self._settings_screen = SettingsScreen()
        self._stack.addWidget(self._packing_screen)
        self._stack.addWidget(self._boxes_screen)
        self._stack.addWidget(self._defect_screen)
        self._stack.addWidget(self._settings_screen)
        self._session_panel.logout_requested.connect(self.logout_requested.emit)

        nav = QVBoxLayout()
        nav.addWidget(self._session_panel)
        nav.addWidget(self._nav_button("Упаковка", 0))
        nav.addWidget(self._nav_button("Коробки", 1))
        nav.addWidget(self._nav_button("Брак", 2))
        nav.addStretch(1)
        nav.addWidget(self._nav_button("Настройки", 3))

        layout = QHBoxLayout(self)
        layout.addLayout(nav)
        layout.addWidget(self._stack, stretch=1)

    @property
    def packing_screen(self) -> PackingScreen:
        """Возвращает экран упаковки для подключения контроллера."""

        return self._packing_screen

    @property
    def settings_screen(self) -> SettingsScreen:
        """Возвращает экран настроек для подключения контроллеров."""

        return self._settings_screen

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет рабочий экран из общего runtime snapshot."""

        self._session_panel.apply_snapshot(snapshot)

    def _nav_button(self, title: str, index: int) -> QPushButton:
        """Создает кнопку перехода на экран с указанным индексом."""

        button = QPushButton(title)
        button.clicked.connect(lambda: self._stack.setCurrentIndex(index))
        return button
