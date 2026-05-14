"""Страница основных настроек приложения."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState


class AppSettingsPage(QWidget):
    """Редактирует backend URL и идентификатор устройства."""

    back_requested = Signal()
    save_requested = Signal(str, str)

    def __init__(self) -> None:
        """Создает форму основных настроек."""

        super().__init__()
        self._backend_input = QLineEdit()
        self._backend_input.setPlaceholderText("Backend URL")
        self._device_input = QLineEdit()
        self._device_input.setPlaceholderText("Device ID")
        self._save_button = QPushButton("Сохранить основные настройки")
        self._back_button = QPushButton("Назад к настройкам")
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Основные"))
        layout.addWidget(self._backend_input)
        layout.addWidget(self._device_input)
        layout.addWidget(self._save_button)
        layout.addWidget(self._back_button)
        layout.addStretch(1)

    def apply_state(self, state: SettingsUiState) -> None:
        """Заполняет поля из сохраненных настроек."""

        self._backend_input.setText(state.api_base_url)
        self._device_input.setText(state.device_id)

    def values(self) -> tuple[str, str]:
        """Возвращает значения формы основных настроек."""

        return self._backend_input.text(), self._device_input.text()

    def _emit_save(self) -> None:
        """Публикует запрос сохранения основных настроек."""

        self.save_requested.emit(self._backend_input.text(), self._device_input.text())
