"""Bootstrap desktop-приложения."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.services.auth_service import AuthService
from chestniy_znak_desktop.api.services.packing_service import PackingService
from chestniy_znak_desktop.api.session_store import FileCookieStore
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.controllers.packing_controller import PackingController
from chestniy_znak_desktop.controllers.scanner_controller import ScannerController
from chestniy_znak_desktop.controllers.settings_controller import SettingsController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.connection_monitor import ConnectionMonitor
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.task_runner import QtTaskRunner, UnauthorizedAwareTaskRunner
from chestniy_znak_desktop.services.sound_service import SoundService
from chestniy_znak_desktop.ui.app_window import AppWindow
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager


def create_app_window(qt_app: QApplication, config: AppConfig) -> AppWindow:
    """Создает главное окно и подключает базовое состояние приложения."""

    qt_app.setApplicationName(config.app_name)
    qt_app.setOrganizationName(config.organization_name)
    settings_store = SettingsStore.from_config(config)
    settings = settings_store.load(defaults=config)
    config = replace(
        config,
        api_base_url=settings.api_base_url,
        device_id=settings.device_id,
    )
    theme_manager = ThemeManager(settings.theme_name)
    theme_manager.apply(qt_app)
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
    task_runner = QtTaskRunner()
    sound_service = SoundService(
        enabled=settings.sound_enabled,
        volume=settings.sound_volume,
    )
    auth_controller = AuthController(
        auth_service=AuthService(api_client),
        runtime_controller=runtime_controller,
        task_runner=task_runner,
    )
    api_task_runner = UnauthorizedAwareTaskRunner(
        base_runner=task_runner,
        on_unauthorized=lambda exc: _handle_unauthorized_api_error(
            api_client,
            auth_controller,
            exc,
        ),
    )
    packing_controller = PackingController(
        packing_service=PackingService(api_client),
        task_runner=api_task_runner,
        device_id=settings.device_id,
        sound_service=sound_service,
    )
    scanner_controller = ScannerController(
        runtime_controller=runtime_controller,
        initial_port=settings.scanner_port,
        initial_baudrate=settings.scanner_baudrate,
    )
    settings_controller = SettingsController(
        settings_store=settings_store,
        initial_settings=settings,
        theme_manager=theme_manager,
        sound_service=sound_service,
        qt_app=qt_app,
    )
    window = AppWindow(
        app_state=state,
        runtime_controller=runtime_controller,
        auth_controller=auth_controller,
        packing_controller=packing_controller,
        scanner_controller=scanner_controller,
        settings_controller=settings_controller,
    )
    window.destroyed.connect(lambda _obj: runtime_controller.stop())
    window.destroyed.connect(lambda _obj: api_client.close())
    window.destroyed.connect(lambda _obj: scanner_controller.stop())
    auth_controller.authenticated.connect(lambda _user: packing_controller.refresh_current_box())
    runtime_controller.start()
    scanner_controller.refresh_ports()
    settings_controller.publish_state()
    auth_controller.restore_session()
    return window


def _handle_unauthorized_api_error(
    api_client: ApiClient,
    auth_controller: AuthController,
    exc: Exception,
) -> None:
    """Очищает cookies и переводит приложение на экран авторизации."""

    api_client.clear_cookies()
    auth_controller.handle_session_expired(str(exc))
