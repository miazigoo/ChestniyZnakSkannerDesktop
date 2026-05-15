"""Тесты постоянных настроек приложения."""

from __future__ import annotations

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore, UserSettings


def test_settings_store_loads_defaults(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет загрузку настроек по умолчанию из конфигурации."""

    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    settings = store.load(AppConfig(api_base_url="http://test/api/v2/", device_id="pc-1"))
    assert settings.api_base_url == "http://test/api/v2/"
    assert settings.device_id == "pc-1"
    assert settings.theme_name == "light"
    assert settings.auto_pack_codes_per_item == 1


def test_settings_store_saves_and_loads_values(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет сохранение и повторную загрузку пользовательских настроек."""

    settings_path = tmp_path / "settings.ini"
    store = SettingsStore.from_file(str(settings_path))
    store.save(
        UserSettings(
            api_base_url="https://backend/api/v2/",
            device_id="desktop-1",
            theme_name="dark",
            scanner_port="COM7",
            scanner_baudrate=115200,
            sound_enabled=False,
            sound_volume=0.4,
            sound_ok_file="ok_03.mp3",
            sound_warning_file="other_order.mp3",
            sound_error_file="error_02.mp3",
            sound_victory_file="victory.mp3",
            auto_pack_codes_per_item=12,
        )
    )
    loaded = SettingsStore.from_file(str(settings_path)).load(AppConfig())
    assert loaded.theme_name == "dark"
    assert loaded.scanner_port == "COM7"
    assert loaded.scanner_baudrate == 115200
    assert loaded.sound_enabled is False
    assert loaded.sound_volume == 0.4
    assert loaded.sound_ok_file == "ok_03.mp3"
    assert loaded.sound_warning_file == "other_order.mp3"
    assert loaded.sound_error_file == "error_02.mp3"
    assert loaded.auto_pack_codes_per_item == 12
