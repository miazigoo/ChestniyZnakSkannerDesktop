"""Bootstrap desktop-приложения."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.services.auth_service import AuthService
from chestniy_znak_desktop.api.session_store import FileCookieStore
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.connection_monitor import ConnectionMonitor
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.task_runner import QtTaskRunner
from chestniy_znak_desktop.ui.app_window import AppWindow
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager


def create_app_window(qt_app: QApplication, config: AppConfig) -> AppWindow:
    """Создает главное окно и подключает базовое состояние приложения."""

    qt_app.setApplicationName(config.app_name)
    qt_app.setOrganizationName(config.organization_name)
    settings = SettingsStore.from_config(config).load(defaults=config)
    ThemeManager(settings.theme_name).apply(qt_app)
    state = AppState(config=config)
    connection_monitor = ConnectionMonitor(websocket_url=config.websocket_url)
    runtime_controller = RuntimeController(
        app_state=state,
        connection_monitor=connection_monitor,
    )
    api_client = ApiClient(
        config=config,
        cookie_store=FileCookieStore(config.data_dir / "cookies.txt"),
    )
    auth_controller = AuthController(
        auth_service=AuthService(api_client),
        runtime_controller=runtime_controller,
        task_runner=QtTaskRunner(),
    )
    window = AppWindow(
        app_state=state,
        runtime_controller=runtime_controller,
        auth_controller=auth_controller,
    )
    window.destroyed.connect(lambda _obj: runtime_controller.stop())
    window.destroyed.connect(lambda _obj: api_client.close())
    runtime_controller.start()
    auth_controller.restore_session()
    return window
