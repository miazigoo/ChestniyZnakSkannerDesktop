"""Контроллер пользовательских настроек."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.app.settings_store import SettingsStore, UserSettings
from chestniy_znak_desktop.services.sound_service import SoundEvent, SoundService
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager


@dataclass(frozen=True, slots=True)
class SettingsFormData:
    """Данные формы настроек, пришедшие из UI."""

    api_base_url: str
    device_id: str
    theme_name: str
    sound_enabled: bool
    sound_volume: float
    sound_ok_file: str
    sound_warning_file: str
    sound_error_file: str
    sound_victory_file: str


@dataclass(frozen=True, slots=True)
class SettingsUiState:
    """Состояние экрана настроек."""

    api_base_url: str
    device_id: str
    theme_name: str
    sound_enabled: bool
    sound_volume: float
    sound_ok_file: str
    sound_warning_file: str
    sound_error_file: str
    sound_victory_file: str
    available_sound_files: list[str]
    status_message: str = ""
    error_message: str = ""


class SettingsController(QObject):
    """Сохраняет настройки и применяет изменения, доступные без перезапуска."""

    state_changed = Signal(SettingsUiState)

    def __init__(
        self,
        settings_store: SettingsStore,
        initial_settings: UserSettings,
        theme_manager: ThemeManager,
        sound_service: SoundService,
        qt_app: QApplication,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер настроек."""

        super().__init__(parent)
        self._settings_store = settings_store
        self._settings = initial_settings
        self._theme_manager = theme_manager
        self._sound_service = sound_service
        self._qt_app = qt_app

    @property
    def settings(self) -> UserSettings:
        """Возвращает текущие сохраненные настройки."""

        return self._settings

    def publish_state(self) -> None:
        """Публикует состояние настроек для первичного заполнения UI."""

        self._emit_state(status_message="Настройки загружены")

    def save_form(self, form_data: SettingsFormData) -> None:
        """Валидирует и сохраняет значения основной формы настроек."""

        api_base_url = form_data.api_base_url.strip()
        device_id = form_data.device_id.strip()
        if not api_base_url:
            self._emit_state(error_message="Backend URL не может быть пустым")
            return
        if not device_id:
            self._emit_state(error_message="Device ID не может быть пустым")
            return
        self._settings = replace(
            self._settings,
            api_base_url=api_base_url,
            device_id=device_id,
            theme_name=form_data.theme_name,
            sound_enabled=form_data.sound_enabled,
            sound_volume=form_data.sound_volume,
            sound_ok_file=form_data.sound_ok_file,
            sound_warning_file=form_data.sound_warning_file,
            sound_error_file=form_data.sound_error_file,
            sound_victory_file=form_data.sound_victory_file,
        )
        self._apply_live_settings()
        self._save("Настройки сохранены. Backend и Device ID применятся после перезапуска.")

    def set_scanner_port(self, port: str) -> None:
        """Сохраняет выбранный COM/SPP-порт сканера."""

        self._settings = replace(self._settings, scanner_port=port)
        self._save("Порт сканера сохранен")

    def set_scanner_baudrate(self, baudrate: int) -> None:
        """Сохраняет скорость COM/SPP-порта сканера."""

        self._settings = replace(self._settings, scanner_baudrate=baudrate)
        self._save("Скорость сканера сохранена")

    def set_theme(self, theme_name: str) -> None:
        """Сохраняет и сразу применяет выбранную тему интерфейса."""

        theme = self._theme_manager.get_theme(theme_name)
        self._settings = replace(self._settings, theme_name=theme.name)
        self._theme_manager.set_theme(theme.name, self._qt_app)
        self._save(f"Тема применена: {theme.title}")

    def preview_sound_file(self, filename: str) -> None:
        """Проигрывает выбранный звук из настроек."""

        if filename not in SoundService.available_sound_files():
            self._emit_state(error_message="Файл звука не найден")
            return
        self._sound_service.preview_file(filename)
        self._emit_state(status_message=f"Прослушивание: {filename}")

    def _apply_live_settings(self) -> None:
        """Применяет настройки, которые можно изменить без пересоздания API."""

        self._theme_manager.set_theme(self._settings.theme_name, self._qt_app)
        self._sound_service.set_enabled(self._settings.sound_enabled)
        self._sound_service.set_volume(self._settings.sound_volume)
        self._sound_service.set_sound_file(SoundEvent.OK, self._settings.sound_ok_file)
        self._sound_service.set_sound_file(
            SoundEvent.WARNING,
            self._settings.sound_warning_file,
        )
        self._sound_service.set_sound_file(SoundEvent.ERROR, self._settings.sound_error_file)
        self._sound_service.set_sound_file(
            SoundEvent.VICTORY,
            self._settings.sound_victory_file,
        )

    def _save(self, status_message: str) -> None:
        """Сохраняет настройки и публикует успешный статус."""

        self._settings_store.save(self._settings)
        self._emit_state(status_message=status_message)

    def _emit_state(
        self,
        status_message: str = "",
        error_message: str = "",
    ) -> None:
        """Публикует состояние экрана настроек."""

        self.state_changed.emit(
            SettingsUiState(
                api_base_url=self._settings.api_base_url,
                device_id=self._settings.device_id,
                theme_name=self._settings.theme_name,
                sound_enabled=self._settings.sound_enabled,
                sound_volume=self._settings.sound_volume,
                sound_ok_file=self._settings.sound_ok_file,
                sound_warning_file=self._settings.sound_warning_file,
                sound_error_file=self._settings.sound_error_file,
                sound_victory_file=self._settings.sound_victory_file,
                available_sound_files=SoundService.available_sound_files(),
                status_message=status_message,
                error_message=error_message,
            )
        )
