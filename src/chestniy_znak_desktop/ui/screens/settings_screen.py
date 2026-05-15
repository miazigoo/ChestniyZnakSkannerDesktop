"""Экран настроек desktop-клиента."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.controllers.printer_controller import PrinterUiState
from chestniy_znak_desktop.controllers.scanner_controller import ScannerUiState
from chestniy_znak_desktop.controllers.settings_controller import (
    SettingsFormData,
    SettingsUiState,
)
from chestniy_znak_desktop.ui.screens.settings_pages.app_page import AppSettingsPage
from chestniy_znak_desktop.ui.screens.settings_pages.hub_page import SettingsHubPage
from chestniy_znak_desktop.ui.screens.settings_pages.printer_page import (
    PrinterSettingsPage,
)
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
    printer_refresh_requested = Signal()
    printer_selected = Signal(int)
    sound_preview_requested = Signal(str)

    def __init__(self) -> None:
        """Создает grouped-навигацию настроек."""

        super().__init__()
        self._settings_state = SettingsUiState(
            api_base_url=AppConfig().api_base_url,
            device_id=AppConfig().device_id,
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
        self._printer_page = PrinterSettingsPage()
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
        self._apply_styles()

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

    def apply_printer_state(self, state: PrinterUiState) -> None:
        """Обновляет страницу принтера."""

        self._printer_page.apply_state(state)

    def _register_pages(self) -> None:
        """Добавляет страницы в стек настроек."""

        for page in (
            self._hub_page,
            self._app_page,
            self._scanner_page,
            self._printer_page,
            self._theme_page,
            self._sound_page,
        ):
            self._stack.addWidget(page)

    def _connect_pages(self) -> None:
        """Связывает внутренние страницы с внешними сигналами."""

        self._hub_page.app_requested.connect(lambda: self._show_page(self._app_page))
        self._hub_page.scanner_requested.connect(lambda: self._show_page(self._scanner_page))
        self._hub_page.printer_requested.connect(lambda: self._show_page(self._printer_page))
        self._hub_page.theme_requested.connect(lambda: self._show_page(self._theme_page))
        self._hub_page.sound_requested.connect(lambda: self._show_page(self._sound_page))
        for page in (
            self._app_page,
            self._scanner_page,
            self._printer_page,
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
        self._printer_page.refresh_requested.connect(self.printer_refresh_requested.emit)
        self._printer_page.printer_selected.connect(self.printer_selected.emit)
        self._theme_page.save_requested.connect(self._save_theme_settings)
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
        )
        self._emit_settings_save(state)

    def _save_theme_settings(self, theme_name: str) -> None:
        """Сохраняет выбранную тему через общий DTO настроек."""

        self._emit_settings_save(replace(self._settings_state, theme_name=theme_name))

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
                theme_name=state.theme_name,
                sound_enabled=state.sound_enabled,
                sound_volume=state.sound_volume,
                sound_ok_file=state.sound_ok_file,
                sound_warning_file=state.sound_warning_file,
                sound_error_file=state.sound_error_file,
                sound_victory_file=state.sound_victory_file,
            )
        )

    def _apply_styles(self) -> None:
        """Применяет общий стиль раздела настроек."""

        self.setStyleSheet("""
            #settingsScreen,
            #settingsPage,
            #settingsStack {
                background: transparent;
            }
            #settingsPageHeader,
            #settingsCard {
                background: rgba(16, 24, 40, 222);
                border: 1px solid rgba(129, 140, 168, 70);
                border-radius: 18px;
            }
            #settingsPageHeader {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(33, 52, 76, 238),
                    stop: 0.56 rgba(18, 32, 48, 235),
                    stop: 1 rgba(28, 70, 67, 222)
                );
            }
            #settingsPageTitle {
                color: #f8fbff;
                font-size: 25px;
                font-weight: 850;
                background: transparent;
            }
            #settingsPageSubtitle,
            #settingsMutedText,
            #settingsStatusText {
                color: rgba(225, 233, 244, 176);
                font-size: 13px;
                background: transparent;
            }
            #settingsCardTitle {
                color: #f8fbff;
                font-size: 17px;
                font-weight: 800;
                background: transparent;
            }
            #settingsHubButton {
                min-height: 86px;
                border: 1px solid rgba(129, 140, 168, 70);
                border-radius: 18px;
                padding: 18px 20px;
                color: #f8fbff;
                background: rgba(16, 24, 40, 222);
                font-size: 17px;
                font-weight: 850;
                text-align: left;
            }
            #settingsHubButton:hover {
                border: 1px solid rgba(102, 210, 199, 150);
                background: rgba(23, 39, 57, 235);
            }
            #settingsFormRow {
                background: rgba(255, 255, 255, 22);
                border: 1px solid rgba(129, 140, 168, 45);
                border-radius: 14px;
            }
            #settingsFormLabel {
                color: rgba(225, 233, 244, 190);
                font-size: 13px;
                font-weight: 750;
                background: transparent;
            }
            #settingsInput,
            #settingsCombo {
                min-height: 38px;
                color: #f8fbff;
                background: rgba(255, 255, 255, 28);
                border: 1px solid rgba(129, 140, 168, 70);
                border-radius: 12px;
                padding: 0 12px;
                font-weight: 650;
            }
            #settingsInput:focus,
            #settingsCombo:focus {
                border: 1px solid rgba(102, 210, 199, 190);
            }
            #settingsCheckBox {
                color: rgba(225, 233, 244, 210);
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }
            #settingsSlider {
                min-height: 34px;
                background: transparent;
            }
            #settingsPrimaryButton,
            #settingsSecondaryButton,
            #settingsDangerButton {
                min-height: 38px;
                border: 0;
                border-radius: 12px;
                padding: 0 14px;
                font-weight: 800;
            }
            #settingsPrimaryButton {
                color: #071212;
                background: #66d2c7;
            }
            #settingsSecondaryButton {
                color: #f8fbff;
                background: rgba(255, 255, 255, 42);
            }
            #settingsDangerButton {
                color: #fff4f2;
                background: rgba(227, 85, 78, 190);
            }
            #settingsPrimaryButton:disabled,
            #settingsSecondaryButton:disabled,
            #settingsDangerButton:disabled {
                color: rgba(225, 233, 244, 92);
                background: rgba(255, 255, 255, 22);
            }
            #settingsErrorText {
                color: #ffb4ad;
                border-radius: 12px;
                padding: 9px 11px;
                background: rgba(227, 85, 78, 38);
                font-weight: 750;
            }
            #settingsInlinePicker {
                background: transparent;
                border: 0;
            }
            """)
