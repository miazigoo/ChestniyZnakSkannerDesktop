"""Страница выбора темы интерфейса."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.themes.theme import available_themes, theme_by_name
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class ThemeSettingsPage(QWidget):
    """Редактирует тему интерфейса."""

    back_requested = Signal()
    save_requested = Signal(str)

    def __init__(self) -> None:
        """Создает форму выбора темы."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._theme_select = QComboBox()
        self._theme_select.setObjectName("settingsCombo")
        for theme in available_themes():
            self._theme_select.addItem(theme.title, theme.name)
        self._save_button = QPushButton("Сохранить")
        self._save_button.setObjectName("settingsPrimaryButton")
        self._back_button = create_back_button()
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        header = create_page_header(
            title="Тема",
            subtitle="Визуальный стиль рабочего интерфейса.",
            icon_name=VectorIconName.SETTINGS,
            icon_color="#8fb8ff",
        )
        card, card_layout = create_card(
            title="Оформление",
            subtitle="Тема применяется сразу после сохранения.",
            icon_name=VectorIconName.SHIELD,
            icon_color="#66d2c7",
        )
        card_layout.addWidget(create_form_row("Тема интерфейса", self._theme_select))
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
        """Устанавливает текущую тему в combo box."""

        theme_index = self._theme_select.findData(theme_by_name(state.theme_name).name)
        if theme_index >= 0:
            self._theme_select.setCurrentIndex(theme_index)

    def value(self) -> str:
        """Возвращает выбранную тему."""

        return str(self._theme_select.currentData() or "light")

    def _emit_save(self) -> None:
        """Публикует запрос сохранения темы."""

        self.save_requested.emit(self.value())
