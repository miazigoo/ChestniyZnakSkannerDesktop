"""Модалка результата закрытия коробки."""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.packing_controller import CloseBoxUiEvent
from chestniy_znak_desktop.i18n import tr


class CloseBoxDialog(QDialog):
    """Показывает итог закрытия коробки с иллюстрацией."""

    def __init__(self, event: CloseBoxUiEvent, parent: QWidget | None = None) -> None:
        """Создает модалку результата закрытия."""

        super().__init__(parent)
        self.setObjectName("closeBoxDialog")
        self.setWindowTitle(event.title)
        self.setModal(True)
        self.setMinimumSize(760, 420)
        self.resize(820, 460)

        image = QLabel()
        image.setObjectName("closeBoxDialogImage")
        image.setPixmap(
            self._pixmap(event).scaledToWidth(
                300,
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

        ok_button = QPushButton(tr("common.ok"))
        ok_button.setObjectName("closeBoxDialogButton")
        ok_button.clicked.connect(self.accept)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(14)
        text_layout.addWidget(title)
        text_layout.addWidget(message)
        text_layout.addWidget(details)
        text_layout.addStretch(1)
        text_layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(28)
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
            tr("closeBox.detailsBox", box_id=event.box_id),
            tr("closeBox.detailsFill", filled=event.filled, capacity=event.capacity),
        ]
        if event.sscc:
            lines.append(f"SSCC: {event.sscc}")
        if event.print_ok is True:
            lines.append(
                tr(
                    "closeBox.printed",
                    printer=event.print_printer_name or tr("common.notAvailable"),
                )
            )
        elif event.print_ok is False:
            lines.append(
                tr(
                    "closeBox.printFailed",
                    error=event.print_error or tr("common.notAvailable"),
                )
            )
        if event.error_message:
            lines.append(tr("closeBox.error", error=event.error_message))
        return "\n".join(lines)


class CloseBoxConfirmDialog(QDialog):
    """Показывает красивое подтверждение закрытия неполной коробки."""

    def __init__(self, filled: int, capacity: int, parent: QWidget | None = None) -> None:
        """Создает диалог подтверждения закрытия коробки."""

        super().__init__(parent)
        self.setObjectName("closeBoxConfirmDialog")
        self.setWindowTitle(tr("closeBox.confirmTitle"))
        self.setModal(True)
        self.setMinimumSize(720, 390)

        image = QLabel()
        image.setObjectName("closeBoxDialogImage")
        image.setPixmap(
            self._box_pixmap("open_box.png").scaledToWidth(
                260,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(tr("closeBox.confirmTitle"))
        title.setObjectName("closeBoxDialogTitle")
        title.setWordWrap(True)

        message = QLabel(tr("closeBox.confirmMessage"))
        message.setObjectName("closeBoxDialogMessage")
        message.setWordWrap(True)

        details = QLabel(tr("closeBox.detailsFill", filled=filled, capacity=capacity))
        details.setObjectName("closeBoxDialogDetails")
        details.setWordWrap(True)

        cancel_button = QPushButton(tr("common.cancel"))
        cancel_button.setObjectName("closeBoxDialogSecondaryButton")
        cancel_button.clicked.connect(self.reject)

        close_button = QPushButton(tr("packing.closeBox"))
        close_button.setObjectName("closeBoxDialogButton")
        close_button.clicked.connect(self.accept)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(close_button)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(14)
        text_layout.addWidget(title)
        text_layout.addWidget(message)
        text_layout.addWidget(details)
        text_layout.addStretch(1)
        text_layout.addLayout(buttons_layout)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(28)
        layout.addWidget(image)
        layout.addLayout(text_layout, 1)

    @staticmethod
    def _box_pixmap(image_name: str) -> QPixmap:
        """Возвращает картинку коробки из ресурсов приложения."""

        image_path = resources.files("chestniy_znak_desktop.resources.icons").joinpath(image_name)
        return QPixmap(str(image_path))


class CloseBoxProgressDialog(QDialog):
    """Показывает ожидание закрытия коробки и печати этикетки."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает модалку прогресса закрытия коробки."""

        super().__init__(parent)
        self.setObjectName("closeBoxProgressDialog")
        self.setWindowTitle(tr("closeBox.progressTitle"))
        self.setModal(True)
        self.setMinimumSize(520, 230)

        title = QLabel(tr("closeBox.progressTitle"))
        title.setObjectName("closeBoxDialogTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)

        message = QLabel(tr("closeBox.progressMessage"))
        message.setObjectName("closeBoxDialogMessage")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)

        progress = QProgressBar()
        progress.setObjectName("closeBoxProgressBar")
        progress.setRange(0, 0)
        progress.setTextVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 34, 34)
        layout.setSpacing(18)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addWidget(progress)
