"""Mock-тесты контроллера настроек."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import cast

import pytest

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


def _controller(
    tmp_path: Path,
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


def test_settings_controller_saves_form(tmp_path: Path) -> None:
    """Проверяет сохранение основной формы настроек."""

    controller, store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    saved_messages: list[str] = []
    controller.state_changed.connect(states.append)
    controller.settings_saved.connect(saved_messages.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="https://new-backend/api/v2/",
            device_id="desktop-2",
            language="ru",
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
    assert saved_messages == [
        "Настройки сохранены. Backend и Device ID применятся после перезапуска."
    ]


def test_settings_controller_reports_sound_save_message(
    tmp_path: Path,
) -> None:
    """Проверяет понятную модалку при сохранении звука."""

    controller, _store = _controller(tmp_path)
    saved_messages: list[str] = []
    controller.settings_saved.connect(saved_messages.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            language="ru",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.6,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
        )
    )

    assert saved_messages == ["Звуковые настройки сохранены и применены."]


def test_settings_controller_reports_generic_save_message(
    tmp_path: Path,
) -> None:
    """Проверяет нейтральную модалку при сохранении без изменений."""

    controller, _store = _controller(tmp_path)
    saved_messages: list[str] = []
    controller.settings_saved.connect(saved_messages.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            language="ru",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.85,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
        )
    )

    assert saved_messages == ["Настройки сохранены."]


def test_settings_controller_saves_language(tmp_path: Path) -> None:
    """Проверяет сохранение языка API-ответов."""

    controller, store = _controller(tmp_path)
    changed_languages: list[str] = []
    saved_messages: list[str] = []
    controller.language_changed.connect(changed_languages.append)
    controller.settings_saved.connect(saved_messages.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            language="zh-CN",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.85,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
        )
    )

    assert store.load(AppConfig()).language == "zh"
    assert changed_languages == ["zh"]
    assert saved_messages == ["语言已保存，并会用于新的请求。"]


def test_settings_rejects_empty_backend(tmp_path: Path) -> None:
    """Проверяет валидацию пустого backend URL."""

    controller, store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    controller.state_changed.connect(states.append)

    controller.save_form(
        SettingsFormData(
            api_base_url="",
            device_id="desktop-2",
            language="ru",
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


def test_settings_controller_saves_scanner_values(tmp_path: Path) -> None:
    """Проверяет сохранение порта и скорости сканера."""

    controller, store = _controller(tmp_path)

    controller.set_scanner_port("COM9")
    controller.set_scanner_baudrate(115200)

    loaded = store.load(AppConfig())
    assert loaded.scanner_port == "COM9"
    assert loaded.scanner_baudrate == 115200


def test_settings_controller_applies_theme_immediately(
    tmp_path: Path,
) -> None:
    """Проверяет быстрое сохранение темы без полной формы настроек."""

    controller, store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    controller.state_changed.connect(states.append)

    controller.set_theme("graphite")

    loaded = store.load(AppConfig())
    assert loaded.theme_name == "graphite"
    assert controller.settings.theme_name == "graphite"
    assert states[-1].status_message == "Тема применена: Graphite Pro"


def test_settings_controller_previews_sound_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет прослушивание выбранного звука."""

    controller, _store = _controller(tmp_path)
    played: list[str] = []
    states: list[SettingsUiState] = []
    saved_messages: list[str] = []
    controller.state_changed.connect(states.append)
    controller.settings_saved.connect(saved_messages.append)
    monkeypatch.setattr(controller._sound_service, "preview_file", played.append)  # noqa: SLF001

    controller.preview_sound_file("ok_02.mp3")

    assert played == ["ok_02.mp3"]
    assert states[-1].status_message == "Прослушивание: ok_02.mp3"
    assert saved_messages == []


def test_settings_controller_rejects_missing_sound_file(
    tmp_path: Path,
) -> None:
    """Проверяет ошибку прослушивания неизвестного файла."""

    controller, _store = _controller(tmp_path)
    states: list[SettingsUiState] = []
    controller.state_changed.connect(states.append)

    controller.preview_sound_file("missing.mp3")

    assert states[-1].error_message == "Файл звука не найден"
