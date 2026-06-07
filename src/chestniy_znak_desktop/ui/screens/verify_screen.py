"""Экран проверки DataMatrix-кода."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.verify_controller import VerifyUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class VerifyScreen(QWidget):
    """Показывает результат проверки кода по скану."""

    duplicate_check_changed = Signal(bool)

    def __init__(self) -> None:
        """Создает scanner-only экран проверки кода."""

        super().__init__()
        self.setObjectName("verifyScreen")
        self._title = QLabel(tr("verify.title"))
        self._status = QLabel(tr("verify.waitScan"))
        self._scanner_status = QLabel(tr("verify.scannerChecking"))
        self._duplicate_check = QCheckBox(tr("verify.duplicate"))
        self._result = QLabel(tr("verify.resultWait"))
        self._error = QLabel("")
        self._last_code = QLabel(tr("verify.code", code="-"))
        self._technical_status = QLabel(tr("verify.technicalStatus", status="-"))
        self._exists = QLabel(tr("verify.exists", exists="-"))
        self._order = QLabel(tr("verify.order", order="-"))
        self._device = QLabel(tr("verify.device", device="-"))
        self._box = QLabel(tr("verify.box", box="-"))
        self._box_status = QLabel(tr("verify.boxStatus", status="-"))
        self._box_hint = QLabel(tr("verify.boxEmpty"))
        self._warnings = QLabel("")
        self._log = QTextEdit()
        self._log.setReadOnly(True)

        self._configure_widgets()
        self._build_layout()

    def apply_state(self, state: VerifyUiState) -> None:
        """Обновляет экран проверки из состояния контроллера."""

        has_error = bool(state.error_message)
        self._status.setText(state.status_message)
        self._result.setText(state.result_message or tr("verify.resultWait"))
        self._result.setProperty("tone", self._result_tone(state, has_error))
        self._result.style().unpolish(self._result)
        self._result.style().polish(self._result)
        self._error.setText(state.error_message)
        self._error.setVisible(has_error)
        self._last_code.setText(tr("verify.code", code=self._preview(state.last_visible_code)))
        self._technical_status.setText(
            tr("verify.technicalStatus", status=state.technical_status or "-")
        )
        self._exists.setText(tr("verify.exists", exists=self._exists_text(state.exists)))
        self._sync_duplicate_check(state.check_duplicates)
        self._order.setText(tr("verify.order", order=state.order_name or "-"))
        self._device.setText(tr("verify.device", device=state.device_name or "-"))
        self._box.setText(tr("verify.box", box=self._box_text(state)))
        self._box_status.setText(tr("verify.boxStatus", status=state.box_status or "-"))
        self._box_hint.setText(state.box_hint)
        warnings = "; ".join(state.warnings)
        self._warnings.setText(tr("verify.warnings", warnings=warnings) if warnings else "")
        self._warnings.setVisible(bool(warnings))
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для проверки."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(
                tr("verify.scannerReady", port=snapshot.scanner.port or "-")
            )
            self._scanner_status.setProperty("tone", "active")
        else:
            self._scanner_status.setText(tr("verify.scannerBlocked"))
            self._scanner_status.setProperty("tone", "error")
        self._scanner_status.style().unpolish(self._scanner_status)
        self._scanner_status.style().polish(self._scanner_status)

    def _configure_widgets(self) -> None:
        """Настраивает objectName и переносы текста."""

        self._title.setObjectName("verifyHeroTitle")
        self._status.setObjectName("verifyStatusText")
        self._scanner_status.setObjectName("verifyScannerStatus")
        self._duplicate_check.setObjectName("verifyDuplicateCheck")
        self._result.setObjectName("verifyResult")
        self._error.setObjectName("verifyError")
        self._last_code.setObjectName("verifyMetaValue")
        self._technical_status.setObjectName("verifyMetaValue")
        self._exists.setObjectName("verifyMetaValue")
        self._order.setObjectName("verifyMetaValue")
        self._device.setObjectName("verifyMetaValue")
        self._box.setObjectName("verifyMetaValue")
        self._box_status.setObjectName("verifyMetaValue")
        self._box_hint.setObjectName("verifyBoxHint")
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
            self._box,
            self._box_status,
            self._box_hint,
            self._warnings,
        ):
            label.setWordWrap(True)
        self._error.setVisible(False)
        self._warnings.setVisible(False)
        self._duplicate_check.toggled.connect(self.duplicate_check_changed.emit)

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
        subtitle = QLabel(tr("verify.heroSubtitle"))
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
        title = QLabel(tr("verify.source"))
        title.setObjectName("verifyCardTitle")
        note = QLabel(tr("verify.sourceNote"))
        note.setObjectName("verifyMutedText")
        note.setWordWrap(True)
        duplicate_note = QLabel(tr("verify.duplicateNote"))
        duplicate_note.setObjectName("verifyMutedText")
        duplicate_note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(VectorIcon(VectorIconName.SCANNER, "#8fb8ff"))
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self._scanner_status)
        layout.addWidget(self._duplicate_check)
        layout.addWidget(duplicate_note)
        layout.addStretch(1)
        return card

    def _create_result_card(self) -> QFrame:
        """Создает карточку результата проверки."""

        card = QFrame()
        card.setObjectName("verifyResultCard")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header_text = QVBoxLayout()
        title = QLabel(tr("verify.resultTitle"))
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
        layout.addWidget(self._box_hint)
        layout.addWidget(self._last_code)
        layout.addStretch(1)
        return card

    def _create_meta_panel(self) -> QFrame:
        """Создает панель деталей проверенного кода."""

        panel = QFrame()
        panel.setObjectName("verifyMetaPanel")
        title = QLabel(tr("verify.details"))
        title.setObjectName("verifyCardTitle")
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.addWidget(self._technical_status, 0, 0)
        grid.addWidget(self._exists, 0, 1)
        grid.addWidget(self._order, 1, 0)
        grid.addWidget(self._device, 1, 1)
        grid.addWidget(self._box, 2, 0)
        grid.addWidget(self._box_status, 2, 1)
        grid.addWidget(self._warnings, 3, 0, 1, 2)

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
        title = QLabel(tr("verify.logTitle"))
        title.setObjectName("verifyCardTitle")
        hint = QLabel(tr("verify.logHint"))
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
            return tr("verify.found")
        if exists is False:
            return tr("verify.notFound")
        return "-"

    @staticmethod
    def _box_text(state: VerifyUiState) -> str:
        """Возвращает компактное отображение коробки для карточки деталей."""

        if state.box_id is None and not state.box_sscc:
            return "-"
        if state.box_id is None:
            return state.box_sscc
        if not state.box_sscc:
            return f"#{state.box_id}"
        return f"#{state.box_id} · {state.box_sscc}"

    def _sync_duplicate_check(self, checked: bool) -> None:
        """Синхронизирует переключатель дублей без повторного сигнала."""

        if self._duplicate_check.isChecked() == checked:
            return
        self._duplicate_check.blockSignals(True)
        self._duplicate_check.setChecked(checked)
        self._duplicate_check.blockSignals(False)

    @staticmethod
    def _preview(code: str) -> str:
        """Возвращает компактное отображение кода маркировки."""

        if not code:
            return "-"
        compact = code.strip().replace("\n", "")
        if len(compact) <= 36:
            return compact
        return f"{compact[:18]}...{compact[-12:]}"
