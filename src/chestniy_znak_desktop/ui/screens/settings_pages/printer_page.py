"""Страница выбора принтера этикеток."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.printer_controller import PrinterUiState
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    apply_combo_popup_style,
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class PrinterSettingsPage(QWidget):
    """Показывает доступные принтеры и сохраняет выбор."""

    back_requested = Signal()
    refresh_requested = Signal()
    printer_selected = Signal(int)

    def __init__(self) -> None:
        """Создает форму выбора принтера."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._printer_select = QComboBox()
        self._printer_select.setObjectName("settingsCombo")
        apply_combo_popup_style(self._printer_select)
        self._printer_status = QLabel("Принтер не выбран")
        self._printer_status.setObjectName("settingsStatusText")
        self._printer_error = QLabel("")
        self._printer_error.setObjectName("settingsErrorText")
        self._printer_error.setVisible(False)
        self._refresh_button = QPushButton("Обновить принтеры")
        self._refresh_button.setObjectName("settingsPrimaryButton")
        self._back_button = create_back_button()
        self._printer_select.currentIndexChanged.connect(self._emit_printer_selected)
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._back_button.clicked.connect(self.back_requested.emit)

        header = create_page_header(
            title="Принтер",
            subtitle="Выбор принтера этикеток для печати SSCC коробок.",
            icon_name=VectorIconName.SETTINGS,
            icon_color="#f3c969",
        )
        card, card_layout = create_card(
            title="Принтер этикеток",
            subtitle="Список загружается из backend для текущего Device ID.",
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
        )
        card_layout.addWidget(create_form_row("Принтер", self._printer_select))
        card_layout.addWidget(self._refresh_button)
        card_layout.addWidget(self._printer_status)
        card_layout.addWidget(self._printer_error)
        card_layout.addWidget(self._back_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
        layout.addStretch(1)

    def apply_state(self, state: PrinterUiState) -> None:
        """Обновляет список принтеров из состояния контроллера."""

        self._printer_select.blockSignals(True)
        self._printer_select.clear()
        self._printer_select.addItem("Принтер не выбран", 0)
        for printer in state.printers:
            self._printer_select.addItem(printer.title, printer.id)
        if state.selected_printer_id is not None:
            index = self._printer_select.findData(state.selected_printer_id)
            if index >= 0:
                self._printer_select.setCurrentIndex(index)
        self._printer_select.blockSignals(False)
        self._printer_status.setText(state.status_message)
        self._printer_error.setText(state.error_message)
        self._printer_error.setVisible(bool(state.error_message))
        self._printer_select.setEnabled(not state.is_busy)
        self._refresh_button.setEnabled(not state.is_busy)

    def _emit_printer_selected(self, _index: int) -> None:
        """Публикует выбранный принтер."""

        printer_id = int(self._printer_select.currentData() or 0)
        if printer_id > 0:
            self.printer_selected.emit(printer_id)
