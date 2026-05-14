"""Экран отправки кода в брак."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class DefectScreen(QWidget):
    """Показывает результат сценария брака по скану."""

    def __init__(self) -> None:
        """Создает экран брака с журналом результата."""

        super().__init__()
        self._title = QLabel("Брак")
        self._status = QLabel("Ожидание скана кода")
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._status)
        layout.addWidget(self._log)
