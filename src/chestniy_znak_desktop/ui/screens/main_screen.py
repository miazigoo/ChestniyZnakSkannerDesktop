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
from chestniy_znak_desktop.ui.screens.diagnostics_screen import DiagnosticsScreen
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen
from chestniy_znak_desktop.ui.screens.verify_screen import VerifyScreen
from chestniy_znak_desktop.ui.widgets.user_session_panel import UserSessionPanel


class MainScreen(QWidget):
    """Содержит рабочую навигацию после авторизации."""

    logout_requested = Signal()
    screen_changed = Signal(str)

    def __init__(self) -> None:
        """Создает навигацию и регистрирует рабочие экраны."""

        super().__init__()
        self._stack = QStackedWidget()
        self._session_panel = UserSessionPanel()
        self._packing_screen = PackingScreen()
        self._boxes_screen = BoxesScreen()
        self._verify_screen = VerifyScreen()
        self._defect_screen = DefectScreen()
        self._settings_screen = SettingsScreen()
        self._diagnostics_screen = DiagnosticsScreen()
        self._stack.addWidget(self._packing_screen)
        self._stack.addWidget(self._boxes_screen)
        self._stack.addWidget(self._verify_screen)
        self._stack.addWidget(self._defect_screen)
        self._stack.addWidget(self._settings_screen)
        self._stack.addWidget(self._diagnostics_screen)
        self._session_panel.logout_requested.connect(self.logout_requested.emit)

        nav = QVBoxLayout()
        nav.addWidget(self._session_panel)
        nav.addWidget(self._nav_button("Упаковка", 0, "packing"))
        nav.addWidget(self._nav_button("Коробки", 1, "boxes"))
        nav.addWidget(self._nav_button("Проверка", 2, "verify"))
        nav.addWidget(self._nav_button("Брак", 3, "defect"))
        nav.addStretch(1)
        nav.addWidget(self._nav_button("Настройки", 4, "settings"))
        nav.addWidget(self._nav_button("Диагностика", 5, "diagnostics"))

        layout = QHBoxLayout(self)
        layout.addLayout(nav)
        layout.addWidget(self._stack, stretch=1)

    @property
    def packing_screen(self) -> PackingScreen:
        """Возвращает экран упаковки для подключения контроллера."""

        return self._packing_screen

    @property
    def boxes_screen(self) -> BoxesScreen:
        """Возвращает экран коробок для подключения контроллера."""

        return self._boxes_screen

    @property
    def defect_screen(self) -> DefectScreen:
        """Возвращает экран брака для подключения контроллера."""

        return self._defect_screen

    @property
    def verify_screen(self) -> VerifyScreen:
        """Возвращает экран проверки для подключения контроллера."""

        return self._verify_screen

    @property
    def settings_screen(self) -> SettingsScreen:
        """Возвращает экран настроек для подключения контроллеров."""

        return self._settings_screen

    @property
    def diagnostics_screen(self) -> DiagnosticsScreen:
        """Возвращает экран диагностики для подключения контроллера."""

        return self._diagnostics_screen

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет рабочий экран из общего runtime snapshot."""

        self._session_panel.apply_snapshot(snapshot)
        self._packing_screen.apply_runtime_snapshot(snapshot)
        self._verify_screen.apply_runtime_snapshot(snapshot)
        self._defect_screen.apply_runtime_snapshot(snapshot)
        self._diagnostics_screen.apply_runtime_snapshot(snapshot)

    def _nav_button(self, title: str, index: int, screen_name: str) -> QPushButton:
        """Создает кнопку перехода на экран с указанным индексом."""

        button = QPushButton(title)
        button.clicked.connect(lambda: self._show_screen(index, screen_name))
        return button

    def _show_screen(self, index: int, screen_name: str) -> None:
        """Переключает рабочий экран и публикует выбранный сценарий."""

        self._stack.setCurrentIndex(index)
        self.screen_changed.emit(screen_name)
