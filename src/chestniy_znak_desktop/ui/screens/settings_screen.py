"""Экран настроек desktop-клиента."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.scanner_controller import ScannerUiState


class SettingsScreen(QWidget):
    """Показывает настройки backend, сканера, темы и звуков."""

    scanner_ports_refresh_requested = Signal()
    scanner_start_requested = Signal()
    scanner_stop_requested = Signal()
    scanner_port_changed = Signal(str)
    scanner_baudrate_changed = Signal(int)

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
        self._scanner_port.currentTextChanged.connect(self.scanner_port_changed.emit)
        self._scanner_baudrate = QComboBox()
        self._scanner_baudrate.addItems(["9600", "19200", "38400", "57600", "115200"])
        self._scanner_baudrate.currentTextChanged.connect(self._emit_baudrate)
        self._scanner_status = QLabel("Сканер не запущен")
        self._scanner_error = QLabel("")
        self._refresh_ports_button = QPushButton("Обновить порты")
        self._refresh_ports_button.clicked.connect(self.scanner_ports_refresh_requested.emit)
        self._start_scanner_button = QPushButton("Запустить сканер")
        self._start_scanner_button.clicked.connect(self.scanner_start_requested.emit)
        self._stop_scanner_button = QPushButton("Остановить сканер")
        self._stop_scanner_button.clicked.connect(self.scanner_stop_requested.emit)
        self._theme_select = QComboBox()
        self._theme_select.addItems(["light", "dark"])
        self._sound_enabled = QCheckBox("Звуки включены")
        self._sound_enabled.setChecked(True)
        scanner_actions = QHBoxLayout()
        scanner_actions.addWidget(self._refresh_ports_button)
        scanner_actions.addWidget(self._start_scanner_button)
        scanner_actions.addWidget(self._stop_scanner_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._backend_input)
        layout.addWidget(self._device_input)
        layout.addWidget(QLabel("COM/SPP порт сканера"))
        layout.addWidget(self._scanner_port)
        layout.addWidget(QLabel("Скорость порта"))
        layout.addWidget(self._scanner_baudrate)
        layout.addLayout(scanner_actions)
        layout.addWidget(self._scanner_status)
        layout.addWidget(self._scanner_error)
        layout.addWidget(self._theme_select)
        layout.addWidget(self._sound_enabled)
        layout.addStretch(1)

    def apply_scanner_state(self, state: ScannerUiState) -> None:
        """Обновляет элементы настроек сканера."""

        self._scanner_port.blockSignals(True)
        self._scanner_port.clear()
        for port in state.ports:
            self._scanner_port.addItem(port.title, port.device)
        if state.selected_port:
            index = self._scanner_port.findData(state.selected_port)
            if index >= 0:
                self._scanner_port.setCurrentIndex(index)
            else:
                self._scanner_port.setEditText(state.selected_port)
        self._scanner_port.blockSignals(False)
        self._scanner_baudrate.blockSignals(True)
        baudrate_index = self._scanner_baudrate.findText(str(state.baudrate))
        if baudrate_index >= 0:
            self._scanner_baudrate.setCurrentIndex(baudrate_index)
        self._scanner_baudrate.blockSignals(False)
        self._scanner_status.setText(state.status_message)
        self._scanner_error.setText(state.error_message)
        self._start_scanner_button.setEnabled(not state.is_running)
        self._stop_scanner_button.setEnabled(state.is_running)

    def _emit_baudrate(self, value: str) -> None:
        """Публикует выбранную скорость serial-порта."""

        if not value:
            return
        self.scanner_baudrate_changed.emit(int(value))
