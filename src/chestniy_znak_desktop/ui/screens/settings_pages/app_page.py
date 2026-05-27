"""Страница основных настроек приложения."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState
from chestniy_znak_desktop.i18n import LANGUAGE_TITLES, SUPPORTED_LANGUAGES, tr
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class AppSettingsPage(QWidget):
    """Редактирует backend URL и идентификатор устройства."""

    back_requested = Signal()
    save_requested = Signal(str, str)

    def __init__(self) -> None:
        """Создает форму основных настроек."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._backend_input = QLineEdit()
        self._backend_input.setObjectName("settingsInput")
        self._backend_input.setPlaceholderText("Backend URL")
        self._device_input = QLineEdit()
        self._device_input.setObjectName("settingsInput")
        self._device_input.setPlaceholderText("Device ID")
        self._language_select = QComboBox()
        self._language_select.setObjectName("settingsInput")
        for language in SUPPORTED_LANGUAGES:
            self._language_select.addItem(LANGUAGE_TITLES[language], language)
        self._save_button = QPushButton(tr("common.save"))
        self._save_button.setObjectName("settingsPrimaryButton")
        self._back_button = create_back_button()
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        header = create_page_header(
            title=tr("settings.main.title"),
            subtitle=tr("settings.main.subtitle"),
            icon_name=VectorIconName.SETTINGS,
            icon_color="#8fb8ff",
        )
        card, card_layout = create_card(
            title=tr("settings.connection.title"),
            subtitle=tr("settings.connection.subtitle"),
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
        )
        card_layout.addWidget(create_form_row("Backend URL", self._backend_input))
        card_layout.addWidget(create_form_row("Device ID", self._device_input))
        card_layout.addWidget(create_form_row(tr("common.language"), self._language_select))
        actions = QHBoxLayout()
        actions.addWidget(self._save_button)
        actions.addWidget(self._back_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
        layout.addStretch(1)

    def apply_state(self, state: SettingsUiState) -> None:
        """Заполняет поля из сохраненных настроек."""

        self._backend_input.setText(state.api_base_url)
        self._device_input.setText(state.device_id)
        index = self._language_select.findData(state.language)
        self._language_select.setCurrentIndex(max(index, 0))

    def values(self) -> tuple[str, str]:
        """Возвращает значения формы основных настроек."""

        return self._backend_input.text(), self._device_input.text()

    def language(self) -> str:
        """Возвращает выбранный язык интерфейса/API."""

        return str(self._language_select.currentData() or "ru")

    def _emit_save(self) -> None:
        """Публикует запрос сохранения основных настроек."""

        self.save_requested.emit(self._backend_input.text(), self._device_input.text())
