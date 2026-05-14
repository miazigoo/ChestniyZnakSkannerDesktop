"""Экран списка коробок."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.boxes_controller import BoxesUiState


class BoxesScreen(QWidget):
    """Показывает список коробок и поиск по ним."""

    refresh_requested = Signal()
    search_requested = Signal(str)
    status_filter_changed = Signal(str)
    next_page_requested = Signal()
    previous_page_requested = Signal()

    def __init__(self) -> None:
        """Создает базовый экран списка коробок."""

        super().__init__()
        self._title = QLabel("Список коробок")
        self._status_label = QLabel("Загрузите список коробок")
        self._error_label = QLabel("")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по SSCC, заказу или ID")
        self._search_input.returnPressed.connect(self._emit_search)
        self._status_filter = QComboBox()
        self._status_filter.addItem("Все", "all")
        self._status_filter.addItem("Открытые", "open")
        self._status_filter.addItem("Закрытые", "closed")
        self._status_filter.currentIndexChanged.connect(self._emit_status_filter)
        self._search_button = QPushButton("Найти")
        self._search_button.clicked.connect(self._emit_search)
        self._refresh_button = QPushButton("Обновить")
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._previous_button = QPushButton("Назад")
        self._previous_button.clicked.connect(self.previous_page_requested.emit)
        self._next_button = QPushButton("Дальше")
        self._next_button.clicked.connect(self.next_page_requested.emit)
        self._page_label = QLabel("0 / 0")
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Заказ", "SSCC", "Заполнено", "Статус", "Оператор", "Печать"]
        )

        filters = QHBoxLayout()
        filters.addWidget(self._status_filter)
        filters.addWidget(self._search_input, stretch=1)
        filters.addWidget(self._search_button)
        filters.addWidget(self._refresh_button)

        pagination = QHBoxLayout()
        pagination.addWidget(self._previous_button)
        pagination.addWidget(self._page_label)
        pagination.addWidget(self._next_button)
        pagination.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addLayout(filters)
        layout.addWidget(self._table)
        layout.addLayout(pagination)

    def apply_state(self, state: BoxesUiState) -> None:
        """Обновляет таблицу и элементы управления из состояния контроллера."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._page_label.setText(state.page_title)
        self._set_busy(state.is_busy)
        self._previous_button.setEnabled(not state.is_busy and state.has_previous)
        self._next_button.setEnabled(not state.is_busy and state.has_more)
        self._table.setRowCount(len(state.rows))
        for row_index, row in enumerate(state.rows):
            values = [
                str(row.box_id),
                row.order_name,
                row.sscc,
                row.filled,
                row.status,
                row.operator,
                row.print_status,
            ]
            for column_index, value in enumerate(values):
                self._table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _set_busy(self, is_busy: bool) -> None:
        """Включает или отключает элементы управления на время загрузки."""

        self._status_filter.setEnabled(not is_busy)
        self._search_input.setEnabled(not is_busy)
        self._search_button.setEnabled(not is_busy)
        self._refresh_button.setEnabled(not is_busy)

    def _emit_search(self) -> None:
        """Публикует поисковую строку из поля ввода."""

        self.search_requested.emit(self._search_input.text())

    def _emit_status_filter(self, _index: int) -> None:
        """Публикует выбранный фильтр статуса коробок."""

        self.status_filter_changed.emit(str(self._status_filter.currentData()))
