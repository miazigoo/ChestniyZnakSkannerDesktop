"""Основной экран упаковки кодов в коробку."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.packing_controller import PackingUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.code_format import format_marking_code_for_display
from chestniy_znak_desktop.ui.widgets.packing_cards import (
    PackingScanCard,
    PackingSummaryCard,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class PackingScreen(QWidget):
    """Рабочий экран оператора упаковки."""

    refresh_requested = Signal()
    open_box_requested = Signal()
    close_box_requested = Signal()
    clear_box_requested = Signal()
    choose_order_requested = Signal()
    count_in_packing_changed = Signal(bool)
    order_search_changed = Signal(str)
    order_line_selected = Signal(str)

    def __init__(self) -> None:
        """Создает современную раскладку экрана упаковки."""

        super().__init__()
        self.setObjectName("packingScreen")
        self._is_busy = False
        self._scanner_ready = False
        self._has_box = False
        self._box_items_count = 0
        self._has_order_selection = False
        self._selected_order_scan_required = True
        self._summary_card = PackingSummaryCard(show_actions=True)
        self._scan_card = PackingScanCard()
        self._progress_bar = self._summary_card.progress_bar
        self._order_search = QLineEdit()
        self._order_combo = QComboBox()
        self._order_line_ids: list[str] = []
        self._count_in_packing = QCheckBox(tr("packing.countInPacking"))
        self._refresh_button = QPushButton(tr("packing.refresh"))
        self._open_box_button = QPushButton(tr("packing.openBox"))
        self._close_box_button = QPushButton(tr("packing.closeBox"))
        self._items_table = self._create_items_table()

        self._configure_actions()
        self._build_layout()
        self._set_busy(False)

    def apply_state(self, state: PackingUiState) -> None:
        """Обновляет экран из состояния контроллера упаковки."""

        self._count_in_packing.blockSignals(True)
        self._count_in_packing.setChecked(state.count_in_packing)
        self._count_in_packing.blockSignals(False)
        self._apply_order_options(state)
        self._selected_order_scan_required = state.selected_order_scan_required
        self._scan_card.set_messages(
            status=state.status_message,
            result=state.result_message,
            error=state.error_message,
            last_code=state.last_scanned_code,
        )
        self._has_box = state.current_box is not None
        if state.current_box is None:
            self._box_items_count = 0
            self._summary_card.set_empty()
            self._items_table.setRowCount(0)
        else:
            box = state.current_box
            self._box_items_count = len(box.items)
            self._summary_card.set_box(
                box_id=box.box_id,
                order_name=box.order_name,
                sscc=box.sscc,
                filled=box.filled,
                capacity=box.capacity,
                count_in_packing=box.count_in_packing,
                is_closed=box.is_closed,
            )
            self._fill_items_table(state)
        self._set_busy(state.is_busy)

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет защиту рабочих действий по состоянию сканера."""

        self._scanner_ready = snapshot.scanner.is_running
        self._scan_card.set_runtime(
            scanner_ready=self._scanner_ready,
            port=snapshot.scanner.port,
        )
        self._set_busy(self._is_busy)

    def _configure_actions(self) -> None:
        """Настраивает кнопки и рабочие сигналы экрана."""

        self._refresh_button.setObjectName("packingSecondaryButton")
        self._open_box_button.setObjectName("packingPrimaryButton")
        self._close_box_button.setObjectName("packingDangerButton")
        self._order_search.setObjectName("settingsInput")
        self._order_search.setPlaceholderText(tr("packing.searchPlaceholder"))
        self._order_combo.setObjectName("settingsInput")
        self._order_combo.setMinimumWidth(280)
        self._count_in_packing.setObjectName("packingCheckBox")
        self._count_in_packing.setChecked(True)
        self._order_search.textChanged.connect(self.order_search_changed.emit)
        self._order_combo.currentIndexChanged.connect(self._emit_order_line_selected)
        self._count_in_packing.toggled.connect(self.count_in_packing_changed.emit)
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._open_box_button.clicked.connect(self.open_box_requested.emit)
        self._close_box_button.clicked.connect(self.close_box_requested.emit)
        self._summary_card.clear_box_requested.connect(self.clear_box_requested.emit)
        self._summary_card.choose_order_requested.connect(self._focus_order_selector)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру рабочего экрана."""

        hero = self._create_hero()
        actions = self._create_actions_panel()
        top_grid = QGridLayout()
        top_grid.setSpacing(18)
        top_grid.addWidget(hero, 0, 0, 1, 2)
        top_grid.addWidget(actions, 0, 2)
        top_grid.addWidget(self._summary_card, 1, 0, 1, 2)
        top_grid.addWidget(self._scan_card, 1, 2)
        top_grid.setColumnStretch(0, 2)
        top_grid.setColumnStretch(1, 2)
        top_grid.setColumnStretch(2, 3)

        table_panel = self._create_table_panel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addLayout(top_grid)
        layout.addWidget(table_panel, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний информационный блок сценария упаковки."""

        hero = QFrame()
        hero.setObjectName("packingHero")
        icon = VectorIcon(VectorIconName.BOX, "#66d2c7")
        title = QLabel(tr("packing.heroTitle"))
        title.setObjectName("packingHeroTitle")
        subtitle = QLabel(tr("packing.heroSubtitle"))
        subtitle.setObjectName("packingHeroSubtitle")
        subtitle.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(icon)
        layout.addLayout(text_layout, 1)
        return hero

    def _create_actions_panel(self) -> QFrame:
        """Создает панель основных действий оператора."""

        panel = QFrame()
        panel.setObjectName("packingActionsPanel")
        title = QLabel(tr("packing.actions"))
        title.setObjectName("packingCardTitle")
        hint = QLabel(tr("packing.actionsHint"))
        hint.setObjectName("packingMutedText")
        hint.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addWidget(self._refresh_button)
        buttons.addWidget(self._open_box_button)
        buttons.addWidget(self._close_box_button)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(QLabel(tr("packing.orderAndProduct")))
        layout.addWidget(self._order_search)
        layout.addWidget(self._order_combo)
        layout.addLayout(buttons)
        layout.addWidget(self._count_in_packing)
        return panel

    def _apply_order_options(self, state: PackingUiState) -> None:
        """Обновляет список выбора заказа и номенклатуры."""

        self._has_order_selection = bool(state.selected_order_line_id)
        self._order_search.blockSignals(True)
        if self._order_search.text() != state.order_search:
            self._order_search.setText(state.order_search)
        self._order_search.blockSignals(False)

        self._order_combo.blockSignals(True)
        self._order_combo.clear()
        self._order_line_ids = [option.order_line_id for option in state.order_options]
        if state.orders_loading:
            self._order_combo.addItem(tr("packing.ordersLoading"))
        elif not state.order_options:
            self._order_combo.addItem(tr("packing.ordersEmpty"))
        else:
            for option in state.order_options:
                self._order_combo.addItem(option.label)
            selected_index = (
                self._order_line_ids.index(state.selected_order_line_id)
                if state.selected_order_line_id in self._order_line_ids
                else 0
            )
            self._order_combo.setCurrentIndex(selected_index)
        self._order_combo.blockSignals(False)

    def _emit_order_line_selected(self, index: int) -> None:
        """Публикует выбранный идентификатор строки заказа."""

        if index < 0 or index >= len(self._order_line_ids):
            return
        self.order_line_selected.emit(self._order_line_ids[index])

    def _create_table_panel(self) -> QFrame:
        """Создает панель списка отсканированных изделий."""

        panel = QFrame()
        panel.setObjectName("packingTablePanel")
        header = QHBoxLayout()
        title = QLabel(tr("packing.tableTitle"))
        title.setObjectName("packingCardTitle")
        hint = QLabel(tr("packing.tableHint"))
        hint.setObjectName("packingMutedText")
        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(hint)
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header.addLayout(header_text, 1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._items_table, 1)
        return panel

    def _create_items_table(self) -> QTableWidget:
        """Создает таблицу кодов текущей коробки."""

        table = QTableWidget(0, 4)
        table.setObjectName("packingItemsTable")
        table.setHorizontalHeaderLabels(["#", "GTIN", "Serial", tr("packing.column.code")])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 54)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return table

    def _fill_items_table(self, state: PackingUiState) -> None:
        """Заполняет таблицу изделиями из текущей коробки."""

        if state.current_box is None:
            return
        self._items_table.setRowCount(len(state.current_box.items))
        for row, item in enumerate(state.current_box.items):
            values = [
                str(row + 1),
                item.gtin,
                item.serial,
                format_marking_code_for_display(item.visible_code, empty=""),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 3 and value:
                    cell.setToolTip(value)
                if column == 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._items_table.setItem(row, column, cell)

    def _set_busy(self, is_busy: bool) -> None:
        """Включает или отключает рабочие кнопки на время операции."""

        self._is_busy = is_busy
        is_ready = not is_busy and self._scanner_ready
        can_open_selected_order = self._has_order_selection and self._selected_order_scan_required
        self._refresh_button.setEnabled(not is_busy)
        self._open_box_button.setEnabled(is_ready and (self._has_box or can_open_selected_order))
        self._close_box_button.setEnabled(is_ready and self._has_box)
        self._order_search.setEnabled(not is_busy and not self._has_box)
        self._order_combo.setEnabled(
            not is_busy and not self._has_box and self._has_order_selection
        )
        self._count_in_packing.setEnabled(not is_busy)
        self._summary_card.set_action_state(
            can_choose_order=not is_busy and not self._has_box,
            can_clear_box=not is_busy and self._has_box and self._box_items_count > 0,
        )

    def _focus_order_selector(self) -> None:
        """Переводит оператора к выбору заказа для следующей коробки."""

        self.choose_order_requested.emit()
        self._order_search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._order_search.selectAll()
