"""Карточки состояния для рабочего экрана упаковки."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.ui.code_format import format_marking_code_for_display
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class PackingSummaryCard(QFrame):
    """Показывает текущую коробку, прогресс и ключевые параметры."""

    choose_order_requested = Signal()
    clear_box_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        show_actions: bool = False,
    ) -> None:
        """Создает карточку текущей коробки."""

        super().__init__(parent)
        self.setObjectName("packingCard")
        self._box_title = QLabel(tr("packing.summary.emptyTitle"))
        self._box_title.setObjectName("packingCardTitle")
        self._box_subtitle = QLabel(tr("packing.summary.emptySubtitle"))
        self._box_subtitle.setObjectName("packingMutedText")
        self._status_badge = QLabel(tr("packing.summary.idle"))
        self._status_badge.setObjectName("packingBadge")
        self._progress_label = QLabel("0 / 0")
        self._progress_label.setObjectName("packingProgressValue")
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("packingProgressBar")
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._order_value = QLabel("-")
        self._sscc_value = QLabel("-")
        self._mode_value = QLabel("-")
        self._choose_order_button = QPushButton(tr("packing.summary.chooseOrder"))
        self._choose_order_button.setObjectName("packingSecondaryButton")
        self._choose_order_button.setToolTip(tr("packing.summary.chooseOrderHint"))
        self._clear_box_button = QPushButton(tr("packing.summary.clearBox"))
        self._clear_box_button.setObjectName("packingDangerButton")
        self._clear_box_button.setToolTip(tr("packing.summary.clearBoxHint"))
        self._actions = QFrame()
        self._actions.setObjectName("packingSummaryActions")
        self._actions.setVisible(show_actions)
        self._choose_order_button.clicked.connect(self.choose_order_requested.emit)
        self._clear_box_button.clicked.connect(self.clear_box_requested.emit)

        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.BOX, "#66d2c7"))
        title_block = QVBoxLayout()
        title_block.addWidget(self._box_title)
        title_block.addWidget(self._box_subtitle)
        header.addLayout(title_block, 1)
        header.addWidget(self._status_badge)

        progress_row = QHBoxLayout()
        progress_caption = QLabel(tr("packing.progress"))
        progress_caption.setObjectName("packingMutedText")
        progress_row.addWidget(progress_caption)
        progress_row.addStretch(1)
        progress_row.addWidget(self._progress_label)

        meta_grid = QGridLayout()
        meta_grid.setHorizontalSpacing(18)
        meta_grid.setVerticalSpacing(6)
        self._add_meta_row(meta_grid, 0, tr("packing.column.order"), self._order_value)
        self._add_meta_row(meta_grid, 1, "SSCC", self._sscc_value)
        self._add_meta_row(meta_grid, 2, tr("packing.mode"), self._mode_value)

        actions_layout = QHBoxLayout(self._actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self._choose_order_button)
        actions_layout.addWidget(self._clear_box_button)
        actions_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addLayout(progress_row)
        layout.addWidget(self._progress_bar)
        layout.addLayout(meta_grid)
        layout.addStretch(1)
        layout.addWidget(self._actions)

    @property
    def progress_bar(self) -> QProgressBar:
        """Возвращает прогресс-бар для тестов и внешней синхронизации."""

        return self._progress_bar

    def set_action_state(
        self,
        *,
        can_choose_order: bool,
        can_clear_box: bool,
    ) -> None:
        """Обновляет доступность действий карточки."""

        self._choose_order_button.setEnabled(can_choose_order)
        self._clear_box_button.setEnabled(can_clear_box)

    def set_empty(self) -> None:
        """Переводит карточку в состояние без открытой коробки."""

        self._box_title.setText(tr("packing.summary.emptyTitle"))
        self._box_subtitle.setText(tr("packing.summary.emptySubtitle"))
        self._status_badge.setText(tr("packing.summary.idle"))
        self._status_badge.setProperty("tone", "idle")
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)
        self._progress_label.setText("0 / 0")
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._order_value.setText("-")
        self._sscc_value.setText("-")
        self._mode_value.setText("-")

    def set_box(
        self,
        *,
        box_id: int,
        order_name: str,
        sscc: str,
        filled: int,
        capacity: int,
        count_in_packing: bool,
        is_closed: bool,
    ) -> None:
        """Показывает параметры открытой коробки."""

        has_capacity = capacity > 0
        progress_max = capacity if has_capacity else 1
        progress_value = min(max(filled, 0), progress_max) if has_capacity else 0
        self._box_title.setText(tr("packing.summary.boxTitle", box_id=box_id))
        self._box_subtitle.setText(tr("packing.summary.ready"))
        self._status_badge.setText(
            tr("packing.summary.closed") if is_closed else tr("packing.summary.open")
        )
        self._status_badge.setProperty("tone", "closed" if is_closed else "active")
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)
        capacity_text = str(capacity) if has_capacity else tr("packing.capacityUnknown")
        self._progress_label.setText(f"{filled} / {capacity_text}")
        self._progress_bar.setRange(0, progress_max)
        self._progress_bar.setValue(progress_value)
        self._order_value.setText(order_name or "-")
        self._sscc_value.setText(sscc or "-")
        mode = tr("packing.modeCounted") if count_in_packing else tr("packing.modeNotCounted")
        self._mode_value.setText(mode)

    @staticmethod
    def _add_meta_row(
        grid: QGridLayout,
        row: int,
        title: str,
        value: QLabel,
    ) -> None:
        """Добавляет строку метаданных коробки."""

        title_label = QLabel(title)
        title_label.setObjectName("packingMetaTitle")
        value.setObjectName("packingMetaValue")
        value.setWordWrap(True)
        grid.addWidget(title_label, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(value, row, 1)


class PackingScanCard(QFrame):
    """Показывает готовность сканера и результат последнего скана."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает карточку сканирования изделий."""

        super().__init__(parent)
        self.setObjectName("packingScanCard")
        self._scanner_label = QLabel(tr("packing.scannerChecking"))
        self._scanner_label.setObjectName("packingScannerStatus")
        self._status_label = QLabel(tr("packing.noOpenBox"))
        self._status_label.setObjectName("packingScanTitle")
        self._result_label = QLabel("")
        self._result_label.setObjectName("packingResult")
        self._error_label = QLabel("")
        self._error_label.setObjectName("packingError")
        self._last_code_label = QLabel(tr("packing.lastScan", code="-"))
        self._last_code_label.setObjectName("packingMutedText")
        self._last_code_label.setTextFormat(Qt.TextFormat.PlainText)
        self._last_code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._last_code_label.setWordWrap(True)

        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.SCANNER, "#8fb8ff"))
        header_text = QVBoxLayout()
        title = QLabel(tr("packing.scanTitle"))
        title.setObjectName("packingCardTitle")
        subtitle = QLabel(tr("packing.scanSubtitle"))
        subtitle.setObjectName("packingMutedText")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(self._scanner_label)
        layout.addWidget(self._status_label)
        layout.addWidget(self._result_label)
        layout.addWidget(self._error_label)
        layout.addStretch(1)
        layout.addWidget(self._last_code_label)

    def set_runtime(self, *, scanner_ready: bool, port: str) -> None:
        """Обновляет отображение готовности сканера."""

        if scanner_ready:
            self._scanner_label.setText(tr("packing.scannerReady", port=port or "-"))
            self._scanner_label.setProperty("tone", "active")
        else:
            self._scanner_label.setText(tr("packing.scannerBlocked"))
            self._scanner_label.setProperty("tone", "error")
        self._scanner_label.style().unpolish(self._scanner_label)
        self._scanner_label.style().polish(self._scanner_label)

    def set_messages(
        self,
        *,
        status: str,
        result: str,
        error: str,
        last_code: str,
    ) -> None:
        """Обновляет текстовые статусы последней операции."""

        self._status_label.setText(status)
        self._result_label.setText(result or tr("packing.waitScan"))
        self._error_label.setText(error)
        self._error_label.setVisible(bool(error))
        visible_code = self._visible_code(last_code)
        self._last_code_label.setText(tr("packing.lastScan", code=visible_code))
        self._last_code_label.setToolTip(visible_code if last_code else "")

    @staticmethod
    def _visible_code(code: str) -> str:
        """Возвращает полный код сканера с видимыми управляющими символами."""

        return format_marking_code_for_display(code)
