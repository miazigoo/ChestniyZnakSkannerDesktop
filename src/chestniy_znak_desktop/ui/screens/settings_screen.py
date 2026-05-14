"""Экран настроек desktop-клиента."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QLineEdit, QVBoxLayout, QWidget


class SettingsScreen(QWidget):
    """Показывает настройки backend, сканера, темы и звуков."""

    def __init__(self) -> None:
        """Создает базовую форму настроек."""

        super().__init__()
        self._title = QLabel("Настройки")
        self._backend_input = QLineEdit()
        self._backend_input.setPlaceholderText("Backend URL")
        self._device_input = QLineEdit()
        self._device_input.setPlaceholderText("Device ID")
        self._scanner_port = QComboBox()
        self._scanner_port.setEditable(True)
        self._theme_select = QComboBox()
        self._theme_select.addItems(["light", "dark"])
        self._sound_enabled = QCheckBox("Звуки включены")
        self._sound_enabled.setChecked(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._backend_input)
        layout.addWidget(self._device_input)
        layout.addWidget(self._scanner_port)
        layout.addWidget(self._theme_select)
        layout.addWidget(self._sound_enabled)
        layout.addStretch(1)
