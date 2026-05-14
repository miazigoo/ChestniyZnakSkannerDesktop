"""Экран списка коробок."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QTableWidget, QVBoxLayout, QWidget


class BoxesScreen(QWidget):
    """Показывает список коробок и поиск по ним."""

    def __init__(self) -> None:
        """Создает базовый экран списка коробок."""

        super().__init__()
        self._title = QLabel("Список коробок")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по SSCC, заказу или ID")
        self._refresh_button = QPushButton("Обновить")
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["ID", "Заказ", "SSCC", "Заполнено", "Статус"])
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._search_input)
        layout.addWidget(self._refresh_button)
        layout.addWidget(self._table)
