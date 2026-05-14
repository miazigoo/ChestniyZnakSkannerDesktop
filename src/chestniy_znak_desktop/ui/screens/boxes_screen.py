"""Экран списка коробок."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditUiState
from chestniy_znak_desktop.controllers.boxes_controller import BoxesUiState


class BoxesScreen(QWidget):
    """Показывает список коробок и поиск по ним."""

    refresh_requested = Signal()
    search_requested = Signal(str)
    status_filter_changed = Signal(str)
    next_page_requested = Signal()
    previous_page_requested = Signal()
    box_detail_requested = Signal(int)
    print_label_requested = Signal(int)
    edit_open_requested = Signal(int)
    edit_close_requested = Signal(int)
    remove_item_requested = Signal(int, int)
    clear_box_requested = Signal(int)
    delete_empty_box_requested = Signal(int)

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
        self._status_filter.addItem("Активные", "active")
        self._status_filter.addItem("Открытые", "open")
        self._status_filter.addItem("На редактировании", "edit")
        self._status_filter.addItem("Закрытые", "closed")
        self._status_filter.addItem("Пустые", "empty")
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
        self._detail_button = QPushButton("Открыть детали")
        self._detail_button.clicked.connect(self._emit_selected_box_detail)
        self._print_label_button = QPushButton("Печать этикетки")
        self._print_label_button.clicked.connect(self._emit_print_label)
        self._edit_open_button = QPushButton("Открыть редактирование")
        self._edit_open_button.clicked.connect(self._emit_edit_open)
        self._edit_close_button = QPushButton("Закрыть редактирование")
        self._edit_close_button.clicked.connect(self._emit_edit_close)
        self._remove_item_button = QPushButton("Удалить код")
        self._remove_item_button.clicked.connect(self._emit_remove_item)
        self._clear_box_button = QPushButton("Очистить коробку")
        self._clear_box_button.clicked.connect(self._emit_clear_box)
        self._delete_empty_button = QPushButton("Удалить пустую")
        self._delete_empty_button.clicked.connect(self._emit_delete_empty)
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Заказ", "SSCC", "Заполнено", "Статус", "Оператор", "Печать"]
        )
        self._table.cellDoubleClicked.connect(self._emit_row_detail)
        self._detail_title = QLabel("Детали коробки")
        self._detail_status = QLabel("Выберите коробку для просмотра состава")
        self._detail_error = QLabel("")
        self._edit_status = QLabel("Редактирование не запущено")
        self._edit_error = QLabel("")
        self._detail_loaded = False
        self._detail_summary = QLabel("Коробка: -")
        self._detail_items_table = QTableWidget(0, 4)
        self._detail_items_table.setHorizontalHeaderLabels(["ID", "GTIN", "Serial", "Код"])

        filters = QHBoxLayout()
        filters.addWidget(self._status_filter)
        filters.addWidget(self._search_input, stretch=1)
        filters.addWidget(self._search_button)
        filters.addWidget(self._refresh_button)

        pagination = QHBoxLayout()
        pagination.addWidget(self._previous_button)
        pagination.addWidget(self._page_label)
        pagination.addWidget(self._next_button)
        pagination.addWidget(self._detail_button)
        pagination.addWidget(self._print_label_button)
        pagination.addStretch(1)

        edit_actions = QHBoxLayout()
        edit_actions.addWidget(self._edit_open_button)
        edit_actions.addWidget(self._edit_close_button)
        edit_actions.addWidget(self._remove_item_button)
        edit_actions.addWidget(self._clear_box_button)
        edit_actions.addWidget(self._delete_empty_button)
        edit_actions.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status_label)
        layout.addWidget(self._error_label)
        layout.addLayout(filters)
        layout.addWidget(self._table)
        layout.addLayout(pagination)
        layout.addWidget(self._detail_title)
        layout.addWidget(self._detail_status)
        layout.addWidget(self._detail_error)
        layout.addWidget(self._edit_status)
        layout.addWidget(self._edit_error)
        layout.addWidget(self._detail_summary)
        layout.addLayout(edit_actions)
        layout.addWidget(self._detail_items_table)

    def apply_state(self, state: BoxesUiState) -> None:
        """Обновляет таблицу и элементы управления из состояния контроллера."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._page_label.setText(state.page_title)
        self._set_busy(state.is_busy)
        self._previous_button.setEnabled(not state.is_busy and state.has_previous)
        self._next_button.setEnabled(not state.is_busy and state.has_more)
        self._detail_button.setEnabled(not state.is_detail_busy and bool(state.rows))
        self._print_label_button.setEnabled(not state.is_action_busy and state.detail is not None)
        self._set_edit_buttons_enabled(state.detail is not None)
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
        if state.rows and self._table.currentRow() < 0:
            self._table.setCurrentCell(0, 0)
        self._apply_detail(state)

    def apply_edit_state(self, state: BoxEditUiState) -> None:
        """Обновляет статус действий редактирования коробки."""

        self._edit_status.setText(state.status_message)
        self._edit_error.setText(state.error_message)
        self._set_edit_buttons_enabled(not state.is_busy and self._detail_loaded)

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

    def _emit_selected_box_detail(self) -> None:
        """Публикует запрос деталей для выбранной строки таблицы."""

        row = self._table.currentRow()
        if row < 0:
            return
        self._emit_row_detail(row, 0)

    def _emit_row_detail(self, row: int, _column: int) -> None:
        """Публикует запрос деталей для строки таблицы."""

        item = self._table.item(row, 0)
        if item is None:
            return
        self.box_detail_requested.emit(int(item.text()))

    def _emit_print_label(self) -> None:
        """Публикует запрос повторной печати этикетки выбранной коробки."""

        box_id = self._selected_box_id()
        if box_id is not None:
            self.print_label_requested.emit(box_id)

    def _emit_edit_open(self) -> None:
        """Публикует запрос открытия режима редактирования."""

        box_id = self._selected_box_id()
        if box_id is not None:
            self.edit_open_requested.emit(box_id)

    def _emit_edit_close(self) -> None:
        """Публикует запрос закрытия режима редактирования."""

        box_id = self._selected_box_id()
        if box_id is not None:
            self.edit_close_requested.emit(box_id)

    def _emit_remove_item(self) -> None:
        """Публикует запрос удаления выбранного кода из коробки."""

        box_id = self._selected_box_id()
        item_id = self._selected_item_id()
        if (
            box_id is not None
            and item_id is not None
            and self._confirm(
                title="Удалить код",
                text=f"Удалить код #{item_id} из коробки #{box_id}?",
            )
        ):
            self.remove_item_requested.emit(box_id, item_id)

    def _emit_clear_box(self) -> None:
        """Публикует запрос очистки выбранной коробки."""

        box_id = self._selected_box_id()
        if box_id is not None and self._confirm(
            title="Очистить коробку",
            text=f"Удалить все коды из коробки #{box_id}?",
        ):
            self.clear_box_requested.emit(box_id)

    def _emit_delete_empty(self) -> None:
        """Публикует запрос удаления пустой коробки."""

        box_id = self._selected_box_id()
        if box_id is not None and self._confirm(
            title="Удалить пустую коробку",
            text=f"Удалить пустую коробку #{box_id}?",
        ):
            self.delete_empty_box_requested.emit(box_id)

    def _apply_detail(self, state: BoxesUiState) -> None:
        """Обновляет панель деталей выбранной коробки."""

        self._detail_status.setText(state.detail_status_message)
        self._detail_error.setText(state.detail_error_message)
        if state.detail is None:
            self._detail_loaded = False
            self._detail_summary.setText("Коробка: -")
            self._detail_items_table.setRowCount(0)
            return
        self._detail_loaded = True
        detail = state.detail
        self._detail_summary.setText(
            (
                f"Коробка #{detail.box_id} | Заказ: {detail.order_name} | "
                f"SSCC: {detail.sscc} | {detail.filled}/{detail.capacity} | "
                f"{detail.status} | Учитывать: {detail.count_in_packing} | "
                f"Оператор: {detail.operator} | Печать: {detail.print_status}"
            )
        )
        self._detail_items_table.setRowCount(len(detail.items))
        for row_index, item in enumerate(detail.items):
            values = [str(item.id), item.gtin, item.serial, item.visible_code]
            for column_index, value in enumerate(values):
                self._detail_items_table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(value),
                )

    def _selected_box_id(self) -> int | None:
        """Возвращает ID выбранной коробки из таблицы."""

        row = self._table.currentRow()
        item = self._table.item(row, 0) if row >= 0 else None
        return int(item.text()) if item is not None else None

    def _selected_item_id(self) -> int | None:
        """Возвращает ID выбранного кода из таблицы деталей."""

        row = self._detail_items_table.currentRow()
        item = self._detail_items_table.item(row, 0) if row >= 0 else None
        return int(item.text()) if item is not None else None

    def _set_edit_buttons_enabled(self, enabled: bool) -> None:
        """Включает или отключает кнопки редактирования."""

        self._edit_open_button.setEnabled(enabled)
        self._edit_close_button.setEnabled(enabled)
        self._remove_item_button.setEnabled(enabled)
        self._clear_box_button.setEnabled(enabled)
        self._delete_empty_button.setEnabled(enabled)

    def _confirm(self, title: str, text: str) -> bool:
        """Запрашивает подтверждение опасного действия."""

        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes
