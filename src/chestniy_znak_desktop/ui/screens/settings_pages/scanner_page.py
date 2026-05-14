"""Страница настроек COM/SPP-сканера."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.scanner_controller import ScannerUiState


class ScannerSettingsPage(QWidget):
    """Редактирует порт и скорость COM/SPP-сканера."""

    back_requested = Signal()
    ports_refresh_requested = Signal()
    scanner_start_requested = Signal()
    scanner_stop_requested = Signal()
    port_changed = Signal(str)
    baudrate_changed = Signal(int)

    def __init__(self) -> None:
        """Создает форму настроек сканера."""

        super().__init__()
        self._scanner_port = QComboBox()
        self._scanner_port.setEditable(True)
        self._scanner_port.currentTextChanged.connect(self.port_changed.emit)
        self._scanner_baudrate = QComboBox()
        self._scanner_baudrate.addItems(["9600", "19200", "38400", "57600", "115200"])
        self._scanner_baudrate.currentTextChanged.connect(self._emit_baudrate)
        self._scanner_status = QLabel("Сканер не запущен")
        self._scanner_error = QLabel("")
        self._refresh_ports_button = QPushButton("Обновить порты")
        self._start_scanner_button = QPushButton("Запустить сканер")
        self._stop_scanner_button = QPushButton("Остановить сканер")
        self._back_button = QPushButton("Назад к настройкам")
        self._refresh_ports_button.clicked.connect(self.ports_refresh_requested.emit)
        self._start_scanner_button.clicked.connect(self.scanner_start_requested.emit)
        self._stop_scanner_button.clicked.connect(self.scanner_stop_requested.emit)
        self._back_button.clicked.connect(self.back_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(self._refresh_ports_button)
        actions.addWidget(self._start_scanner_button)
        actions.addWidget(self._stop_scanner_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Сканер"))
        layout.addWidget(QLabel("COM/SPP порт сканера"))
        layout.addWidget(self._scanner_port)
        layout.addWidget(QLabel("Скорость порта"))
        layout.addWidget(self._scanner_baudrate)
        layout.addLayout(actions)
        layout.addWidget(self._scanner_status)
        layout.addWidget(self._scanner_error)
        layout.addWidget(self._back_button)
        layout.addStretch(1)

    def apply_state(self, state: ScannerUiState) -> None:
        """Обновляет форму из состояния сканера."""

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

        if value:
            self.baudrate_changed.emit(int(value))
