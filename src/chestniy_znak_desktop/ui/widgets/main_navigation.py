"""Виджеты современной навигации главного экрана."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class MainSidebar(QFrame):
    """Декоративная боковая панель рабочего экрана."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает боковую панель с векторным фоном."""

        super().__init__(parent)
        self.setObjectName("mainSidebar")
        self.setFixedWidth(278)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Ignored)

    def set_compact(self, is_compact: bool) -> None:
        """Переключает ширину сайдбара для небольших экранов."""

        self.setFixedWidth(258 if is_compact else 278)
        self.setProperty("compact", is_compact)
        self.style().unpolish(self)
        self.style().polish(self)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Рисует премиальный фон боковой панели."""

        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor(86, 199, 184, 36), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(-86, 92, 210, 210))
        painter.drawEllipse(QRectF(132, -58, 176, 176))
        self._draw_data_matrix_hint(painter)

    def _draw_data_matrix_hint(self, painter: QPainter) -> None:
        """Рисует декоративный DataMatrix-паттерн."""

        painter.setPen(Qt.PenStyle.NoPen)
        pattern = {(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)}
        for x_index, y_index in pattern:
            painter.setBrush(QColor(86, 199, 184, 42))
            painter.drawRoundedRect(
                QRectF(28 + x_index * 12, self.height() - 126 + y_index * 12, 7, 7),
                1.5,
                1.5,
            )


class MainWorkspace(QFrame):
    """Контейнер рабочей области с мягким фоном."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает контейнер рабочей области."""

        super().__init__(parent)
        self.setObjectName("mainWorkspace")

    def paintEvent(self, event: QPaintEvent) -> None:
        """Рисует тонкий технический фон рабочей области."""

        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(86, 199, 184, 24), 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(self.width() - 260, -180, 440, 440))
        painter.drawLine(34, self.height() - 48, self.width() - 38, 58)


class NavItem(QFrame):
    """Пункт навигации с иконкой и активным состоянием."""

    clicked = Signal(int, str)

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_name: VectorIconName,
        index: int,
        screen_name: str,
        parent: QWidget | None = None,
    ) -> None:
        """Создает пункт навигации."""

        super().__init__(parent)
        self._index = index
        self._screen_name = screen_name
        self._active = False
        self.setObjectName("mainNavItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(58)
        self.setProperty("active", False)
        self.setProperty("screen_name", screen_name)
        self._icon = VectorIcon(icon_name, "#56c7b8")
        self._title = QLabel(title)
        self._title.setObjectName("mainNavTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("mainNavSubtitle")
        self._subtitle.setWordWrap(True)

        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(1)
        texts.addWidget(self._title)
        texts.addWidget(self._subtitle)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self._icon)
        layout.addLayout(texts, stretch=1)

    def set_active(self, active: bool) -> None:
        """Обновляет активное состояние пункта."""

        self._active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_texts(self, title: str, subtitle: str) -> None:
        """Обновляет локализованные тексты пункта навигации."""

        self._title.setText(title)
        self._subtitle.setText(subtitle)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Публикует переход по нажатию мышью."""

        self.clicked.emit(self._index, self._screen_name)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Рисует активный индикатор пункта."""

        super().paintEvent(event)
        if not self._active:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e0b15e"))
        path = QPainterPath()
        path.addRoundedRect(QRectF(4, 12, 4, self.height() - 24), 2, 2)
        painter.drawPath(path)
