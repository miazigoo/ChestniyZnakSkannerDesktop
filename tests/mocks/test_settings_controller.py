"""Mock-тесты контроллера настроек."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from chestniy_znak_desktop.app.config import AppConfig  # noqa: E402
from chestniy_znak_desktop.app.settings_store import (  # noqa: E402
    SettingsStore,
    UserSettings,
)
from chestniy_znak_desktop.controllers.settings_controller import (  # noqa: E402
    SettingsController,
    SettingsFormData,
    SettingsUiState,
)
from chestniy_znak_desktop.services.sound_service import SoundService  # noqa: E402
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager  # noqa: E402


def qapp() -> QApplication:
    """Возвращает существующий QApplication или создает новый."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return cast(QApplication, app)


def _controller(  # type: ignore[no-untyped-def]
    tmp_path,
) -> tuple[SettingsController, SettingsStore]:
    """Создает контроллер настроек с INI-хранилищем."""

    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    settings = UserSettings(
        api_base_url="http://backend/api/v2/",
        device_id="pc-1",
        theme_name="light",
        scanner_port="COM3",
        scanner_baudrate=9600,
        sound_enabled=True,
        sound_volume=0.85,
        sound_ok_file="ok_02.mp3",
        sound_warning_file="other.mp3",
        sound_error_file="error.mp3",
        sound_victory_file="victory.mp3",
    )
    controller = SettingsController(
        settings_store=store,
        initial_settings=settings,
        theme_manager=ThemeManager("light"),
        sound_service=SoundService(),
        qt_app=qapp(),
    )
    return controller, store


def test_settings_controller_saves_form(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет сохранение основной формы настроек."""

    controller, store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    controller.state_changed.connect(states.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="https://new-backend/api/v2/",
            device_id="desktop-2",
            theme_name="dark",
            sound_enabled=False,
            sound_volume=0.4,
            sound_ok_file="ok_03.mp3",
            sound_warning_file="other_order.mp3",
            sound_error_file="error_02.mp3",
            sound_victory_file="victory.mp3",
        )
    )

    loaded = store.load(AppConfig())
    assert loaded.api_base_url == "https://new-backend/api/v2/"
    assert loaded.device_id == "desktop-2"
    assert loaded.theme_name == "dark"
    assert loaded.sound_enabled is False
    assert loaded.sound_volume == 0.4
    assert loaded.sound_ok_file == "ok_03.mp3"
    assert loaded.sound_warning_file == "other_order.mp3"
    assert loaded.sound_error_file == "error_02.mp3"
    assert states[-1].status_message.startswith("Настройки сохранены")


def test_settings_rejects_empty_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет валидацию пустого backend URL."""

    controller, store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    controller.state_changed.connect(states.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="",
            device_id="desktop-2",
            theme_name="dark",
            sound_enabled=False,
            sound_volume=0.4,
            sound_ok_file="ok_03.mp3",
            sound_warning_file="other_order.mp3",
            sound_error_file="error_02.mp3",
            sound_victory_file="victory.mp3",
        )
    )

    assert controller.settings.api_base_url == "http://backend/api/v2/"
    assert store.load(AppConfig()).theme_name == "light"
    assert states[-1].error_message == "Backend URL не может быть пустым"


def test_settings_controller_saves_scanner_values(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет сохранение порта и скорости сканера."""

    controller, store = _controller(tmp_path)

    controller.set_scanner_port("COM9")
    controller.set_scanner_baudrate(115200)

    loaded = store.load(AppConfig())
    assert loaded.scanner_port == "COM9"
    assert loaded.scanner_baudrate == 115200
