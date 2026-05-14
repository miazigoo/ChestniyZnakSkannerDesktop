"""Страница выбора темы интерфейса."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState


class ThemeSettingsPage(QWidget):
    """Редактирует тему интерфейса."""

    back_requested = Signal()
    save_requested = Signal(str)

    def __init__(self) -> None:
        """Создает форму выбора темы."""

        super().__init__()
        self._theme_select = QComboBox()
        self._theme_select.addItems(["light", "dark"])
        self._save_button = QPushButton("Сохранить тему")
        self._back_button = QPushButton("Назад к настройкам")
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Тема"))
        layout.addWidget(self._theme_select)
        layout.addWidget(self._save_button)
        layout.addWidget(self._back_button)
        layout.addStretch(1)

    def apply_state(self, state: SettingsUiState) -> None:
        """Устанавливает текущую тему в combo box."""

        theme_index = self._theme_select.findText(state.theme_name)
        if theme_index >= 0:
            self._theme_select.setCurrentIndex(theme_index)

    def value(self) -> str:
        """Возвращает выбранную тему."""

        return self._theme_select.currentText()

    def _emit_save(self) -> None:
        """Публикует запрос сохранения темы."""

        self.save_requested.emit(self._theme_select.currentText())
