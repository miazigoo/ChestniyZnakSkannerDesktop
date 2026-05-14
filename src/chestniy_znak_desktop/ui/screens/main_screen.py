"""Главный рабочий экран desktop-клиента."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen
from chestniy_znak_desktop.ui.screens.defect_screen import DefectScreen
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen


class MainScreen(QWidget):
    """Содержит рабочую навигацию после авторизации."""

    def __init__(self) -> None:
        """Создает навигацию и регистрирует рабочие экраны."""

        super().__init__()
        self._stack = QStackedWidget()
        self._packing_screen = PackingScreen()
        self._boxes_screen = BoxesScreen()
        self._defect_screen = DefectScreen()
        self._settings_screen = SettingsScreen()
        self._stack.addWidget(self._packing_screen)
        self._stack.addWidget(self._boxes_screen)
        self._stack.addWidget(self._defect_screen)
        self._stack.addWidget(self._settings_screen)

        nav = QVBoxLayout()
        nav.addWidget(self._nav_button("Упаковка", 0))
        nav.addWidget(self._nav_button("Коробки", 1))
        nav.addWidget(self._nav_button("Брак", 2))
        nav.addStretch(1)
        nav.addWidget(self._nav_button("Настройки", 3))

        layout = QHBoxLayout(self)
        layout.addLayout(nav)
        layout.addWidget(self._stack, stretch=1)

    def _nav_button(self, title: str, index: int) -> QPushButton:
        """Создает кнопку перехода на экран с указанным индексом."""

        button = QPushButton(title)
        button.clicked.connect(lambda: self._stack.setCurrentIndex(index))
        return button
