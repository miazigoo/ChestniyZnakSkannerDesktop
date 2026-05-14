"""Основной экран упаковки кодов в коробку."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.packing_controller import PackingUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot


class PackingScreen(QWidget):
    """Рабочий экран оператора упаковки."""

    refresh_requested = Signal()
    open_box_requested = Signal()
    close_box_requested = Signal()
    count_in_packing_changed = Signal(bool)

    def __init__(self) -> None:
        """Создает базовую раскладку экрана упаковки."""

        super().__init__()
        self._title_label = QLabel("Упаковка")
        self._status_label = QLabel("Открытая коробка не найдена")
        self._scanner_label = QLabel("Сканер: проверяем состояние")
        self._result_label = QLabel("")
        self._error_label = QLabel("")
        self._box_label = QLabel("Коробка: -")
        self._progress_label = QLabel("0 / 0")
        self._count_in_packing = QCheckBox("Учитывать в упаковке")
        self._count_in_packing.setChecked(True)
        self._count_in_packing.toggled.connect(self.count_in_packing_changed.emit)
        self._refresh_button = QPushButton("Обновить")
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._open_box_button = QPushButton("Открыть коробку")
        self._open_box_button.clicked.connect(self.open_box_requested.emit)
        self._close_box_button = QPushButton("Закрыть коробку")
        self._close_box_button.clicked.connect(self.close_box_requested.emit)
        self._items_table = QTableWidget(0, 3)
        self._items_table.setHorizontalHeaderLabels(["GTIN", "Serial", "Код"])

        actions = QHBoxLayout()
        actions.addWidget(self._refresh_button)
        actions.addWidget(self._open_box_button)
        actions.addWidget(self._close_box_button)
        actions.addStretch(1)
        actions.addWidget(self._count_in_packing)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._scanner_label)
        layout.addWidget(self._result_label)
        layout.addWidget(self._error_label)
        layout.addWidget(self._box_label)
        layout.addWidget(self._progress_label)
        layout.addLayout(actions)
        layout.addWidget(self._items_table)
        self._is_busy = False
        self._scanner_ready = False

    def apply_state(self, state: PackingUiState) -> None:
        """Обновляет экран из состояния контроллера упаковки."""

        self._status_label.setText(state.status_message)
        self._result_label.setText(state.result_message)
        self._error_label.setText(state.error_message)
        self._count_in_packing.blockSignals(True)
        self._count_in_packing.setChecked(state.count_in_packing)
        self._count_in_packing.blockSignals(False)
        self._set_busy(state.is_busy)
        if state.current_box is None:
            self._box_label.setText("Коробка: -")
            self._progress_label.setText("0 / 0")
            self._items_table.setRowCount(0)
            return
        box = state.current_box
        self._box_label.setText(f"Коробка #{box.box_id}  Заказ: {box.order_name or '-'}")
        self._progress_label.setText(f"{box.filled} / {box.capacity}")
        self._items_table.setRowCount(len(box.items))
        for row, item in enumerate(box.items):
            self._items_table.setItem(row, 0, QTableWidgetItem(item.gtin))
            self._items_table.setItem(row, 1, QTableWidgetItem(item.serial))
            self._items_table.setItem(row, 2, QTableWidgetItem(item.visible_code))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет защиту рабочих действий по состоянию сканера."""

        self._scanner_ready = snapshot.scanner.is_running
        if self._scanner_ready:
            self._scanner_label.setText(f"Сканер готов: {snapshot.scanner.port}")
        else:
            self._scanner_label.setText("Сканер не запущен. Упаковка заблокирована.")
        self._set_busy(self._is_busy)

    def _set_busy(self, is_busy: bool) -> None:
        """Включает или отключает рабочие кнопки на время операции."""

        self._is_busy = is_busy
        self._refresh_button.setEnabled(not is_busy)
        self._open_box_button.setEnabled(not is_busy and self._scanner_ready)
        self._close_box_button.setEnabled(not is_busy and self._scanner_ready)
