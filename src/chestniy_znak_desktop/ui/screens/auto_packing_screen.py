"""Экран упаковки через автосканер мультиплат."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.auto_packing_controller import (
    AutoPackingUiState,
)
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.packing_cards import PackingSummaryCard
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class AutoPackingScreen(QWidget):
    """Рабочий экран автосканера для мультиплат с несколькими кодами."""

    refresh_requested = Signal()
    open_box_requested = Signal()
    clear_pending_requested = Signal()
    remove_pending_requested = Signal(int)
    remove_box_item_requested = Signal(int)
    clear_box_requested = Signal()
    delete_box_requested = Signal()
    codes_per_item_changed = Signal(int)

    def __init__(self) -> None:
        """Создает экран автосканерной упаковки."""

        super().__init__()
        self.setObjectName("autoPackingScreen")
        self._is_busy = False
        self._scanner_ready = False
        self._has_box = False
        self._summary_card = PackingSummaryCard()
        self._capacity_spin = QSpinBox()
        self._refresh_button = QPushButton("Обновить")
        self._open_box_button = QPushButton("Открыть коробку")
        self._clear_button = QPushButton("Очистить бокс")
        self._remove_button = QPushButton("Удалить код")
        self._remove_box_item_button = QPushButton("Удалить код из коробки")
        self._clear_box_button = QPushButton("Очистить коробку")
        self._delete_box_button = QPushButton("Удалить пустую коробку")
        self._quick_buttons: list[QPushButton] = []
        self._status_title = QLabel("Автоскана-бокс пуст")
        self._status_title.setObjectName("autoPackingStatusTitle")
        self._status_detail = QLabel("Ожидаем коды от COM/SPP-сканера")
        self._status_detail.setObjectName("autoPackingStatusDetail")
        self._status_detail.setWordWrap(True)
        self._error_label = QLabel("")
        self._error_label.setObjectName("packingError")
        self._error_label.setWordWrap(True)
        self._scanner_status = QLabel("Сканер не запущен")
        self._scanner_status.setObjectName("packingScannerStatus")
        self._pending_table = self._create_pending_table()
        self._box_items_table = self._create_box_items_table()
        self._pending_tab_index = 0
        self._box_tab_index = 1
        self._tables_tabs = QTabWidget()
        self._box_filled = 0
        self._box_items_count = 0
        self._configure_actions()
        self._build_layout()
        self._set_busy(False)

    def apply_state(self, state: AutoPackingUiState) -> None:
        """Обновляет экран из состояния контроллера автосканера."""

        self._capacity_spin.blockSignals(True)
        self._capacity_spin.setValue(state.codes_per_item)
        self._capacity_spin.blockSignals(False)
        self._has_box = state.current_box is not None
        self._box_filled = state.current_box.filled if state.current_box is not None else 0
        self._box_items_count = len(state.current_box.items) if state.current_box is not None else 0
        if state.current_box is None:
            self._summary_card.set_empty()
        else:
            box = state.current_box
            self._summary_card.set_box(
                box_id=box.box_id,
                order_name=box.order_name,
                sscc=box.sscc,
                filled=box.filled,
                capacity=box.capacity,
                count_in_packing=box.count_in_packing,
                is_closed=box.is_closed,
            )
        self._fill_pending_table(state)
        self._fill_box_items_table(state)
        self._update_table_tabs(state)
        self._apply_pending_tone(state)
        self._status_detail.setText(
            state.error_message or state.result_message or state.status_message
        )
        self._error_label.setText(state.error_message)
        self._error_label.setVisible(bool(state.error_message))
        self._set_busy(state.is_busy)

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет защиту действий по состоянию сканера."""

        self._scanner_ready = snapshot.scanner.is_running
        self._scanner_status.setText(
            f"Сканер: {snapshot.scanner.port}" if self._scanner_ready else "Сканер не запущен"
        )
        self._scanner_status.setProperty(
            "tone",
            "ok" if self._scanner_ready else "error",
        )
        self._scanner_status.style().unpolish(self._scanner_status)
        self._scanner_status.style().polish(self._scanner_status)
        self._set_busy(self._is_busy)

    def _configure_actions(self) -> None:
        """Настраивает кнопки, таблицу и сигналы экрана."""

        self._capacity_spin.setObjectName("settingsInput")
        self._capacity_spin.setRange(1, 99)
        self._capacity_spin.valueChanged.connect(self.codes_per_item_changed.emit)
        self._refresh_button.setObjectName("packingSecondaryButton")
        self._open_box_button.setObjectName("packingPrimaryButton")
        self._clear_button.setText("Очистить локальный бокс")
        self._clear_button.setObjectName("packingDangerButton")
        self._remove_button.setObjectName("packingSecondaryButton")
        self._remove_box_item_button.setObjectName("packingDangerButton")
        self._clear_box_button.setObjectName("packingDangerButton")
        self._delete_box_button.setObjectName("packingDangerButton")
        self._refresh_button.clicked.connect(self.refresh_requested.emit)
        self._open_box_button.clicked.connect(self.open_box_requested.emit)
        self._clear_button.clicked.connect(self.clear_pending_requested.emit)
        self._remove_button.clicked.connect(self._emit_remove_selected)
        self._remove_box_item_button.clicked.connect(self._emit_remove_box_item_selected)
        self._clear_box_button.clicked.connect(self.clear_box_requested.emit)
        self._delete_box_button.clicked.connect(self.delete_box_requested.emit)
        for value in (1, 6, 12):
            button = QPushButton(str(value))
            button.setObjectName("packingSecondaryButton")
            button.clicked.connect(
                lambda _checked=False, value=value: self._capacity_spin.setValue(value)
            )
            self._quick_buttons.append(button)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру экрана."""

        hero = self._create_hero()
        controls = self._create_controls_panel()
        local_box = self._create_local_box_panel()
        top_grid = QGridLayout()
        top_grid.setSpacing(18)
        top_grid.addWidget(hero, 0, 0, 1, 2)
        top_grid.addWidget(controls, 0, 2)
        top_grid.addWidget(self._summary_card, 1, 0)
        top_grid.addWidget(local_box, 1, 1, 1, 2)
        top_grid.setColumnStretch(0, 2)
        top_grid.setColumnStretch(1, 2)
        top_grid.setColumnStretch(2, 2)

        table_panel = self._create_table_panel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addLayout(top_grid)
        layout.addWidget(table_panel, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний блок описания сценария автосканера."""

        hero = QFrame()
        hero.setObjectName("packingHero")
        title = QLabel("Автоупаковка мультиплат")
        title.setObjectName("packingHeroTitle")
        subtitle = QLabel(
            "Коды сначала копятся в локальном боксе изделия. "
            "В коробку они уходят только после заполнения бокса."
        )
        subtitle.setObjectName("packingHeroSubtitle")
        subtitle.setWordWrap(True)
        text = QVBoxLayout()
        text.setSpacing(4)
        text.addWidget(title)
        text.addWidget(subtitle)
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(VectorIcon(VectorIconName.SCANNER, "#66d2c7"))
        layout.addLayout(text, 1)
        return hero

    def _create_controls_panel(self) -> QFrame:
        """Создает панель действий и вместимости изделия."""

        panel = QFrame()
        panel.setObjectName("packingActionsPanel")
        title = QLabel("Настройка изделия")
        title.setObjectName("packingCardTitle")
        capacity_label = QLabel("DataMatrix на изделии")
        capacity_label.setObjectName("packingMutedText")
        quick = QHBoxLayout()
        quick.setSpacing(8)
        for button in self._quick_buttons:
            quick.addWidget(button)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self._refresh_button)
        actions.addWidget(self._open_box_button)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(capacity_label)
        layout.addWidget(self._capacity_spin)
        layout.addLayout(quick)
        layout.addLayout(actions)
        layout.addWidget(self._scanner_status)
        return panel

    def _create_local_box_panel(self) -> QFrame:
        """Создает красно-зеленую карточку локального автоскана-бокса."""

        panel = QFrame()
        panel.setObjectName("autoPackingBoxPanel")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        text = QVBoxLayout()
        text.addWidget(self._status_title)
        text.addWidget(self._status_detail)
        header.addLayout(text, 1)
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addWidget(self._remove_button)
        buttons.addWidget(self._clear_button)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._error_label)
        layout.addLayout(buttons)
        return panel

    def _create_table_panel(self) -> QFrame:
        """Создает панель кодов локального бокса."""

        panel = QFrame()
        panel.setObjectName("packingTablePanel")
        title = QLabel("Коды автоскана и текущей коробки")
        title.setObjectName("packingCardTitle")
        hint = QLabel(
            "В локальном боксе видны прочитанные коды изделия. "
            "После заполнения они появляются во вкладке текущей коробки."
        )
        hint.setObjectName("packingMutedText")
        hint.setWordWrap(True)
        self._tables_tabs.setObjectName("packingTablesTabs")
        self._tables_tabs.addTab(self._pending_table, "Локальный бокс")
        self._tables_tabs.addTab(self._box_items_table, "Текущая коробка")
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self._remove_box_item_button)
        actions.addWidget(self._clear_box_button)
        actions.addWidget(self._delete_box_button)
        header = QVBoxLayout()
        header.addWidget(title)
        header.addWidget(hint)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._tables_tabs, 1)
        layout.addLayout(actions)
        return panel

    def _create_pending_table(self) -> QTableWidget:
        """Создает таблицу локально накопленных кодов."""

        table = QTableWidget(0, 5)
        table.setObjectName("packingItemsTable")
        table.setHorizontalHeaderLabels(["#", "Заказ", "GTIN", "Serial", "Код"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 54)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return table

    def _create_box_items_table(self) -> QTableWidget:
        """Создает таблицу кодов, уже добавленных в текущую коробку."""

        table = QTableWidget(0, 4)
        table.setObjectName("packingItemsTable")
        table.setHorizontalHeaderLabels(["#", "GTIN", "Serial", "Код"])
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

    def _fill_pending_table(self, state: AutoPackingUiState) -> None:
        """Заполняет таблицу кодами локального бокса."""

        self._pending_table.setRowCount(len(state.pending_items))
        for row, item in enumerate(state.pending_items):
            values = [
                str(row + 1),
                item.order_key,
                item.gtin,
                item.serial,
                item.visible_code,
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._pending_table.setItem(row, column, cell)

    def _fill_box_items_table(self, state: AutoPackingUiState) -> None:
        """Заполняет таблицу кодов, уже добавленных в текущую коробку."""

        items = state.current_box.items if state.current_box is not None else []
        self._box_items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                str(row + 1),
                item.gtin,
                item.serial,
                item.visible_code,
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._box_items_table.setItem(row, column, cell)

    def _update_table_tabs(self, state: AutoPackingUiState) -> None:
        """Обновляет подписи вкладок таблиц и выбирает актуальную вкладку."""

        box_count = len(state.current_box.items) if state.current_box is not None else 0
        self._tables_tabs.setTabText(
            self._pending_tab_index,
            f"Локальный бокс ({state.pending_count}/{state.codes_per_item})",
        )
        self._tables_tabs.setTabText(self._box_tab_index, f"Текущая коробка ({box_count})")
        if state.pending_items:
            self._tables_tabs.setCurrentIndex(self._pending_tab_index)
        elif box_count:
            self._tables_tabs.setCurrentIndex(self._box_tab_index)

    def _apply_pending_tone(self, state: AutoPackingUiState) -> None:
        """Подкрашивает локальный бокс по заполненности."""

        tone = "full" if state.is_pending_full else "partial"
        self._status_title.setText(
            f"Бокс заполнен: {state.pending_count} / {state.codes_per_item}"
            if state.is_pending_full
            else f"Бокс не заполнен: {state.pending_count} / {state.codes_per_item}"
        )
        parent = self._status_title.parentWidget()
        while parent is not None and parent.objectName() != "autoPackingBoxPanel":
            parent = parent.parentWidget()
        if parent is not None:
            parent.setProperty("tone", tone)
            parent.style().unpolish(parent)
            parent.style().polish(parent)

    def _emit_remove_selected(self) -> None:
        """Публикует запрос удаления выбранной строки локального бокса."""

        row = self._pending_table.currentRow()
        self.remove_pending_requested.emit(row)

    def _emit_remove_box_item_selected(self) -> None:
        """Публикует запрос удаления выбранной строки из текущей коробки."""

        row = self._box_items_table.currentRow()
        self.remove_box_item_requested.emit(row)

    def _set_busy(self, is_busy: bool) -> None:
        """Включает или отключает рабочие действия."""

        self._is_busy = is_busy
        is_ready = not is_busy and self._scanner_ready
        self._refresh_button.setEnabled(not is_busy)
        self._open_box_button.setEnabled(is_ready)
        self._capacity_spin.setEnabled(not is_busy)
        for button in self._quick_buttons:
            button.setEnabled(not is_busy)
        self._clear_button.setEnabled(not is_busy)
        self._remove_button.setEnabled(not is_busy and self._pending_table.rowCount() > 0)
        self._remove_box_item_button.setEnabled(not is_busy and self._box_items_count > 0)
        self._clear_box_button.setEnabled(not is_busy and self._box_items_count > 0)
        self._delete_box_button.setEnabled(not is_busy and self._has_box and self._box_filled == 0)
