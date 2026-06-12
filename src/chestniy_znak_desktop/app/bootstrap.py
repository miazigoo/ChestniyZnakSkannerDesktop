"""Bootstrap desktop-приложения."""

from __future__ import annotations

import json
import sys
import os
from dataclasses import replace
from typing import TypeAlias

from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.services.box_edit_service import BoxEditService
from chestniy_znak_desktop.api.services.auth_service import AuthService
from chestniy_znak_desktop.api.services.order_service import OrderService
from chestniy_znak_desktop.api.services.packing_service import PackingService
from chestniy_znak_desktop.api.services.printer_service import PrinterService
from chestniy_znak_desktop.api.services.chestniy_znak_service import ChestniyZnakService
from chestniy_znak_desktop.api.session_store import FileBearerTokenStore, FileCookieStore
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.controllers.auto_packing_controller import AutoPackingController
from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditController
from chestniy_znak_desktop.controllers.box_lookup_controller import BoxLookupController
from chestniy_znak_desktop.controllers.boxes_controller import BoxesController
from chestniy_znak_desktop.controllers.defect_controller import DefectController
from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsController
from chestniy_znak_desktop.controllers.packing_controller import PackingController
from chestniy_znak_desktop.controllers.printer_controller import PrinterController
from chestniy_znak_desktop.controllers.scanner_controller import ScannerController
from chestniy_znak_desktop.controllers.settings_controller import SettingsController
from chestniy_znak_desktop.i18n import set_current_language
from chestniy_znak_desktop.controllers.verify_controller import VerifyController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.connection_monitor import ConnectionMonitor
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.task_runner import QtTaskRunner, UnauthorizedAwareTaskRunner
from chestniy_znak_desktop.scanner.evdev_keyboard_scanner import (
    EvdevKeyboardScanner,
    MultiEvdevKeyboardScanner,
    default_evdev_scanner_paths,
)
from chestniy_znak_desktop.scanner.hid_keyboard_scanner import HidKeyboardScanner
from chestniy_znak_desktop.scanner.hid_process_worker import HidProcessScanner
from chestniy_znak_desktop.scanner.windows_hid_scanner import WindowsHidScanner
from chestniy_znak_desktop.scanner.windows_raw_input_scanner import WindowsRawInputScanner
from chestniy_znak_desktop.services.auto_pack_ws_verifier import AutoPackWsVerifier
from chestniy_znak_desktop.services.order_local_pool_cache import OrderLocalPoolCache
from chestniy_znak_desktop.services.sound_service import SoundEvent, SoundService
from chestniy_znak_desktop.services.log_service import LogService
from chestniy_znak_desktop.ui.app_window import AppWindow
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager

HidScannerSource: TypeAlias = (
    EvdevKeyboardScanner
    | MultiEvdevKeyboardScanner
    | HidKeyboardScanner
    | HidProcessScanner
    | WindowsHidScanner
    | WindowsRawInputScanner
)


def create_app_window(qt_app: QApplication, config: AppConfig) -> AppWindow:
    """Создает главное окно и подключает базовое состояние приложения."""

    qt_app.setApplicationName(config.app_name)
    qt_app.setOrganizationName(config.organization_name)
    settings_store = SettingsStore.from_config(config)
    settings = settings_store.load(defaults=config)
    set_current_language(settings.language)
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
        bearer_store=FileBearerTokenStore(config.data_dir / "saas_session.json"),
        language=settings.language,
    )
    task_runner = QtTaskRunner()
    sound_service = SoundService(
        enabled=settings.sound_enabled,
        volume=settings.sound_volume,
        sound_files={
            SoundEvent.OK: settings.sound_ok_file,
            SoundEvent.WARNING: settings.sound_warning_file,
            SoundEvent.ERROR: settings.sound_error_file,
            SoundEvent.VICTORY: settings.sound_victory_file,
        },
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
    packing_service = PackingService(api_client)
    printer_service = PrinterService(api_client)
    local_pool_cache = OrderLocalPoolCache(config.data_dir / "local_pool.sqlite3")
    order_service = OrderService(api_client, local_pool_cache=local_pool_cache)
    chz_service = ChestniyZnakService(api_client)
    box_edit_service = BoxEditService(api_client)
    auto_pack_ws_verifier = AutoPackWsVerifier(connection_monitor=connection_monitor)
    packing_controller = PackingController(
        packing_service=packing_service,
        task_runner=api_task_runner,
        device_id=settings.device_id,
        order_service=order_service,
        sound_service=sound_service,
        label_printer=printer_service,
    )
    auto_packing_controller = AutoPackingController(
        packing_service=packing_service,
        verify_service=chz_service,
        box_edit_service=box_edit_service,
        task_runner=api_task_runner,
        settings_store=settings_store,
        settings_defaults=config,
        device_id=settings.device_id,
        order_service=order_service,
        ws_verify_service=auto_pack_ws_verifier,
        sound_service=sound_service,
        label_printer=printer_service,
    )
    boxes_controller = BoxesController(
        boxes_service=packing_service,
        task_runner=api_task_runner,
        sound_service=sound_service,
    )
    box_lookup_controller = BoxLookupController(
        boxes_service=packing_service,
        task_runner=api_task_runner,
        sound_service=sound_service,
    )
    box_edit_controller = BoxEditController(
        edit_service=box_edit_service,
        task_runner=api_task_runner,
        sound_service=sound_service,
    )
    defect_controller = DefectController(
        defect_service=chz_service,
        task_runner=api_task_runner,
        sound_service=sound_service,
    )
    verify_controller = VerifyController(
        verify_service=chz_service,
        task_runner=api_task_runner,
        sound_service=sound_service,
    )
    printer_controller = PrinterController(
        printer_service=printer_service,
        task_runner=api_task_runner,
        device_id=settings.device_id,
    )
    diagnostics_controller = DiagnosticsController(
        config=config,
        log_service=LogService(config.data_dir / "logs" / "desktop.log"),
    )
    hid_keyboard_scanner = _create_hid_scanner()
    scanner_controller = ScannerController(
        runtime_controller=runtime_controller,
        hid_keyboard_worker=hid_keyboard_scanner,
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
    settings_controller.language_changed.connect(api_client.set_language)
    settings_controller.language_changed.connect(set_current_language)
    window = AppWindow(
        app_state=state,
        runtime_controller=runtime_controller,
        auth_controller=auth_controller,
        packing_controller=packing_controller,
        auto_packing_controller=auto_packing_controller,
        boxes_controller=boxes_controller,
        box_lookup_controller=box_lookup_controller,
        box_edit_controller=box_edit_controller,
        defect_controller=defect_controller,
        verify_controller=verify_controller,
        printer_controller=printer_controller,
        diagnostics_controller=diagnostics_controller,
        scanner_controller=scanner_controller,
        settings_controller=settings_controller,
    )
    if isinstance(
        hid_keyboard_scanner,
        (HidKeyboardScanner, WindowsHidScanner, WindowsRawInputScanner),
    ):
        hid_keyboard_scanner.bind_root(window)
    window.destroyed.connect(lambda _obj: runtime_controller.stop())
    window.destroyed.connect(lambda _obj: api_client.close())
    window.destroyed.connect(lambda _obj: scanner_controller.stop())
    auth_controller.authenticated.connect(lambda _user: packing_controller.refresh_current_box())
    auth_controller.authenticated.connect(lambda _user: packing_controller.refresh_orders())
    auth_controller.authenticated.connect(
        lambda _user: auto_packing_controller.refresh_current_box()
    )
    auth_controller.authenticated.connect(lambda _user: auto_packing_controller.refresh_orders())
    connection_monitor.message_received.connect(
        lambda message: _handle_package_realtime_message(
            message,
            packing_controller=packing_controller,
            auto_packing_controller=auto_packing_controller,
        )
    )
    runtime_controller.start()
    scanner_controller.refresh_ports()
    scanner_controller.start_hid_keyboard()
    scanner_controller.start_if_configured()
    settings_controller.publish_state()
    diagnostics_controller.publish_state()
    diagnostics_controller.refresh_logs()
    auth_controller.restore_session()
    return window


def _handle_package_realtime_message(
    message: str,
    *,
    packing_controller: PackingController,
    auto_packing_controller: AutoPackingController,
) -> None:
    """Refresh Desktop packing screens on package realtime events."""

    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    message_type = str(payload.get("type") or "")
    if not message_type.startswith("package."):
        return
    packing_controller.refresh_current_box()
    auto_packing_controller.handle_realtime_message(message)


def _create_hid_scanner() -> HidScannerSource:
    """Возвращает самый надежный HID-источник для текущей платформы."""

    # Raw Linux evdev can crash native Qt/PySide on some workstations. Keep it opt-in.
    evdev_paths = (
        default_evdev_scanner_paths()
        if os.getenv("CHZ_ENABLE_EVDEV") == "1" and os.getenv("CHZ_DISABLE_EVDEV") != "1"
        else []
    )
    if evdev_paths:
        return MultiEvdevKeyboardScanner(device_paths=evdev_paths)
    if sys.platform == "win32":
        return WindowsRawInputScanner()
    return HidKeyboardScanner()


def _handle_unauthorized_api_error(
    api_client: ApiClient,
    auth_controller: AuthController,
    exc: Exception,
) -> None:
    """Очищает локальную сессию и переводит приложение на экран авторизации."""

    api_client.clear_cookies()
    api_client.clear_bearer_tokens()
    auth_controller.handle_session_expired(str(exc))
