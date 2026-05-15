"""Адаптивный scroll-контейнер для рабочих экранов."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QWidget


class AdaptiveScrollArea(QScrollArea):
    """Дает экрану вертикальный скролл без раздувания главного окна."""

    def __init__(self, content: QWidget, object_name: str, parent: QWidget | None = None) -> None:
        """Создает прозрачный scroll-wrapper вокруг переданного контента."""

        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setWidget(content)

    def minimumSizeHint(self) -> QSize:
        """Возвращает компактный минимум, чтобы маленький экран не ломал окно."""

        return QSize(320, 240)

    def sizeHint(self) -> QSize:
        """Возвращает разумный размер, не заставляя окно расти под весь контент."""

        widget = self.widget()
        content_size = widget.sizeHint() if widget is not None else QSize(900, 640)
        return QSize(min(content_size.width(), 1000), min(content_size.height(), 680))
