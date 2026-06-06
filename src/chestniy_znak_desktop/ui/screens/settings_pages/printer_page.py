"""Страница выбора SSCC-принтера рабочего места."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.printer_controller import PrinterUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    apply_combo_popup_style,
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class PrinterSettingsPage(QWidget):
    """Показывает доступные принтеры поставщика и сохраняет выбор рабочего места."""

    back_requested = Signal()
    refresh_requested = Signal()
    printer_selected = Signal(int)

    def __init__(self) -> None:
        """Создает форму выбора принтера."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._printer_combo = QComboBox()
        self._printer_combo.setObjectName("settingsCombo")
        apply_combo_popup_style(self._printer_combo)
        self._printer_ids: list[int] = []
        self._status_label = QLabel(tr("printer.notLoaded"))
        self._status_label.setObjectName("settingsStatusText")
        self._status_label.setWordWrap(True)
        self._error_label = QLabel("")
        self._error_label.setObjectName("settingsErrorText")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        self._refresh_button = QPushButton(tr("printer.refresh"))
        self._refresh_button.setObjectName("settingsSecondaryButton")
        self._back_button = create_back_button()
        self._printer_combo.currentIndexChanged.connect(self._emit_printer_selected)
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._back_button.clicked.connect(self.back_requested.emit)

        header = create_page_header(
            title=tr("settings.printer.title"),
            subtitle=tr("settings.printer.subtitle"),
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
        )
        card, card_layout = create_card(
            title=tr("settings.printer.cardTitle"),
            subtitle=tr("settings.printer.cardSubtitle"),
            icon_name=VectorIconName.BOX,
            icon_color="#f3c969",
        )
        card_layout.addWidget(create_form_row(tr("printer.ssccPrinter"), self._printer_combo))
        card_layout.addWidget(self._status_label)
        card_layout.addWidget(self._error_label)

        actions = QHBoxLayout()
        actions.addWidget(self._refresh_button)
        actions.addWidget(self._back_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
        layout.addStretch(1)

    def apply_state(self, state: PrinterUiState) -> None:
        """Обновляет список принтеров и выбранное значение."""

        self._printer_combo.blockSignals(True)
        self._printer_combo.clear()
        self._printer_ids = []
        if state.is_busy:
            self._printer_combo.addItem(tr("printer.loading"))
        elif not state.options:
            self._printer_combo.addItem(tr("printer.empty"))
        else:
            if state.selected_printer_id is None and len(state.options) > 1:
                self._printer_ids.append(0)
                self._printer_combo.addItem(tr("printer.choosePlaceholder"))
            for option in state.options:
                self._printer_ids.append(option.id)
                self._printer_combo.addItem(option.label)
            selected_id = state.selected_printer_id
            selected_index = (
                self._printer_ids.index(selected_id)
                if selected_id is not None and selected_id in self._printer_ids
                else -1
            )
            self._printer_combo.setCurrentIndex(max(selected_index, 0))
        self._printer_combo.blockSignals(False)

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._error_label.setVisible(bool(state.error_message))
        self._printer_combo.setEnabled(not state.is_busy and bool(state.options))
        self._refresh_button.setEnabled(not state.is_busy)

    def _emit_printer_selected(self, index: int) -> None:
        """Публикует выбранный принтер."""

        if index < 0 or index >= len(self._printer_ids):
            return
        printer_id = self._printer_ids[index]
        if printer_id > 0:
            self.printer_selected.emit(printer_id)
