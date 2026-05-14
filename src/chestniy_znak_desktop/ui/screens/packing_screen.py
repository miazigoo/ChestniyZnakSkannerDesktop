"""Основной экран упаковки кодов в коробку."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QVBoxLayout, QWidget


class PackingScreen(QWidget):
    """Рабочий экран оператора упаковки."""

    def __init__(self) -> None:
        """Создает базовую раскладку экрана упаковки."""

        super().__init__()
        self._status_label = QLabel("Открытая коробка не найдена")
        self._open_box_button = QPushButton("Открыть коробку")
        self._items_table = QTableWidget(0, 3)
        self._items_table.setHorizontalHeaderLabels(["GTIN", "Serial", "Код"])
        layout = QVBoxLayout(self)
        layout.addWidget(self._status_label)
        layout.addWidget(self._open_box_button)
        layout.addWidget(self._items_table)
