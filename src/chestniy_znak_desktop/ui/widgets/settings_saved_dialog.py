"""Модалка успешного сохранения настроек."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.i18n import tr


class SvgBackdrop(QLabel):
    """Показывает декоративный SVG-фон внутри модалки."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создает виджет с встроенным SVG-фоном."""

        super().__init__(parent)
        self.setObjectName("settingsSavedSvgBackdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setScaledContents(True)
        self.setPixmap(self._render_svg(width=860, height=360))

    @classmethod
    def _render_svg(cls, width: int, height: int) -> QPixmap:
        """Рендерит SVG в pixmap один раз, без тяжелых repaint-операций."""

        renderer = QSvgRenderer(cls._svg_markup().encode("utf-8"))
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    @staticmethod
    def _svg_markup() -> str:
        """Возвращает SVG-разметку декоративного фона."""

        return """
        <svg xmlns="http://www.w3.org/2000/svg" width="860" height="360" viewBox="0 0 860 360">
          <defs>
            <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#66D2C7" stop-opacity="0.34"/>
              <stop offset="0.52" stop-color="#F3C969" stop-opacity="0.28"/>
              <stop offset="1" stop-color="#8FB8FF" stop-opacity="0.24"/>
            </linearGradient>
            <radialGradient id="glow" cx="70%" cy="5%" r="80%">
              <stop offset="0" stop-color="#66D2C7" stop-opacity="0.42"/>
              <stop offset="0.7" stop-color="#66D2C7" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <rect width="860" height="360" rx="30" fill="#101720"/>
          <rect width="860" height="360" rx="30" fill="url(#glow)"/>
          <path d="M-40 250 C120 140 235 350 410 230 C540 140 660 150 910 32"
                fill="none" stroke="url(#g1)" stroke-width="70" stroke-linecap="round"
                opacity="0.9"/>
          <path d="M-10 315 C155 220 270 390 470 292 C610 224 724 248 900 120"
                fill="none" stroke="#F3C969" stroke-width="12" stroke-linecap="round"
                opacity="0.42"/>
          <g opacity="0.54" fill="#66D2C7">
            <rect x="650" y="58" width="18" height="18" rx="4"/>
            <rect x="682" y="58" width="18" height="18" rx="4"/>
            <rect x="714" y="58" width="18" height="18" rx="4"/>
            <rect x="650" y="90" width="18" height="18" rx="4"/>
            <rect x="714" y="90" width="18" height="18" rx="4"/>
            <rect x="650" y="122" width="18" height="18" rx="4"/>
            <rect x="682" y="122" width="18" height="18" rx="4"/>
            <rect x="714" y="122" width="18" height="18" rx="4"/>
          </g>
          <circle cx="118" cy="112" r="58" fill="#66D2C7" opacity="0.16"/>
          <circle cx="118" cy="112" r="40" fill="#66D2C7" opacity="0.22"/>
          <path d="M94 112 L112 130 L146 90" fill="none" stroke="#F3C969"
                stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """


class SettingsSavedDialog(QDialog):
    """Показывает подтверждение успешного сохранения настроек."""

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        """Создает модалку с сообщением об успешном сохранении."""

        super().__init__(parent)
        self.setObjectName("settingsSavedDialog")
        self.setWindowTitle(tr("settings.savedTitle"))
        self.setModal(True)
        self.setMinimumSize(700, 330)
        self.resize(760, 360)

        backdrop = SvgBackdrop()

        title = QLabel(tr("settings.savedTitle"))
        title.setObjectName("settingsSavedTitle")
        title.setWordWrap(True)

        body = QLabel(message)
        body.setObjectName("settingsSavedMessage")
        body.setWordWrap(True)

        badge = QLabel(tr("settings.savedBadge"))
        badge.setObjectName("settingsSavedBadge")

        ok_button = QPushButton(tr("common.ok"))
        ok_button.setObjectName("settingsSavedButton")
        ok_button.clicked.connect(self.accept)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(34, 34, 34, 34)
        text_layout.setSpacing(16)
        text_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
        text_layout.addStretch(1)
        text_layout.addWidget(title)
        text_layout.addWidget(body)
        text_layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(ok_button)
        text_layout.addLayout(button_row)

        content = QWidget()
        content.setObjectName("settingsSavedContent")
        content.setLayout(text_layout)

        overlay = QGridLayout()
        overlay.setContentsMargins(0, 0, 0, 0)
        overlay.addWidget(backdrop, 0, 0)
        overlay.addWidget(content, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(overlay)
