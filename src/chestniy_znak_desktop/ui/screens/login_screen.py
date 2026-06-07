"""Экран авторизации оператора."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.auth_controller import AuthUiState
from chestniy_znak_desktop.i18n import (
    LANGUAGE_TITLES,
    SUPPORTED_LANGUAGES,
    current_language,
    tr,
)
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.i18n_widgets import retranslate_widget_tree
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class LoginStatusRow(QFrame):
    """Строка статуса с векторной иконкой."""

    def __init__(
        self,
        icon_name: VectorIconName,
        title: str,
        value: str,
        accent: str = "#56c7b8",
    ) -> None:
        """Создает строку статуса входа."""

        super().__init__()
        self.setObjectName("loginStatusRow")
        self._icon = VectorIcon(icon_name, accent)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("loginStatusTitle")
        self._value_label = QLabel(value)
        self._value_label.setObjectName("loginStatusValue")
        self._value_label.setWordWrap(True)

        texts = QVBoxLayout()
        texts.setContentsMargins(0, 0, 0, 0)
        texts.setSpacing(2)
        texts.addWidget(self._title_label)
        texts.addWidget(self._value_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(self._icon)
        layout.addLayout(texts, stretch=1)

    def set_value(self, value: str) -> None:
        """Обновляет текст значения статуса."""

        self._value_label.setText(value)


class LoginScreen(QWidget):
    """Экран входа по токену авторизации."""

    manual_token_submitted = Signal(str)
    language_changed = Signal(str)

    def __init__(self) -> None:
        """Создает современный экран ожидания скана авторизационного токена."""

        super().__init__()
        self.setObjectName("loginScreen")
        self.setMinimumSize(640, 460)
        self._title_label = QLabel(tr("login.product"))
        self._title_label.setObjectName("loginHeroTitle")
        self._subtitle_label = QLabel(tr("login.subtitle"))
        self._subtitle_label.setObjectName("loginHeroSubtitle")
        self._description_label = QLabel(tr("login.description"))
        self._description_label.setObjectName("loginHeroDescription")
        self._description_label.setWordWrap(True)
        self._language_label = QLabel(tr("common.language"))
        self._language_label.setObjectName("loginStatusTitle")
        self._language_select = QComboBox()
        self._language_select.setObjectName("settingsInput")
        for language in SUPPORTED_LANGUAGES:
            self._language_select.addItem(LANGUAGE_TITLES[language], language)
        self.set_language(current_language())
        self._language_select.currentIndexChanged.connect(self._emit_language_change)

        self._status_badge = QLabel(tr("login.waitBadge"))
        self._status_badge.setObjectName("loginStatusBadge")
        self._status_label = QLabel(tr("login.waitStatus"))
        self._status_label.setObjectName("loginPrimaryStatus")
        self._status_label.setWordWrap(True)
        self._error_label = QLabel("")
        self._error_label.setObjectName("loginError")
        self._error_label.setWordWrap(True)
        self._manual_input = QLineEdit()
        self._manual_input.setPlaceholderText(tr("login.manualPlaceholder"))
        self._manual_input.setClearButtonEnabled(True)
        self._manual_input.returnPressed.connect(self._submit_manual_token)
        self._manual_button = QPushButton(tr("login.manualSubmit"))
        self._manual_button.clicked.connect(self._submit_manual_token)

        self._connection_row = LoginStatusRow(
            VectorIconName.LINK,
            tr("login.connection"),
            tr("login.connectionChecking"),
            "#6ee7d8",
        )
        self._scanner_row = LoginStatusRow(
            VectorIconName.SCANNER,
            tr("login.scanner"),
            tr("login.scannerChecking"),
            "#e0b15e",
        )
        self._token_row = LoginStatusRow(
            VectorIconName.TOKEN,
            tr("login.lastScan"),
            "-",
            "#8ab4ff",
        )
        self._security_row = LoginStatusRow(
            VectorIconName.SHIELD,
            tr("login.session"),
            tr("login.security"),
            "#95d5b2",
        )
        self._build_layout()

    def set_language(self, language: str) -> None:
        """Синхронизирует выбранный язык без публикации сигнала."""

        index = self._language_select.findData(language)
        self._language_select.blockSignals(True)
        self._language_select.setCurrentIndex(max(index, 0))
        self._language_select.blockSignals(False)

    def retranslate(self) -> None:
        """Обновляет статические тексты login-экрана после смены языка."""

        retranslate_widget_tree(self)

    def apply_state(self, state: AuthUiState) -> None:
        """Обновляет экран из состояния контроллера авторизации."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._token_row.set_value(state.token_preview or "-")
        if state.is_submitting:
            self._status_badge.setText(tr("login.signingIn"))
        elif state.error_message:
            self._status_badge.setText(tr("login.needToken"))
        else:
            self._status_badge.setText(tr("login.ready"))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для входа."""

        self._connection_row.set_value(snapshot.connection.message)
        if snapshot.scanner.is_running:
            self._scanner_row.set_value(tr("login.scannerReady", port=snapshot.scanner.port))
            return
        self._scanner_row.set_value(tr("login.scannerStopped"))

    def paintEvent(self, _event: QPaintEvent) -> None:
        """Рисует векторный фон экрана входа."""

        super().paintEvent(_event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_scan_beams(painter)
        self._draw_matrix_pattern(painter)
        self._draw_orbit_lines(painter)

    def _build_layout(self) -> None:
        """Собирает layout hero-зоны и панели статусов."""

        hero = QVBoxLayout()
        hero.setContentsMargins(52, 58, 36, 48)
        hero.setSpacing(16)
        hero.addWidget(self._status_badge, alignment=Qt.AlignmentFlag.AlignLeft)
        hero.addSpacing(8)
        hero.addWidget(self._title_label)
        hero.addWidget(self._subtitle_label)
        hero.addWidget(self._description_label)
        language_row = QHBoxLayout()
        language_row.setContentsMargins(0, 0, 0, 0)
        language_row.setSpacing(10)
        language_row.addWidget(self._language_label)
        language_row.addWidget(self._language_select)
        language_row.addStretch(1)
        hero.addLayout(language_row)
        hero.addStretch(1)
        hero.addWidget(self._connection_row)

        panel = QFrame()
        panel.setObjectName("loginPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(14)
        panel_title = QLabel(tr("login.panelTitle"))
        panel_title.setObjectName("loginPanelTitle")
        panel_hint = QLabel(tr("login.panelHint"))
        panel_hint.setObjectName("loginPanelHint")
        panel_hint.setWordWrap(True)
        panel_layout.addWidget(panel_title)
        panel_layout.addWidget(panel_hint)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(self._status_label)
        panel_layout.addWidget(self._error_label)
        panel_layout.addSpacing(4)
        manual_label = QLabel(tr("login.manualToken"))
        manual_label.setObjectName("loginStatusTitle")
        manual_hint = QLabel(tr("login.manualHint"))
        manual_hint.setObjectName("loginPanelHint")
        manual_hint.setWordWrap(True)
        manual_row = QHBoxLayout()
        manual_row.setContentsMargins(0, 0, 0, 0)
        manual_row.setSpacing(8)
        manual_row.addWidget(self._manual_input, stretch=1)
        manual_row.addWidget(self._manual_button)
        panel_layout.addWidget(manual_label)
        panel_layout.addLayout(manual_row)
        panel_layout.addWidget(manual_hint)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(self._scanner_row)
        panel_layout.addWidget(self._token_row)
        panel_layout.addWidget(self._security_row)
        panel_layout.addStretch(1)

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 26)
        root.setSpacing(26)
        root.addLayout(hero, stretch=6)
        root.addWidget(panel, stretch=5)

    def _submit_manual_token(self) -> None:
        """Передает вручную введенный токен в контроллер авторизации."""

        value = self._manual_input.text().strip()
        if not value:
            return
        self.manual_token_submitted.emit(value)

    def _emit_language_change(self) -> None:
        """Публикует выбранный язык login-экрана."""

        self.language_changed.emit(str(self._language_select.currentData() or "ru"))

    def _draw_scan_beams(self, painter: QPainter) -> None:
        """Рисует декоративные лучи сканирования."""

        beam = QLinearGradient(0, 0, self.width(), 0)
        beam.setColorAt(0.0, QColor(86, 199, 184, 0))
        beam.setColorAt(0.55, QColor(86, 199, 184, 58))
        beam.setColorAt(1.0, QColor(224, 177, 94, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(beam)
        for offset in (90, 210, 330):
            path = QPainterPath()
            path.moveTo(-40, offset)
            path.lineTo(self.width() * 0.72, offset - 92)
            path.lineTo(self.width() * 0.72, offset - 64)
            path.lineTo(-40, offset + 28)
            path.closeSubpath()
            painter.drawPath(path)

    def _draw_matrix_pattern(self, painter: QPainter) -> None:
        """Рисует паттерн DataMatrix из векторных квадратов."""

        painter.setPen(Qt.PenStyle.NoPen)
        colors = [QColor(255, 255, 255, 42), QColor(86, 199, 184, 72)]
        size = 9
        start_x = int(self.width() * 0.08)
        start_y = int(self.height() * 0.58)
        pattern = {
            (0, 0),
            (1, 0),
            (2, 0),
            (0, 1),
            (2, 1),
            (0, 2),
            (1, 2),
            (2, 2),
            (4, 0),
            (6, 1),
            (5, 3),
            (7, 4),
            (4, 6),
            (6, 7),
            (8, 8),
            (9, 5),
        }
        for x_index, y_index in pattern:
            painter.setBrush(colors[(x_index + y_index) % 2])
            painter.drawRoundedRect(
                QRectF(start_x + x_index * 15, start_y + y_index * 15, size, size),
                2,
                2,
            )

    def _draw_orbit_lines(self, painter: QPainter) -> None:
        """Рисует тонкие технические контуры на фоне."""

        pen = QPen(QColor(255, 255, 255, 38), 1.4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(self.width() * 0.54, -150, 430, 430))
        painter.drawEllipse(QRectF(self.width() * 0.62, -80, 270, 270))
        painter.drawLine(
            QPointF(self.width() * 0.06, self.height() - 96),
            QPointF(self.width() * 0.42, 90),
        )
