"""Экран проверки DataMatrix-кода."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.verify_controller import VerifyUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class VerifyScreen(QWidget):
    """Показывает результат проверки кода по скану."""

    def __init__(self) -> None:
        """Создает scanner-only экран проверки кода."""

        super().__init__()
        self.setObjectName("verifyScreen")
        self._title = QLabel("Проверка DataMatrix")
        self._status = QLabel("Ожидание скана кода")
        self._scanner_status = QLabel("Сканер: проверяем состояние")
        self._result = QLabel("Ожидаем DataMatrix от сканера")
        self._error = QLabel("")
        self._last_code = QLabel("Код: -")
        self._technical_status = QLabel("Статус: -")
        self._exists = QLabel("Наличие: -")
        self._order = QLabel("Заказ: -")
        self._device = QLabel("Устройство: -")
        self._warnings = QLabel("")
        self._log = QTextEdit()
        self._log.setReadOnly(True)

        self._configure_widgets()
        self._build_layout()
        self._apply_styles()

    def apply_state(self, state: VerifyUiState) -> None:
        """Обновляет экран проверки из состояния контроллера."""

        has_error = bool(state.error_message)
        self._status.setText(state.status_message)
        self._result.setText(state.result_message or "Ожидаем DataMatrix от сканера")
        self._result.setProperty("tone", self._result_tone(state, has_error))
        self._result.style().unpolish(self._result)
        self._result.style().polish(self._result)
        self._error.setText(state.error_message)
        self._error.setVisible(has_error)
        self._last_code.setText(f"Код: {self._preview(state.last_visible_code)}")
        self._technical_status.setText(f"Статус: {state.technical_status or '-'}")
        self._exists.setText(f"Наличие: {self._exists_text(state.exists)}")
        self._order.setText(f"Заказ: {state.order_name or '-'}")
        self._device.setText(f"Устройство: {state.device_name or '-'}")
        warnings = "; ".join(state.warnings)
        self._warnings.setText(f"Предупреждения: {warnings}" if warnings else "")
        self._warnings.setVisible(bool(warnings))
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для проверки."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(f"Сканер готов: {snapshot.scanner.port or '-'}")
            self._scanner_status.setProperty("tone", "active")
        else:
            self._scanner_status.setText("Сканер не запущен. Проверка кода заблокирована.")
            self._scanner_status.setProperty("tone", "error")
        self._scanner_status.style().unpolish(self._scanner_status)
        self._scanner_status.style().polish(self._scanner_status)

    def _configure_widgets(self) -> None:
        """Настраивает objectName и переносы текста."""

        self._title.setObjectName("verifyHeroTitle")
        self._status.setObjectName("verifyStatusText")
        self._scanner_status.setObjectName("verifyScannerStatus")
        self._result.setObjectName("verifyResult")
        self._error.setObjectName("verifyError")
        self._last_code.setObjectName("verifyMetaValue")
        self._technical_status.setObjectName("verifyMetaValue")
        self._exists.setObjectName("verifyMetaValue")
        self._order.setObjectName("verifyMetaValue")
        self._device.setObjectName("verifyMetaValue")
        self._warnings.setObjectName("verifyWarning")
        self._log.setObjectName("verifyLog")
        for label in (
            self._status,
            self._result,
            self._error,
            self._last_code,
            self._technical_status,
            self._exists,
            self._order,
            self._device,
            self._warnings,
        ):
            label.setWordWrap(True)
        self._error.setVisible(False)
        self._warnings.setVisible(False)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру экрана проверки."""

        hero = self._create_hero()
        scanner_card = self._create_scanner_card()
        result_card = self._create_result_card()
        meta_panel = self._create_meta_panel()
        log_panel = self._create_log_panel()

        top_grid = QGridLayout()
        top_grid.setSpacing(18)
        top_grid.addWidget(scanner_card, 0, 0)
        top_grid.addWidget(result_card, 0, 1)
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(hero)
        layout.addLayout(top_grid)
        layout.addWidget(meta_panel)
        layout.addWidget(log_panel, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний блок сценария проверки."""

        hero = QFrame()
        hero.setObjectName("verifyHero")
        icon = VectorIcon(VectorIconName.SHIELD, "#66d2c7")
        subtitle = QLabel(
            "Сканируйте DataMatrix изделия. Приложение проверит наличие кода "
            "в backend и покажет заказ, устройство и предупреждения."
        )
        subtitle.setObjectName("verifyHeroSubtitle")
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
        """Создает карточку источника сканов."""

        card = QFrame()
        card.setObjectName("verifyCard")
        title = QLabel("Источник данных")
        title.setObjectName("verifyCardTitle")
        note = QLabel("Ручной ввод отключен, принимаем только сканер")
        note.setObjectName("verifyMutedText")
        note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(VectorIcon(VectorIconName.SCANNER, "#8fb8ff"))
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self._scanner_status)
        layout.addStretch(1)
        return card

    def _create_result_card(self) -> QFrame:
        """Создает карточку результата проверки."""

        card = QFrame()
        card.setObjectName("verifyResultCard")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header_text = QVBoxLayout()
        title = QLabel("Результат проверки")
        title.setObjectName("verifyCardTitle")
        header_text.addWidget(title)
        header_text.addWidget(self._status)
        header.addLayout(header_text, 1)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._error)
        layout.addWidget(self._result)
        layout.addWidget(self._last_code)
        layout.addStretch(1)
        return card

    def _create_meta_panel(self) -> QFrame:
        """Создает панель деталей проверенного кода."""

        panel = QFrame()
        panel.setObjectName("verifyMetaPanel")
        title = QLabel("Детали кода")
        title.setObjectName("verifyCardTitle")
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.addWidget(self._technical_status, 0, 0)
        grid.addWidget(self._exists, 0, 1)
        grid.addWidget(self._order, 1, 0)
        grid.addWidget(self._device, 1, 1)
        grid.addWidget(self._warnings, 2, 0, 1, 2)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addLayout(grid)
        return panel

    def _create_log_panel(self) -> QFrame:
        """Создает журнал последних проверок."""

        panel = QFrame()
        panel.setObjectName("verifyLogPanel")
        header = QHBoxLayout()
        title = QLabel("Журнал проверок")
        title.setObjectName("verifyCardTitle")
        hint = QLabel("Последние результаты проверки DataMatrix")
        hint.setObjectName("verifyMutedText")
        text = QVBoxLayout()
        text.addWidget(title)
        text.addWidget(hint)
        header.addWidget(VectorIcon(VectorIconName.LINK, "#66d2c7"))
        header.addLayout(text, 1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._log, 1)
        return panel

    @staticmethod
    def _result_tone(state: VerifyUiState, has_error: bool) -> str:
        """Возвращает визуальный тон результата проверки."""

        if has_error or state.exists is False:
            return "error"
        if state.exists is True:
            return "ok"
        return "idle"

    @staticmethod
    def _exists_text(exists: bool | None) -> str:
        """Возвращает человекочитаемый статус наличия кода."""

        if exists is True:
            return "код найден"
        if exists is False:
            return "код не найден"
        return "-"

    @staticmethod
    def _preview(code: str) -> str:
        """Возвращает компактное отображение кода маркировки."""

        if not code:
            return "-"
        compact = code.strip().replace("\n", "")
        if len(compact) <= 36:
            return compact
        return f"{compact[:18]}...{compact[-12:]}"

    def _apply_styles(self) -> None:
        """Применяет локальные стили экрана проверки."""

        self.setStyleSheet("""
            #verifyScreen {
                background: transparent;
            }
            #verifyHero,
            #verifyCard,
            #verifyResultCard,
            #verifyMetaPanel,
            #verifyLogPanel {
                background: rgba(16, 24, 40, 222);
                border: 1px solid rgba(129, 140, 168, 70);
                border-radius: 18px;
            }
            #verifyHero {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(27, 58, 65, 238),
                    stop: 0.56 rgba(18, 32, 48, 235),
                    stop: 1 rgba(42, 58, 86, 222)
                );
            }
            #verifyHeroTitle {
                color: #f8fbff;
                font-size: 25px;
                font-weight: 850;
                background: transparent;
            }
            #verifyHeroSubtitle,
            #verifyMutedText,
            #verifyStatusText {
                color: rgba(225, 233, 244, 176);
                font-size: 13px;
                background: transparent;
            }
            #verifyCardTitle {
                color: #f8fbff;
                font-size: 17px;
                font-weight: 800;
                background: transparent;
            }
            #verifyScannerStatus {
                border-radius: 12px;
                padding: 10px 12px;
                color: #071212;
                background: #66d2c7;
                font-size: 13px;
                font-weight: 850;
            }
            #verifyScannerStatus[tone="error"] {
                color: #fff4f2;
                background: rgba(227, 85, 78, 180);
            }
            #verifyResult {
                color: #071212;
                border-radius: 16px;
                padding: 16px 18px;
                background: #66d2c7;
                font-size: 20px;
                font-weight: 850;
            }
            #verifyResult[tone="idle"] {
                color: #f8fbff;
                background: rgba(255, 255, 255, 28);
            }
            #verifyResult[tone="error"] {
                color: #fff4f2;
                background: rgba(227, 85, 78, 190);
            }
            #verifyError {
                color: #ffb4ad;
                border-radius: 12px;
                padding: 10px 12px;
                background: rgba(227, 85, 78, 38);
                font-weight: 750;
            }
            #verifyMetaValue {
                color: #f8fbff;
                border-radius: 14px;
                padding: 12px 14px;
                background: rgba(255, 255, 255, 28);
                font-size: 13px;
                font-weight: 700;
            }
            #verifyWarning {
                color: #1f1600;
                border-radius: 14px;
                padding: 12px 14px;
                background: #f3c969;
                font-size: 13px;
                font-weight: 800;
            }
            #verifyLog {
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
