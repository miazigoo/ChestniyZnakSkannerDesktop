"""Модалка результата закрытия коробки."""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.packing_controller import CloseBoxUiEvent


class CloseBoxDialog(QDialog):
    """Показывает итог закрытия коробки с иллюстрацией."""

    def __init__(self, event: CloseBoxUiEvent, parent: QWidget | None = None) -> None:
        """Создает модалку результата закрытия."""

        super().__init__(parent)
        self.setObjectName("closeBoxDialog")
        self.setWindowTitle(event.title)
        self.setModal(True)
        self.setMinimumWidth(520)

        image = QLabel()
        image.setObjectName("closeBoxDialogImage")
        image.setPixmap(
            self._pixmap(event).scaledToWidth(
                210,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(event.title)
        title.setObjectName("closeBoxDialogTitle")
        title.setWordWrap(True)
        message = QLabel(event.message)
        message.setObjectName("closeBoxDialogMessage")
        message.setWordWrap(True)
        details = QLabel(self._details_text(event))
        details.setObjectName("closeBoxDialogDetails")
        details.setWordWrap(True)

        ok_button = QPushButton("OK")
        ok_button.setObjectName("closeBoxDialogButton")
        ok_button.clicked.connect(self.accept)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(10)
        text_layout.addWidget(title)
        text_layout.addWidget(message)
        text_layout.addWidget(details)
        text_layout.addStretch(1)
        text_layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)
        layout.addWidget(image)
        layout.addLayout(text_layout, 1)

    @staticmethod
    def _pixmap(event: CloseBoxUiEvent) -> QPixmap:
        """Возвращает картинку открытой или закрытой коробки."""

        image_name = "close_box.png" if event.is_full else "open_box.png"
        image_path = resources.files("chestniy_znak_desktop.resources.icons").joinpath(image_name)
        return QPixmap(str(image_path))

    @staticmethod
    def _details_text(event: CloseBoxUiEvent) -> str:
        """Формирует детали закрытой коробки."""

        lines = [
            f"Коробка: #{event.box_id}",
            f"Заполнение: {event.filled} / {event.capacity}",
        ]
        if event.sscc:
            lines.append(f"SSCC: {event.sscc}")
        if event.print_ok is False:
            lines.append("Печать: ошибка")
        elif event.print_ok is True:
            lines.append("Печать: выполнена")
        if event.error_message:
            lines.append(f"Ошибка: {event.error_message}")
        return "\n".join(lines)
