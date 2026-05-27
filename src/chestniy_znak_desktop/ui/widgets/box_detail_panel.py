"""Панель детальной информации по выбранной коробке."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.boxes_controller import BoxDetailUi
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class BoxDetailPanel(QFrame):
    """Показывает сводку выбранной коробки и статусы операций."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает панель детальной карточки коробки."""

        super().__init__(parent)
        self.setObjectName("boxesDetailPanel")
        self._title = QLabel(tr("boxes.detailTitle"))
        self._title.setObjectName("boxesPanelTitle")
        self._status = QLabel(tr("boxes.detailSelect"))
        self._status.setObjectName("boxesStatusText")
        self._error = QLabel("")
        self._error.setObjectName("boxesErrorText")
        self._summary = QLabel(tr("boxes.detailSummary", value="-"))
        self._summary.setObjectName("boxesDetailTitle")
        self._progress_label = QLabel("0 / 0")
        self._progress_label.setObjectName("boxesProgressValue")
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("boxesProgressBar")
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, 1)
        self._order_value = QLabel("-")
        self._sscc_value = QLabel("-")
        self._status_value = QLabel("-")
        self._operator_value = QLabel("-")
        self._count_value = QLabel("-")
        self._edit_status = QLabel(tr("boxes.editIdle"))
        self._edit_status.setObjectName("boxesStatusText")
        self._edit_error = QLabel("")
        self._edit_error.setObjectName("boxesErrorText")

        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.BOX, "#66d2c7"))
        header_text = QVBoxLayout()
        header_text.addWidget(self._title)
        header_text.addWidget(self._status)
        header.addLayout(header_text, 1)

        progress_row = QHBoxLayout()
        progress_caption = QLabel(tr("packing.progress"))
        progress_caption.setObjectName("boxesMutedText")
        progress_row.addWidget(progress_caption)
        progress_row.addStretch(1)
        progress_row.addWidget(self._progress_label)

        meta_grid = QGridLayout()
        meta_grid.setHorizontalSpacing(16)
        meta_grid.setVerticalSpacing(8)
        self._add_meta_row(meta_grid, 0, tr("packing.column.order"), self._order_value)
        self._add_meta_row(meta_grid, 1, "SSCC", self._sscc_value)
        self._add_meta_row(meta_grid, 2, tr("packing.column.status"), self._status_value)
        self._add_meta_row(meta_grid, 3, tr("packing.column.operator"), self._operator_value)
        self._add_meta_row(meta_grid, 4, tr("boxes.meta.accounting"), self._count_value)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(13)
        layout.addLayout(header)
        layout.addWidget(self._error)
        layout.addWidget(self._summary)
        layout.addLayout(progress_row)
        layout.addWidget(self._progress_bar)
        layout.addLayout(meta_grid)
        layout.addWidget(self._edit_status)
        layout.addWidget(self._edit_error)
        self._error.setVisible(False)
        self._edit_error.setVisible(False)

    def set_status(self, status: str, error: str) -> None:
        """Обновляет статус загрузки детальной карточки."""

        self._status.setText(status)
        self._error.setText(error)
        self._error.setVisible(bool(error))

    def set_edit_status(self, status: str, error: str) -> None:
        """Обновляет статус операций редактирования коробки."""

        self._edit_status.setText(status)
        self._edit_error.setText(error)
        self._edit_error.setVisible(bool(error))

    def set_empty(self) -> None:
        """Очищает панель, когда коробка не выбрана."""

        self._summary.setText(tr("boxes.detailSummary", value="-"))
        self._progress_label.setText("0 / 0")
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._order_value.setText("-")
        self._sscc_value.setText("-")
        self._status_value.setText("-")
        self._operator_value.setText("-")
        self._count_value.setText("-")

    def set_detail(self, detail: BoxDetailUi) -> None:
        """Показывает детальную информацию по выбранной коробке."""

        progress_max = max(detail.capacity, 1)
        progress_value = min(max(detail.filled, 0), progress_max)
        self._summary.setText(tr("packing.summary.boxTitle", box_id=detail.box_id))
        self._progress_label.setText(f"{detail.filled} / {detail.capacity}")
        self._progress_bar.setRange(0, progress_max)
        self._progress_bar.setValue(progress_value)
        self._order_value.setText(detail.order_name)
        self._sscc_value.setText(detail.sscc)
        self._status_value.setText(detail.status)
        self._operator_value.setText(detail.operator)
        self._count_value.setText(detail.count_in_packing)

    @staticmethod
    def _add_meta_row(
        grid: QGridLayout,
        row: int,
        title: str,
        value: QLabel,
    ) -> None:
        """Добавляет строку свойств коробки."""

        title_label = QLabel(title)
        title_label.setObjectName("boxesMetaTitle")
        value.setObjectName("boxesMetaValue")
        value.setWordWrap(True)
        grid.addWidget(title_label, row, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(value, row, 1)
