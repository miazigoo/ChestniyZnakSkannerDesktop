"""Экран списка коробок."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditUiState
from chestniy_znak_desktop.controllers.boxes_controller import BoxesUiState
from chestniy_znak_desktop.ui.widgets.box_detail_panel import BoxDetailPanel
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


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
        """Создает рабочий экран списка и деталей коробок."""

        super().__init__()
        self.setObjectName("boxesScreen")
        self._detail_loaded = False
        self._title = QLabel("Коробки")
        self._status_label = QLabel("Загрузите список коробок")
        self._error_label = QLabel("")
        self._search_input = QLineEdit()
        self._status_filter = self._create_status_filter()
        self._search_button = QPushButton("Найти")
        self._refresh_button = QPushButton("Обновить")
        self._previous_button = QPushButton("Назад")
        self._next_button = QPushButton("Дальше")
        self._page_label = QLabel("0 / 0")
        self._detail_button = QPushButton("Открыть детали")
        self._print_label_button = QPushButton("Печать этикетки")
        self._edit_open_button = QPushButton("Открыть редактирование")
        self._edit_close_button = QPushButton("Закрыть редактирование")
        self._remove_item_button = QPushButton("Удалить код")
        self._clear_box_button = QPushButton("Очистить коробку")
        self._delete_empty_button = QPushButton("Удалить пустую")
        self._table = self._create_boxes_table()
        self._detail_panel = BoxDetailPanel()
        self._detail_items_table = self._create_detail_items_table()

        self._configure_controls()
        self._build_layout()
        self._set_edit_buttons_enabled(False)

    def apply_state(self, state: BoxesUiState) -> None:
        """Обновляет таблицу и элементы управления из состояния контроллера."""

        self._sync_filter_controls(state)
        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._error_label.setVisible(bool(state.error_message))
        self._page_label.setText(state.page_title)
        self._set_busy(state.is_busy)
        self._previous_button.setEnabled(not state.is_busy and state.has_previous)
        self._next_button.setEnabled(not state.is_busy and state.has_more)
        self._detail_button.setEnabled(not state.is_detail_busy and bool(state.rows))
        self._print_label_button.setEnabled(not state.is_action_busy and state.detail is not None)
        self._set_edit_buttons_enabled(state.detail is not None)
        self._fill_boxes_table(state)
        self._select_state_row(state)
        self._apply_detail(state)

    def apply_edit_state(self, state: BoxEditUiState) -> None:
        """Обновляет статус действий редактирования коробки."""

        self._detail_panel.set_edit_status(state.status_message, state.error_message)
        self._set_edit_buttons_enabled(not state.is_busy and self._detail_loaded)

    def _create_status_filter(self) -> QComboBox:
        """Создает фильтр статуса коробок."""

        status_filter = QComboBox()
        status_filter.addItem("Все", "all")
        status_filter.addItem("Активные", "active")
        status_filter.addItem("Открытые", "open")
        status_filter.addItem("На редактировании", "edit")
        status_filter.addItem("Закрытые", "closed")
        status_filter.addItem("Пустые", "empty")
        return status_filter

    def _configure_controls(self) -> None:
        """Настраивает сигналы и objectName для элементов управления."""

        self._title.setObjectName("boxesHeroTitle")
        self._status_label.setObjectName("boxesStatusText")
        self._error_label.setObjectName("boxesErrorText")
        self._page_label.setObjectName("boxesPageLabel")
        self._status_filter.setObjectName("boxesCombo")
        self._search_input.setObjectName("boxesSearchInput")
        self._search_input.setPlaceholderText("Поиск по SSCC, заказу или ID")
        self._search_input.returnPressed.connect(self._emit_search)
        self._status_filter.currentIndexChanged.connect(self._emit_status_filter)
        self._search_button.setObjectName("boxesPrimaryButton")
        self._refresh_button.setObjectName("boxesSecondaryButton")
        self._previous_button.setObjectName("boxesSecondaryButton")
        self._next_button.setObjectName("boxesSecondaryButton")
        self._detail_button.setObjectName("boxesPrimaryButton")
        self._print_label_button.setObjectName("boxesPrimaryButton")
        self._edit_open_button.setObjectName("boxesSecondaryButton")
        self._edit_close_button.setObjectName("boxesSecondaryButton")
        self._remove_item_button.setObjectName("boxesDangerButton")
        self._clear_box_button.setObjectName("boxesDangerButton")
        self._delete_empty_button.setObjectName("boxesDangerButton")
        self._search_button.clicked.connect(self._emit_search)
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._previous_button.clicked.connect(self.previous_page_requested.emit)
        self._next_button.clicked.connect(self.next_page_requested.emit)
        self._detail_button.clicked.connect(self._emit_selected_box_detail)
        self._print_label_button.clicked.connect(self._emit_print_label)
        self._edit_open_button.clicked.connect(self._emit_edit_open)
        self._edit_close_button.clicked.connect(self._emit_edit_close)
        self._remove_item_button.clicked.connect(self._emit_remove_item)
        self._clear_box_button.clicked.connect(self._emit_clear_box)
        self._delete_empty_button.clicked.connect(self._emit_delete_empty)

    def _build_layout(self) -> None:
        """Собирает современную раскладку экрана коробок."""

        hero = self._create_hero()
        filters = self._create_filters_panel()
        list_panel = self._create_list_panel()
        detail_column = self._create_detail_column()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("boxesSplitter")
        splitter.addWidget(list_panel)
        splitter.addWidget(detail_column)
        splitter.setSizes([820, 520])
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(hero)
        layout.addWidget(filters)
        layout.addWidget(splitter, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний блок раздела коробок."""

        hero = QFrame()
        hero.setObjectName("boxesHero")
        icon = VectorIcon(VectorIconName.BOX, "#66d2c7")
        subtitle = QLabel(
            "Контроль открытых и закрытых коробок, повторная печать и edit-mode операции."
        )
        subtitle.setObjectName("boxesHeroSubtitle")
        subtitle.setWordWrap(True)
        text = QVBoxLayout()
        text.addWidget(self._title)
        text.addWidget(subtitle)
        status_block = QVBoxLayout()
        status_block.addWidget(self._status_label)
        status_block.addWidget(self._error_label)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(icon)
        layout.addLayout(text, 1)
        layout.addLayout(status_block, 1)
        return hero

    def _create_filters_panel(self) -> QFrame:
        """Создает панель фильтров и поиска списка коробок."""

        panel = QFrame()
        panel.setObjectName("boxesToolbar")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)
        layout.addWidget(self._status_filter)
        layout.addWidget(self._search_input, 1)
        layout.addWidget(self._search_button)
        layout.addWidget(self._refresh_button)
        return panel

    def _create_list_panel(self) -> QFrame:
        """Создает левую панель со списком коробок."""

        panel = QFrame()
        panel.setObjectName("boxesListPanel")
        header = QHBoxLayout()
        title = QLabel("Список коробок")
        title.setObjectName("boxesPanelTitle")
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self._previous_button)
        header.addWidget(self._page_label)
        header.addWidget(self._next_button)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self._detail_button)
        actions.addWidget(self._print_label_button)
        actions.addStretch(1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._table, 1)
        layout.addLayout(actions)
        return panel

    def _create_detail_column(self) -> QFrame:
        """Создает правую колонку деталей и edit-mode действий."""

        panel = QFrame()
        panel.setObjectName("boxesSideColumn")
        actions_panel = self._create_edit_actions_panel()
        items_panel = self._create_detail_items_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._detail_panel)
        layout.addWidget(actions_panel)
        layout.addWidget(items_panel, 1)
        return panel

    def _create_edit_actions_panel(self) -> QFrame:
        """Создает панель операций редактирования коробки."""

        panel = QFrame()
        panel.setObjectName("boxesActionsPanel")
        title = QLabel("Операции")
        title.setObjectName("boxesPanelTitle")
        hint = QLabel("Опасные действия требуют подтверждения")
        hint.setObjectName("boxesMutedText")
        hint.setWordWrap(True)

        actions_grid = QGridLayout()
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(10)
        actions_grid.addWidget(self._edit_open_button, 0, 0)
        actions_grid.addWidget(self._edit_close_button, 0, 1)
        actions_grid.addWidget(self._remove_item_button, 1, 0)
        actions_grid.addWidget(self._clear_box_button, 1, 1)
        actions_grid.addWidget(self._delete_empty_button, 2, 0, 1, 2)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(actions_grid)
        return panel

    def _create_detail_items_panel(self) -> QFrame:
        """Создает панель состава выбранной коробки."""

        panel = QFrame()
        panel.setObjectName("boxesItemsPanel")
        title = QLabel("Состав коробки")
        title.setObjectName("boxesPanelTitle")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(self._detail_items_table, 1)
        return panel

    def _create_boxes_table(self) -> QTableWidget:
        """Создает таблицу списка коробок."""

        table = QTableWidget(0, 7)
        table.setObjectName("boxesTable")
        table.setHorizontalHeaderLabels(
            ["ID", "Заказ", "SSCC", "Заполнено", "Статус", "Оператор", "Печать"]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        table.setColumnWidth(0, 72)
        table.cellDoubleClicked.connect(self._emit_row_detail)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return table

    def _create_detail_items_table(self) -> QTableWidget:
        """Создает таблицу состава выбранной коробки."""

        table = QTableWidget(0, 4)
        table.setObjectName("boxesItemsTable")
        table.setHorizontalHeaderLabels(["ID", "GTIN", "Serial", "Код"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 58)
        return table

    def _sync_filter_controls(self, state: BoxesUiState) -> None:
        """Синхронизирует фильтры с состоянием контроллера."""

        self._search_input.blockSignals(True)
        self._search_input.setText(state.query)
        self._search_input.blockSignals(False)
        index = self._status_filter.findData(state.status_filter)
        if index >= 0 and index != self._status_filter.currentIndex():
            self._status_filter.blockSignals(True)
            self._status_filter.setCurrentIndex(index)
            self._status_filter.blockSignals(False)

    def _fill_boxes_table(self, state: BoxesUiState) -> None:
        """Заполняет таблицу коробок строками из состояния."""

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
                cell = QTableWidgetItem(value)
                if column_index == 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row_index, column_index, cell)

    def _select_state_row(self, state: BoxesUiState) -> None:
        """Выбирает строку текущей детальной коробки или первую строку."""

        if not state.rows:
            return
        selected_row = 0
        if state.selected_box_id is not None:
            for row_index, row in enumerate(state.rows):
                if row.box_id == state.selected_box_id:
                    selected_row = row_index
                    break
        if self._table.currentRow() < 0 or state.selected_box_id is not None:
            self._table.setCurrentCell(selected_row, 0)

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

        self._detail_panel.set_status(
            state.detail_status_message,
            state.detail_error_message,
        )
        if state.detail is None:
            self._detail_loaded = False
            self._detail_panel.set_empty()
            self._detail_items_table.setRowCount(0)
            return
        self._detail_loaded = True
        detail = state.detail
        self._detail_panel.set_detail(detail)
        self._detail_items_table.setRowCount(len(detail.items))
        for row_index, item in enumerate(detail.items):
            values = [str(item.id), item.gtin, item.serial, item.visible_code]
            for column_index, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column_index == 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._detail_items_table.setItem(row_index, column_index, cell)

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
