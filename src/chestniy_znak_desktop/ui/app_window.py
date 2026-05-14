"""Главное окно desktop-приложения."""

from __future__ import annotations

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.controllers.packing_controller import PackingController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.ui.screens.login_screen import LoginScreen
from chestniy_znak_desktop.ui.screens.main_screen import MainScreen
from chestniy_znak_desktop.ui.widgets.blocking_overlay import BlockingOverlay
from chestniy_znak_desktop.ui.widgets.runtime_status_bar import RuntimeStatusBar


class AppWindow(QMainWindow):
    """Главное окно с навигацией между экранами приложения."""

    def __init__(
        self,
        app_state: AppState,
        runtime_controller: RuntimeController,
        auth_controller: AuthController,
        packing_controller: PackingController,
    ) -> None:
        """Создает главное окно и регистрирует стартовые экраны."""

        super().__init__()
        self._app_state = app_state
        self._runtime_controller = runtime_controller
        self._auth_controller = auth_controller
        self._packing_controller = packing_controller
        self._central = QWidget()
        self._stack = QStackedWidget()
        self._status_bar = RuntimeStatusBar()
        self._login_screen = LoginScreen()
        self._main_screen = MainScreen()
        self._stack.addWidget(self._login_screen)
        self._stack.addWidget(self._main_screen)
        layout = QVBoxLayout(self._central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._status_bar)
        layout.addWidget(self._stack, stretch=1)
        self.setCentralWidget(self._central)
        self._blocking_overlay = BlockingOverlay(self._central)
        self._blocking_overlay.retry_requested.connect(self._runtime_controller.retry_connection)
        self._runtime_controller.snapshot_changed.connect(self._status_bar.update_snapshot)
        self._runtime_controller.blocking_changed.connect(self._set_work_area_blocking)
        self._auth_controller.state_changed.connect(self._login_screen.apply_state)
        self._auth_controller.authenticated.connect(lambda _user: self.show_main_screen())
        self._auth_controller.unauthenticated.connect(self.show_login_screen)
        self._login_screen.token_submitted.connect(self._auth_controller.login_with_raw_token)
        self._packing_controller.state_changed.connect(self._main_screen.packing_screen.apply_state)
        self._main_screen.packing_screen.refresh_requested.connect(
            self._packing_controller.refresh_current_box
        )
        self._main_screen.packing_screen.open_box_requested.connect(
            self._packing_controller.open_box
        )
        self._main_screen.packing_screen.close_box_requested.connect(
            self._packing_controller.close_current_box
        )
        self._main_screen.packing_screen.count_in_packing_changed.connect(
            self._packing_controller.set_count_in_packing
        )
        self._main_screen.packing_screen.manual_code_submitted.connect(
            self._packing_controller.on_code_scanned
        )
        self.setWindowTitle(app_state.config.app_name)
        self.resize(1180, 760)

    def show_login_screen(self) -> None:
        """Переключает окно на экран авторизации."""

        self._stack.setCurrentWidget(self._login_screen)
        self._blocking_overlay.set_blocking(False, "")

    def show_main_screen(self) -> None:
        """Переключает окно на главный рабочий экран."""

        self._stack.setCurrentWidget(self._main_screen)

    def _set_work_area_blocking(self, is_blocking: bool, message: str) -> None:
        """Блокирует только рабочие экраны, оставляя логин доступным."""

        if self._stack.currentWidget() is self._login_screen:
            self._blocking_overlay.set_blocking(False, "")
            return
        self._blocking_overlay.set_blocking(is_blocking, message)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Подгоняет blocking overlay под размер центрального виджета."""

        super().resizeEvent(event)
        self._blocking_overlay.setGeometry(self._central.rect())
