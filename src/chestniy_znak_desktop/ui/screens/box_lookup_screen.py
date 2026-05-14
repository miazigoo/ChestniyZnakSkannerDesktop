"""Экран поиска коробки по скану."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.box_lookup_controller import BoxLookupUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class BoxLookupScreen(QWidget):
    """Показывает результат поиска коробки по SSCC или ID."""

    reset_requested = Signal()

    def __init__(self) -> None:
        """Создает экран поиска коробки без ручного ввода."""

        super().__init__()
        self.setObjectName("boxLookupScreen")
        self._title = QLabel("Поиск коробки")
        self._status = QLabel("Сканируйте штрихкод коробки")
        self._scanner_status = QLabel("Сканер: проверяем состояние")
        self._error = QLabel("")
        self._last_code = QLabel("Последний скан: -")
        self._found = QLabel("Коробка: -")
        self._reset_button = QPushButton("Сбросить статус")
        self._log = QTextEdit()
        self._log.setReadOnly(True)

        self._configure_controls()
        self._build_layout()
        self._apply_styles()

    def apply_state(self, state: BoxLookupUiState) -> None:
        """Обновляет экран поиска из состояния контроллера."""

        self._status.setText(state.status_message)
        self._error.setText(state.error_message)
        self._error.setVisible(bool(state.error_message))
        self._last_code.setText(f"Последний скан: {self._preview(state.last_scanned_code)}")
        self._found.setText(f"Коробка: {state.found_box_summary or '-'}")
        self._found.setProperty("tone", "found" if state.found_box_id is not None else "empty")
        self._found.style().unpolish(self._found)
        self._found.style().polish(self._found)
        self._reset_button.setEnabled(not state.is_busy)
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для поиска."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(f"Сканер готов: {snapshot.scanner.port or '-'}")
            self._scanner_status.setProperty("tone", "active")
        else:
            self._scanner_status.setText("Сканер не запущен. Поиск коробки заблокирован.")
            self._scanner_status.setProperty("tone", "error")
        self._scanner_status.style().unpolish(self._scanner_status)
        self._scanner_status.style().polish(self._scanner_status)

    def _configure_controls(self) -> None:
        """Настраивает сигналы и objectName виджетов."""

        self._title.setObjectName("lookupHeroTitle")
        self._status.setObjectName("lookupStatusTitle")
        self._scanner_status.setObjectName("lookupScannerStatus")
        self._error.setObjectName("lookupError")
        self._last_code.setObjectName("lookupLastCode")
        self._found.setObjectName("lookupFoundBox")
        self._reset_button.setObjectName("lookupSecondaryButton")
        self._log.setObjectName("lookupLog")
        self._last_code.setWordWrap(True)
        self._found.setWordWrap(True)
        self._reset_button.clicked.connect(self.reset_requested.emit)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру поиска коробки."""

        hero = self._create_hero()
        scanner_card = self._create_scanner_card()
        result_card = self._create_result_card()
        log_panel = self._create_log_panel()

        cards = QGridLayout()
        cards.setSpacing(18)
        cards.addWidget(scanner_card, 0, 0)
        cards.addWidget(result_card, 0, 1)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(hero)
        layout.addLayout(cards)
        layout.addWidget(log_panel, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний блок сценария поиска."""

        hero = QFrame()
        hero.setObjectName("lookupHero")
        icon = VectorIcon(VectorIconName.SCANNER, "#8fb8ff")
        subtitle = QLabel(
            "Сканируйте SSCC или ID коробки. После успешного поиска откроются детали "
            "в общем списке коробок."
        )
        subtitle.setObjectName("lookupHeroSubtitle")
        subtitle.setWordWrap(True)
        text = QVBoxLayout()
        text.addWidget(self._title)
        text.addWidget(subtitle)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(icon)
        layout.addLayout(text, 1)
        return hero

    def _create_scanner_card(self) -> QFrame:
        """Создает карточку готовности сканера."""

        card = QFrame()
        card.setObjectName("lookupCard")
        title = QLabel("Источник данных")
        title.setObjectName("lookupCardTitle")
        note = QLabel("Ручной ввод отключен")
        note.setObjectName("lookupMutedText")
        note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(VectorIcon(VectorIconName.LINK, "#66d2c7"))
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self._scanner_status)
        layout.addStretch(1)
        layout.addWidget(self._reset_button)
        return card

    def _create_result_card(self) -> QFrame:
        """Создает карточку результата последнего поиска."""

        card = QFrame()
        card.setObjectName("lookupResultCard")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.BOX, "#f3c969"))
        header_text = QVBoxLayout()
        title = QLabel("Результат поиска")
        title.setObjectName("lookupCardTitle")
        header_text.addWidget(title)
        header_text.addWidget(self._status)
        header.addLayout(header_text, 1)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._error)
        layout.addWidget(self._found)
        layout.addWidget(self._last_code)
        layout.addStretch(1)
        return card

    def _create_log_panel(self) -> QFrame:
        """Создает журнал последних попыток поиска."""

        panel = QFrame()
        panel.setObjectName("lookupLogPanel")
        header = QHBoxLayout()
        title = QLabel("Журнал сканов")
        title.setObjectName("lookupCardTitle")
        hint = QLabel("Последние попытки поиска коробок")
        hint.setObjectName("lookupMutedText")
        text = QVBoxLayout()
        text.addWidget(title)
        text.addWidget(hint)
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#66d2c7"))
        header.addLayout(text, 1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._log, 1)
        return panel

    @staticmethod
    def _preview(code: str) -> str:
        """Возвращает компактный вид последнего скана."""

        if not code:
            return "-"
        compact = code.strip().replace("\n", "")
        if len(compact) <= 34:
            return compact
        return f"{compact[:16]}...{compact[-12:]}"

    def _apply_styles(self) -> None:
        """Применяет локальные стили экрана поиска коробки."""

        self.setStyleSheet("""
            #boxLookupScreen {
                background: transparent;
            }
            #lookupHero,
            #lookupCard,
            #lookupResultCard,
            #lookupLogPanel {
                background: rgba(16, 24, 40, 222);
                border: 1px solid rgba(129, 140, 168, 70);
                border-radius: 18px;
            }
            #lookupHero {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(25, 47, 76, 238),
                    stop: 0.56 rgba(18, 32, 48, 235),
                    stop: 1 rgba(45, 62, 91, 222)
                );
            }
            #lookupHeroTitle {
                color: #f8fbff;
                font-size: 25px;
                font-weight: 850;
                background: transparent;
            }
            #lookupHeroSubtitle,
            #lookupMutedText,
            #lookupLastCode {
                color: rgba(225, 233, 244, 176);
                font-size: 13px;
                background: transparent;
            }
            #lookupCardTitle {
                color: #f8fbff;
                font-size: 17px;
                font-weight: 800;
                background: transparent;
            }
            #lookupStatusTitle {
                color: rgba(225, 233, 244, 205);
                font-size: 13px;
                font-weight: 750;
                background: transparent;
            }
            #lookupScannerStatus {
                border-radius: 12px;
                padding: 10px 12px;
                color: #071212;
                background: #66d2c7;
                font-size: 13px;
                font-weight: 850;
            }
            #lookupScannerStatus[tone="error"] {
                color: #fff4f2;
                background: rgba(227, 85, 78, 180);
            }
            #lookupFoundBox {
                color: #f8fbff;
                border-radius: 16px;
                padding: 16px 18px;
                background: rgba(255, 255, 255, 28);
                font-size: 20px;
                font-weight: 850;
            }
            #lookupFoundBox[tone="found"] {
                color: #071212;
                background: #66d2c7;
            }
            #lookupError {
                color: #ffb4ad;
                border-radius: 12px;
                padding: 10px 12px;
                background: rgba(227, 85, 78, 38);
                font-weight: 750;
            }
            #lookupSecondaryButton {
                min-height: 38px;
                border: 0;
                border-radius: 12px;
                padding: 0 14px;
                color: #f8fbff;
                background: rgba(255, 255, 255, 42);
                font-weight: 800;
            }
            #lookupSecondaryButton:disabled {
                color: rgba(225, 233, 244, 92);
                background: rgba(255, 255, 255, 22);
            }
            #lookupLog {
                color: #f8fbff;
                background: rgba(255, 255, 255, 18);
                border: 1px solid rgba(129, 140, 168, 55);
                border-radius: 14px;
                padding: 12px;
                selection-background-color: rgba(102, 210, 199, 70);
                selection-color: #f8fbff;
                font-family: monospace;
                font-size: 13px;
            }
            """)
