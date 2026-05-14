"""Карточки состояния для рабочего экрана упаковки."""

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

from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class PackingSummaryCard(QFrame):
    """Показывает текущую коробку, прогресс и ключевые параметры."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает карточку текущей коробки."""

        super().__init__(parent)
        self.setObjectName("packingCard")
        self._box_title = QLabel("Коробка не открыта")
        self._box_title.setObjectName("packingCardTitle")
        self._box_subtitle = QLabel("Откройте коробку и сканируйте изделия")
        self._box_subtitle.setObjectName("packingMutedText")
        self._status_badge = QLabel("Ожидание")
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

        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.BOX, "#66d2c7"))
        title_block = QVBoxLayout()
        title_block.addWidget(self._box_title)
        title_block.addWidget(self._box_subtitle)
        header.addLayout(title_block, 1)
        header.addWidget(self._status_badge)

        progress_row = QHBoxLayout()
        progress_caption = QLabel("Заполнение")
        progress_caption.setObjectName("packingMutedText")
        progress_row.addWidget(progress_caption)
        progress_row.addStretch(1)
        progress_row.addWidget(self._progress_label)

        meta_grid = QGridLayout()
        meta_grid.setHorizontalSpacing(18)
        meta_grid.setVerticalSpacing(6)
        self._add_meta_row(meta_grid, 0, "Заказ", self._order_value)
        self._add_meta_row(meta_grid, 1, "SSCC", self._sscc_value)
        self._add_meta_row(meta_grid, 2, "Режим", self._mode_value)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addLayout(progress_row)
        layout.addWidget(self._progress_bar)
        layout.addLayout(meta_grid)

    @property
    def progress_bar(self) -> QProgressBar:
        """Возвращает прогресс-бар для тестов и внешней синхронизации."""

        return self._progress_bar

    def set_empty(self) -> None:
        """Переводит карточку в состояние без открытой коробки."""

        self._box_title.setText("Коробка не открыта")
        self._box_subtitle.setText("Сканирование изделий пока заблокировано")
        self._status_badge.setText("Ожидание")
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

        progress_max = max(capacity, 1)
        progress_value = min(max(filled, 0), progress_max)
        self._box_title.setText(f"Коробка #{box_id}")
        self._box_subtitle.setText("Готова принимать DataMatrix от сканера")
        self._status_badge.setText("Закрыта" if is_closed else "Открыта")
        self._status_badge.setProperty("tone", "closed" if is_closed else "active")
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)
        self._progress_label.setText(f"{filled} / {capacity}")
        self._progress_bar.setRange(0, progress_max)
        self._progress_bar.setValue(progress_value)
        self._order_value.setText(order_name or "-")
        self._sscc_value.setText(sscc or "-")
        mode = "Учитывается в упаковке" if count_in_packing else "Без учета упаковки"
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
        self._scanner_label = QLabel("Сканер: проверяем состояние")
        self._scanner_label.setObjectName("packingScannerStatus")
        self._status_label = QLabel("Открытая коробка не найдена")
        self._status_label.setObjectName("packingScanTitle")
        self._result_label = QLabel("")
        self._result_label.setObjectName("packingResult")
        self._error_label = QLabel("")
        self._error_label.setObjectName("packingError")
        self._last_code_label = QLabel("Последний скан: -")
        self._last_code_label.setObjectName("packingMutedText")

        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.SCANNER, "#8fb8ff"))
        header_text = QVBoxLayout()
        title = QLabel("Сканирование изделий")
        title.setObjectName("packingCardTitle")
        subtitle = QLabel("Ручной ввод отключен, принимаем только данные сканера")
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
            self._scanner_label.setText(f"Сканер готов: {port or '-'}")
            self._scanner_label.setProperty("tone", "active")
        else:
            self._scanner_label.setText("Сканер не запущен. Упаковка заблокирована.")
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
        self._result_label.setText(result or "Ожидаем скан изделия")
        self._error_label.setText(error)
        self._error_label.setVisible(bool(error))
        self._last_code_label.setText(f"Последний скан: {self._preview(last_code)}")

    @staticmethod
    def _preview(code: str) -> str:
        """Возвращает короткое отображение длинного кода маркировки."""

        if not code:
            return "-"
        compact = code.strip().replace("\n", "")
        if len(compact) <= 20:
            return compact
        return f"{compact[:10]}...{compact[-8:]}"
