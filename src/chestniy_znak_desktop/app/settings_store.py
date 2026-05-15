"""Постоянные пользовательские настройки приложения."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

from chestniy_znak_desktop.app.config import AppConfig


@dataclass(frozen=True, slots=True)
class UserSettings:
    """Настройки, которые оператор меняет из интерфейса."""

    api_base_url: str
    device_id: str
    theme_name: str = "light"
    scanner_port: str = ""
    scanner_baudrate: int = 9600
    sound_enabled: bool = True
    sound_volume: float = 0.85
    sound_ok_file: str = "ok_02.mp3"
    sound_warning_file: str = "other.mp3"
    sound_error_file: str = "error.mp3"
    sound_victory_file: str = "victory.mp3"
    auto_pack_codes_per_item: int = 1


class SettingsStore:
    """Хранит настройки в `QSettings` и отдает типизированную модель."""

    def __init__(self, settings: QSettings) -> None:
        """Создает хранилище вокруг конкретного экземпляра `QSettings`."""

        self._settings = settings

    @classmethod
    def from_config(cls, config: AppConfig) -> "SettingsStore":
        """Создает хранилище из данных приложения и организации."""

        return cls(QSettings(config.organization_name, config.app_name))

    @classmethod
    def from_file(cls, path: str) -> "SettingsStore":
        """Создает хранилище в INI-файле для тестов и portable-режима."""

        return cls(QSettings(path, QSettings.Format.IniFormat))

    def load(self, defaults: AppConfig) -> UserSettings:
        """Загружает настройки, подставляя значения конфигурации по умолчанию."""

        return UserSettings(
            api_base_url=self._value("network/api_base_url", defaults.api_base_url),
            device_id=self._value("device/device_id", defaults.device_id),
            theme_name=self._value("ui/theme_name", "light"),
            scanner_port=self._value("scanner/port", ""),
            scanner_baudrate=self._int_value("scanner/baudrate", 9600),
            sound_enabled=self._bool_value("sound/enabled", True),
            sound_volume=self._float_value("sound/volume", 0.85),
            sound_ok_file=self._value("sound/ok_file", "ok_02.mp3"),
            sound_warning_file=self._value("sound/warning_file", "other.mp3"),
            sound_error_file=self._value("sound/error_file", "error.mp3"),
            sound_victory_file=self._value("sound/victory_file", "victory.mp3"),
            auto_pack_codes_per_item=self._int_value("auto_packing/codes_per_item", 1),
        )

    def save(self, settings: UserSettings) -> None:
        """Сохраняет пользовательские настройки в постоянное хранилище."""

        self._settings.setValue("network/api_base_url", settings.api_base_url)
        self._settings.setValue("device/device_id", settings.device_id)
        self._settings.setValue("ui/theme_name", settings.theme_name)
        self._settings.setValue("scanner/port", settings.scanner_port)
        self._settings.setValue("scanner/baudrate", settings.scanner_baudrate)
        self._settings.setValue("sound/enabled", settings.sound_enabled)
        self._settings.setValue("sound/volume", settings.sound_volume)
        self._settings.setValue("sound/ok_file", settings.sound_ok_file)
        self._settings.setValue("sound/warning_file", settings.sound_warning_file)
        self._settings.setValue("sound/error_file", settings.sound_error_file)
        self._settings.setValue("sound/victory_file", settings.sound_victory_file)
        self._settings.setValue(
            "auto_packing/codes_per_item",
            max(1, settings.auto_pack_codes_per_item),
        )
        self._settings.sync()

    def _value(self, key: str, default: str) -> str:
        """Возвращает строковое значение настройки."""

        value = self._settings.value(key, default)
        return str(value)

    def _int_value(self, key: str, default: int) -> int:
        """Возвращает целочисленное значение настройки."""

        value = self._settings.value(key, default)
        return int(str(value))

    def _float_value(self, key: str, default: float) -> float:
        """Возвращает дробное значение настройки."""

        value = self._settings.value(key, default)
        return float(str(value))

    def _bool_value(self, key: str, default: bool) -> bool:
        """Возвращает булево значение настройки."""

        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}
