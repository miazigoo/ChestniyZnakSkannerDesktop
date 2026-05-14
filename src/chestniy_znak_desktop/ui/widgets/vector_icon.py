"""Векторные иконки для рабочих экранов."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class VectorIconName(str, Enum):
    """Доступные кодовые имена векторных иконок."""

    SCANNER = "scanner"
    SHIELD = "shield"
    LINK = "link"
    TOKEN = "token"
    WARNING = "warning"
    BOX = "box"
    SETTINGS = "settings"
    DIAGNOSTICS = "diagnostics"


class VectorIcon(QWidget):
    """Рисует простую тематическую иконку без bitmap-ресурсов."""

    def __init__(
        self,
        icon_name: VectorIconName,
        color: str = "#56c7b8",
        parent: QWidget | None = None,
    ) -> None:
        """Создает виджет векторной иконки."""

        super().__init__(parent)
        self._icon_name = icon_name
        self._color = QColor(color)
        self.setFixedSize(34, 34)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _event: object) -> None:
        """Рисует выбранную иконку."""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(5, 5, 24, 24)
        if self._icon_name == VectorIconName.SCANNER:
            self._draw_scanner(painter, rect)
        elif self._icon_name == VectorIconName.SHIELD:
            self._draw_shield(painter, rect)
        elif self._icon_name == VectorIconName.LINK:
            self._draw_link(painter, rect)
        elif self._icon_name == VectorIconName.TOKEN:
            self._draw_token(painter, rect)
        elif self._icon_name == VectorIconName.BOX:
            self._draw_box(painter, rect)
        elif self._icon_name == VectorIconName.SETTINGS:
            self._draw_settings(painter, rect)
        elif self._icon_name == VectorIconName.DIAGNOSTICS:
            self._draw_diagnostics(painter, rect)
        else:
            self._draw_warning(painter, rect)

    @staticmethod
    def _draw_scanner(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку сканера."""

        painter.drawRoundedRect(rect.adjusted(1, 4, -1, -4), 4, 4)
        painter.drawLine(
            QPointF(rect.left() + 5, rect.center().y()),
            QPointF(rect.right() - 5, rect.center().y()),
        )
        painter.drawLine(
            QPointF(rect.left() + 8, rect.bottom() - 2),
            QPointF(rect.right() - 8, rect.bottom() - 2),
        )

    @staticmethod
    def _draw_shield(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку защищенной сессии."""

        path = QPainterPath()
        path.moveTo(rect.center().x(), rect.top())
        path.lineTo(rect.right() - 2, rect.top() + 5)
        path.lineTo(rect.right() - 4, rect.bottom() - 5)
        path.quadTo(rect.center().x(), rect.bottom(), rect.left() + 4, rect.bottom() - 5)
        path.lineTo(rect.left() + 2, rect.top() + 5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(
            QPointF(rect.left() + 8, rect.center().y()),
            QPointF(rect.center().x() - 1, rect.bottom() - 7),
        )
        painter.drawLine(
            QPointF(rect.center().x() - 1, rect.bottom() - 7),
            QPointF(rect.right() - 7, rect.top() + 8),
        )

    @staticmethod
    def _draw_link(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку сетевого соединения."""

        painter.drawEllipse(QRectF(rect.left(), rect.center().y() - 5, 10, 10))
        painter.drawEllipse(QRectF(rect.right() - 10, rect.center().y() - 5, 10, 10))
        painter.drawLine(
            QPointF(rect.left() + 10, rect.center().y()),
            QPointF(rect.right() - 10, rect.center().y()),
        )

    @staticmethod
    def _draw_token(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку QR-токена."""

        size = 6
        for x_index, y_index in ((0, 0), (2, 0), (0, 2), (2, 2), (1, 1)):
            x = rect.left() + x_index * 8
            y = rect.top() + y_index * 8
            painter.drawRoundedRect(QRectF(x, y, size, size), 1.5, 1.5)

    @staticmethod
    def _draw_warning(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку предупреждения."""

        path = QPainterPath()
        path.moveTo(rect.center().x(), rect.top())
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left(), rect.bottom())
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(
            QPointF(rect.center().x(), rect.top() + 8),
            QPointF(rect.center().x(), rect.bottom() - 8),
        )
        painter.drawPoint(QPointF(rect.center().x(), rect.bottom() - 4))

    @staticmethod
    def _draw_box(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку коробки."""

        top = QPainterPath()
        top.moveTo(rect.left() + 3, rect.top() + 8)
        top.lineTo(rect.center().x(), rect.top() + 2)
        top.lineTo(rect.right() - 3, rect.top() + 8)
        top.lineTo(rect.center().x(), rect.top() + 14)
        top.closeSubpath()
        painter.drawPath(top)
        painter.drawRoundedRect(rect.adjusted(3, 8, -3, -2), 3, 3)
        painter.drawLine(
            QPointF(rect.center().x(), rect.top() + 14),
            QPointF(rect.center().x(), rect.bottom() - 2),
        )

    @staticmethod
    def _draw_settings(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку настроек."""

        painter.drawEllipse(rect.adjusted(5, 5, -5, -5))
        painter.drawEllipse(rect.adjusted(10, 10, -10, -10))
        for x_offset, y_offset in ((12, 0), (12, 24), (0, 12), (24, 12)):
            painter.drawLine(
                QPointF(rect.left() + x_offset, rect.top() + y_offset),
                QPointF(rect.center().x(), rect.center().y()),
            )

    @staticmethod
    def _draw_diagnostics(painter: QPainter, rect: QRectF) -> None:
        """Рисует иконку диагностики."""

        painter.drawRoundedRect(rect.adjusted(2, 3, -2, -3), 4, 4)
        painter.drawLine(
            QPointF(rect.left() + 7, rect.bottom() - 8),
            QPointF(rect.left() + 7, rect.top() + 12),
        )
        painter.drawLine(
            QPointF(rect.center().x(), rect.bottom() - 8),
            QPointF(rect.center().x(), rect.top() + 7),
        )
        painter.drawLine(
            QPointF(rect.right() - 7, rect.bottom() - 8),
            QPointF(rect.right() - 7, rect.top() + 15),
        )
