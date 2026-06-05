"""Страница настроек COM/SPP-сканера."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.scanner_controller import ScannerUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    apply_combo_popup_style,
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


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
        self.setObjectName("settingsPage")
        self._scanner_port = QComboBox()
        self._scanner_port.setObjectName("settingsCombo")
        apply_combo_popup_style(self._scanner_port)
        self._scanner_port.setEditable(True)
        self._scanner_port.currentTextChanged.connect(self.port_changed.emit)
        self._scanner_baudrate = QComboBox()
        self._scanner_baudrate.setObjectName("settingsCombo")
        apply_combo_popup_style(self._scanner_baudrate)
        self._scanner_baudrate.addItems(["9600", "19200", "38400", "57600", "115200"])
        self._scanner_baudrate.currentTextChanged.connect(self._emit_baudrate)
        self._scanner_status = QLabel(tr("settings.scanner.notRunning"))
        self._scanner_status.setObjectName("settingsStatusText")
        self._scanner_sources = QLabel(self._format_sources(ScannerUiState()))
        self._scanner_sources.setObjectName("settingsStatusText")
        self._scanner_sources.setWordWrap(True)
        self._hid_devices = QLabel(tr("settings.scanner.hidNotFound"))
        self._hid_devices.setObjectName("settingsStatusText")
        self._hid_devices.setWordWrap(True)
        self._scanner_error = QLabel("")
        self._scanner_error.setObjectName("settingsErrorText")
        self._scanner_error.setVisible(False)
        self._refresh_ports_button = QPushButton(tr("settings.scanner.refreshPorts"))
        self._refresh_ports_button.setObjectName("settingsSecondaryButton")
        self._start_scanner_button = QPushButton(tr("settings.scanner.startCom"))
        self._start_scanner_button.setObjectName("settingsPrimaryButton")
        self._stop_scanner_button = QPushButton(tr("settings.scanner.stopAll"))
        self._stop_scanner_button.setObjectName("settingsDangerButton")
        self._back_button = create_back_button()
        self._refresh_ports_button.clicked.connect(self.ports_refresh_requested.emit)
        self._start_scanner_button.clicked.connect(self.scanner_start_requested.emit)
        self._stop_scanner_button.clicked.connect(self.scanner_stop_requested.emit)
        self._back_button.clicked.connect(self.back_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(self._refresh_ports_button)
        actions.addWidget(self._start_scanner_button)
        actions.addWidget(self._stop_scanner_button)
        actions.addStretch(1)

        header = create_page_header(
            title=tr("settings.scanner.title"),
            subtitle=tr("settings.scanner.subtitle"),
            icon_name=VectorIconName.SCANNER,
            icon_color="#8fb8ff",
        )
        card, card_layout = create_card(
            title=tr("settings.scanner.cardTitle"),
            subtitle=tr("settings.scanner.cardSubtitle"),
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
        )
        card_layout.addWidget(create_form_row(tr("settings.scanner.port"), self._scanner_port))
        card_layout.addWidget(
            create_form_row(tr("settings.scanner.baudrate"), self._scanner_baudrate)
        )
        card_layout.addLayout(actions)
        card_layout.addWidget(self._scanner_status)
        card_layout.addWidget(self._scanner_sources)
        card_layout.addWidget(self._hid_devices)
        card_layout.addWidget(self._scanner_error)
        card_layout.addWidget(self._back_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
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
        self._scanner_sources.setText(self._format_sources(state))
        self._hid_devices.setText(self._format_hid_devices(state))
        self._scanner_error.setText(state.error_message)
        self._scanner_error.setVisible(bool(state.error_message))
        self._start_scanner_button.setEnabled(
            bool(state.selected_port) and state.selected_port not in state.active_serial_ports
        )
        self._stop_scanner_button.setEnabled(state.is_running)

    def _emit_baudrate(self, value: str) -> None:
        """Публикует выбранную скорость serial-порта."""

        if value:
            self.baudrate_changed.emit(int(value))

    @staticmethod
    def _format_sources(state: ScannerUiState) -> str:
        """Возвращает читаемый список активных источников сканов."""

        sources: list[str] = []
        if state.serial_running:
            sources.append("COM: " + ", ".join(state.active_serial_ports))
        if state.hid_running:
            sources.append(tr("settings.scanner.sourceHidActive"))
        if not sources:
            sources.append(tr("settings.scanner.sourceNone"))
        return f"{tr('settings.scanner.sourcesPrefix')}: " + "; ".join(sources)

    @staticmethod
    def _format_hid_devices(state: ScannerUiState) -> str:
        """Возвращает список HID-устройств, которые видит приложение."""

        if not state.hid_devices:
            return tr("settings.scanner.hidNotFound")
        return tr("settings.scanner.hidDevices", devices="; ".join(state.hid_devices))
