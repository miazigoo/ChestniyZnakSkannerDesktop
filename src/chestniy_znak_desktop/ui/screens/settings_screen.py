"""Экран настроек desktop-клиента."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.controllers.scanner_controller import ScannerUiState
from chestniy_znak_desktop.controllers.settings_controller import (
    SettingsFormData,
    SettingsUiState,
)
from chestniy_znak_desktop.ui.screens.settings_pages.app_page import AppSettingsPage
from chestniy_znak_desktop.ui.screens.settings_pages.hub_page import SettingsHubPage
from chestniy_znak_desktop.ui.screens.settings_pages.scanner_page import (
    ScannerSettingsPage,
)
from chestniy_znak_desktop.ui.screens.settings_pages.sound_page import SoundSettingsPage
from chestniy_znak_desktop.ui.screens.settings_pages.theme_page import ThemeSettingsPage


class SettingsScreen(QWidget):
    """Показывает настройки приложения через отдельные группы."""

    scanner_ports_refresh_requested = Signal()
    scanner_start_requested = Signal()
    scanner_stop_requested = Signal()
    scanner_port_changed = Signal(str)
    scanner_baudrate_changed = Signal(int)
    settings_save_requested = Signal(SettingsFormData)
    theme_selected = Signal(str)
    sound_preview_requested = Signal(str)

    def __init__(self) -> None:
        """Создает grouped-навигацию настроек."""

        super().__init__()
        self._settings_state = SettingsUiState(
            api_base_url=AppConfig().api_base_url,
            device_id=AppConfig().device_id,
            language="ru",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.85,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
            available_sound_files=[],
        )
        self.setObjectName("settingsScreen")
        self._stack = QStackedWidget()
        self._stack.setObjectName("settingsStack")
        self._hub_page = SettingsHubPage()
        self._app_page = AppSettingsPage()
        self._scanner_page = ScannerSettingsPage()
        self._theme_page = ThemeSettingsPage()
        self._sound_page = SoundSettingsPage()
        self._status_label = QLabel("")
        self._status_label.setObjectName("settingsStatusText")
        self._error_label = QLabel("")
        self._error_label.setObjectName("settingsErrorText")
        self._error_label.setVisible(False)
        self._register_pages()
        self._connect_pages()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._stack, stretch=1)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)

    def apply_settings_state(self, state: SettingsUiState) -> None:
        """Обновляет все страницы из состояния пользовательских настроек."""

        self._settings_state = state
        self._app_page.apply_state(state)
        self._theme_page.apply_state(state)
        self._sound_page.apply_state(state)
        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._error_label.setVisible(bool(state.error_message))

    def apply_scanner_state(self, state: ScannerUiState) -> None:
        """Обновляет страницу сканера."""

        self._scanner_page.apply_state(state)

    def _register_pages(self) -> None:
        """Добавляет страницы в стек настроек."""

        for page in (
            self._hub_page,
            self._app_page,
            self._scanner_page,
            self._theme_page,
            self._sound_page,
        ):
            self._stack.addWidget(page)

    def _connect_pages(self) -> None:
        """Связывает внутренние страницы с внешними сигналами."""

        self._hub_page.app_requested.connect(lambda: self._show_page(self._app_page))
        self._hub_page.scanner_requested.connect(lambda: self._show_page(self._scanner_page))
        self._hub_page.theme_requested.connect(lambda: self._show_page(self._theme_page))
        self._hub_page.sound_requested.connect(lambda: self._show_page(self._sound_page))
        for page in (
            self._app_page,
            self._scanner_page,
            self._theme_page,
            self._sound_page,
        ):
            page.back_requested.connect(self._show_hub)

        self._app_page.save_requested.connect(self._save_app_settings)
        self._scanner_page.ports_refresh_requested.connect(
            self.scanner_ports_refresh_requested.emit
        )
        self._scanner_page.scanner_start_requested.connect(self.scanner_start_requested.emit)
        self._scanner_page.scanner_stop_requested.connect(self.scanner_stop_requested.emit)
        self._scanner_page.port_changed.connect(self.scanner_port_changed.emit)
        self._scanner_page.baudrate_changed.connect(self.scanner_baudrate_changed.emit)
        self._theme_page.theme_selected.connect(self._select_theme_settings)
        self._sound_page.save_requested.connect(self._save_sound_settings)
        self._sound_page.preview_requested.connect(self.sound_preview_requested.emit)

    def _show_hub(self) -> None:
        """Возвращает пользователя на список групп настроек."""

        self._show_page(self._hub_page)

    def _show_page(self, page: QWidget) -> None:
        """Переключает стек на указанную страницу."""

        self._stack.setCurrentWidget(page)

    def _save_app_settings(self, api_base_url: str, device_id: str) -> None:
        """Сохраняет backend URL и device ID через общий DTO настроек."""

        state = replace(
            self._settings_state,
            api_base_url=api_base_url,
            device_id=device_id,
            language=self._app_page.language(),
        )
        self._emit_settings_save(state)

    def _select_theme_settings(self, theme_name: str) -> None:
        """Сохраняет выбранную тему отдельным быстрым действием."""

        self._settings_state = replace(self._settings_state, theme_name=theme_name)
        self.theme_selected.emit(theme_name)

    def _save_sound_settings(
        self,
        enabled: bool,
        volume: float,
        ok_file: str,
        warning_file: str,
        error_file: str,
        victory_file: str,
    ) -> None:
        """Сохраняет выбранные звуки через общий DTO настроек."""

        self._emit_settings_save(
            replace(
                self._settings_state,
                sound_enabled=enabled,
                sound_volume=volume,
                sound_ok_file=ok_file,
                sound_warning_file=warning_file,
                sound_error_file=error_file,
                sound_victory_file=victory_file,
            )
        )

    def _emit_settings_save(self, state: SettingsUiState) -> None:
        """Преобразует UI-state в форму сохранения настроек."""

        self.settings_save_requested.emit(
            SettingsFormData(
                api_base_url=state.api_base_url,
                device_id=state.device_id,
                language=state.language,
                theme_name=state.theme_name,
                sound_enabled=state.sound_enabled,
                sound_volume=state.sound_volume,
                sound_ok_file=state.sound_ok_file,
                sound_warning_file=state.sound_warning_file,
                sound_error_file=state.sound_error_file,
                sound_victory_file=state.sound_victory_file,
            )
        )
