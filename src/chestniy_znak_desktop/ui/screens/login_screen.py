"""Экран авторизации оператора."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
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

    def __init__(self) -> None:
        """Создает современный экран ожидания скана авторизационного токена."""

        super().__init__()
        self.setObjectName("loginScreen")
        self.setMinimumSize(860, 560)
        self._title_label = QLabel("Честный знак")
        self._title_label.setObjectName("loginHeroTitle")
        self._subtitle_label = QLabel("Desktop-клиент оператора")
        self._subtitle_label.setObjectName("loginHeroSubtitle")
        self._description_label = QLabel(
            "Авторизация выполняется только сканером. Считайте QR-токен, "
            "чтобы открыть рабочие сценарии упаковки, проверки и брака."
        )
        self._description_label.setObjectName("loginHeroDescription")
        self._description_label.setWordWrap(True)

        self._status_badge = QLabel("Ожидание токена")
        self._status_badge.setObjectName("loginStatusBadge")
        self._status_label = QLabel("Ожидание токена авторизации")
        self._status_label.setObjectName("loginPrimaryStatus")
        self._status_label.setWordWrap(True)
        self._error_label = QLabel("")
        self._error_label.setObjectName("loginError")
        self._error_label.setWordWrap(True)

        self._connection_row = LoginStatusRow(
            VectorIconName.LINK,
            "Связь",
            "Проверяем соединение с сервером",
            "#6ee7d8",
        )
        self._scanner_row = LoginStatusRow(
            VectorIconName.SCANNER,
            "Сканер",
            "Проверяем подключение сканера",
            "#e0b15e",
        )
        self._token_row = LoginStatusRow(
            VectorIconName.TOKEN,
            "Последний скан",
            "-",
            "#8ab4ff",
        )
        self._security_row = LoginStatusRow(
            VectorIconName.SHIELD,
            "Сессия",
            "Токен будет отправлен в backend по защищенной cookie-сессии",
            "#95d5b2",
        )
        self._build_layout()
        self._apply_local_style()

    def apply_state(self, state: AuthUiState) -> None:
        """Обновляет экран из состояния контроллера авторизации."""

        self._status_label.setText(state.status_message)
        self._error_label.setText(state.error_message)
        self._token_row.set_value(state.token_preview or "-")
        if state.is_submitting:
            self._status_badge.setText("Выполняем вход")
        elif state.error_message:
            self._status_badge.setText("Требуется новый токен")
        else:
            self._status_badge.setText("Готов к скану")

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для входа."""

        self._connection_row.set_value(snapshot.connection.message)
        if snapshot.scanner.is_running:
            self._scanner_row.set_value(f"Готов к чтению: {snapshot.scanner.port}")
            return
        self._scanner_row.set_value("Сканер не запущен. Вход невозможен без сканера.")

    def paintEvent(self, _event: object) -> None:
        """Рисует векторный фон экрана входа."""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_gradient_background(painter)
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
        hero.addStretch(1)
        hero.addWidget(self._connection_row)

        panel = QFrame()
        panel.setObjectName("loginPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(14)
        panel_title = QLabel("Вход по QR-токену")
        panel_title.setObjectName("loginPanelTitle")
        panel_hint = QLabel("Поднесите QR авторизации к подключенному COM/SPP-сканеру.")
        panel_hint.setObjectName("loginPanelHint")
        panel_hint.setWordWrap(True)
        panel_layout.addWidget(panel_title)
        panel_layout.addWidget(panel_hint)
        panel_layout.addSpacing(6)
        panel_layout.addWidget(self._status_label)
        panel_layout.addWidget(self._error_label)
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

    def _apply_local_style(self) -> None:
        """Применяет локальные стили login-экрана поверх общей темы."""

        self.setStyleSheet("""
            #loginHeroTitle {
                color: #ffffff;
                font-size: 46px;
                font-weight: 800;
                letter-spacing: 0px;
            }
            #loginHeroSubtitle {
                color: #b9f7ef;
                font-size: 22px;
                font-weight: 700;
            }
            #loginHeroDescription {
                color: rgba(255, 255, 255, 0.80);
                font-size: 16px;
                line-height: 136%;
            }
            #loginStatusBadge {
                color: #071217;
                background: #e0b15e;
                border-radius: 14px;
                padding: 7px 12px;
                font-weight: 800;
            }
            #loginPanel {
                background: rgba(12, 18, 24, 0.82);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 18px;
            }
            #loginPanelTitle {
                color: #ffffff;
                font-size: 28px;
                font-weight: 800;
            }
            #loginPanelHint, #loginStatusValue {
                color: rgba(236, 244, 247, 0.76);
                font-size: 14px;
            }
            #loginPrimaryStatus {
                color: #ffffff;
                font-size: 17px;
                font-weight: 700;
                padding: 8px 0;
            }
            #loginError {
                color: #ff9a8d;
                font-size: 15px;
                font-weight: 700;
                min-height: 22px;
            }
            #loginStatusRow {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 14px;
            }
            #loginStatusTitle {
                color: #ffffff;
                font-weight: 800;
                font-size: 14px;
            }
            """)

    def _draw_gradient_background(self, painter: QPainter) -> None:
        """Рисует глубокий градиентный фон."""

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#071217"))
        gradient.setColorAt(0.48, QColor("#102a32"))
        gradient.setColorAt(1.0, QColor("#1d1726"))
        painter.fillRect(self.rect(), gradient)

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
