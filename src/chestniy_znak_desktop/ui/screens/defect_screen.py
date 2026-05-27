"""Экран отправки кода в брак."""

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

from chestniy_znak_desktop.controllers.defect_controller import DefectUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class DefectScreen(QWidget):
    """Показывает результат сценария брака по скану."""

    def __init__(self) -> None:
        """Создает scanner-only экран брака с журналом результата."""

        super().__init__()
        self.setObjectName("defectScreen")
        self._title = QLabel(tr("defect.title"))
        self._status = QLabel(tr("defect.waitScan"))
        self._scanner_status = QLabel(tr("verify.scannerChecking"))
        self._result = QLabel(tr("defect.resultWait"))
        self._error = QLabel("")
        self._last_code = QLabel(tr("verify.code", code="-"))
        self._order = QLabel(tr("verify.order", order="-"))
        self._device = QLabel(tr("verify.device", device="-"))
        self._removed_box = QLabel(tr("defect.removedFromBox", value="-"))
        self._warnings = QLabel("")
        self._log = QTextEdit()
        self._log.setReadOnly(True)

        self._configure_widgets()
        self._build_layout()

    def apply_state(self, state: DefectUiState) -> None:
        """Обновляет экран брака из состояния контроллера."""

        has_error = bool(state.error_message)
        self._status.setText(state.status_message)
        self._result.setText(state.result_message or tr("defect.resultWait"))
        self._result.setProperty("tone", "error" if has_error else "ok")
        self._result.style().unpolish(self._result)
        self._result.style().polish(self._result)
        self._error.setText(state.error_message)
        self._error.setVisible(has_error)
        self._last_code.setText(tr("verify.code", code=self._preview(state.last_visible_code)))
        self._order.setText(tr("verify.order", order=state.order_name or "-"))
        self._device.setText(tr("verify.device", device=state.device_name or "-"))
        removed_box = state.removed_box_message or "-"
        self._removed_box.setText(tr("defect.removedFromBox", value=removed_box))
        warnings = "; ".join(state.warnings)
        self._warnings.setText(tr("verify.warnings", warnings=warnings) if warnings else "")
        self._warnings.setVisible(bool(warnings))
        self._log.setPlainText("\n".join(state.log))

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет подсказку о доступности сканера для брака."""

        if snapshot.scanner.is_running:
            self._scanner_status.setText(
                tr("verify.scannerReady", port=snapshot.scanner.port or "-")
            )
            self._scanner_status.setProperty("tone", "active")
        else:
            self._scanner_status.setText(tr("defect.scannerBlocked"))
            self._scanner_status.setProperty("tone", "error")
        self._scanner_status.style().unpolish(self._scanner_status)
        self._scanner_status.style().polish(self._scanner_status)

    def _configure_widgets(self) -> None:
        """Настраивает objectName и переносы текста."""

        self._title.setObjectName("defectHeroTitle")
        self._status.setObjectName("defectStatusText")
        self._scanner_status.setObjectName("defectScannerStatus")
        self._result.setObjectName("defectResult")
        self._error.setObjectName("defectError")
        self._last_code.setObjectName("defectMetaValue")
        self._order.setObjectName("defectMetaValue")
        self._device.setObjectName("defectMetaValue")
        self._removed_box.setObjectName("defectMetaValue")
        self._warnings.setObjectName("defectWarning")
        self._log.setObjectName("defectLog")
        for label in (
            self._status,
            self._result,
            self._error,
            self._last_code,
            self._order,
            self._device,
            self._removed_box,
            self._warnings,
        ):
            label.setWordWrap(True)
        self._error.setVisible(False)
        self._warnings.setVisible(False)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру экрана брака."""

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
        """Создает верхний блок сценария брака."""

        hero = QFrame()
        hero.setObjectName("defectHero")
        icon = VectorIcon(VectorIconName.WARNING, "#f3c969")
        subtitle = QLabel(tr("defect.heroSubtitle"))
        subtitle.setObjectName("defectHeroSubtitle")
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
        card.setObjectName("defectCard")
        title = QLabel(tr("defect.source"))
        title.setObjectName("defectCardTitle")
        note = QLabel(tr("defect.sourceNote"))
        note.setObjectName("defectMutedText")
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
        """Создает карточку результата отправки в брак."""

        card = QFrame()
        card.setObjectName("defectResultCard")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.SHIELD, "#66d2c7"))
        header_text = QVBoxLayout()
        title = QLabel(tr("defect.resultTitle"))
        title.setObjectName("defectCardTitle")
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
        """Создает панель деталей обработанного кода."""

        panel = QFrame()
        panel.setObjectName("defectMetaPanel")
        title = QLabel(tr("defect.details"))
        title.setObjectName("defectCardTitle")
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.addWidget(self._order, 0, 0)
        grid.addWidget(self._device, 0, 1)
        grid.addWidget(self._removed_box, 1, 0, 1, 2)
        grid.addWidget(self._warnings, 2, 0, 1, 2)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addLayout(grid)
        return panel

    def _create_log_panel(self) -> QFrame:
        """Создает журнал последних отправок в брак."""

        panel = QFrame()
        panel.setObjectName("defectLogPanel")
        header = QHBoxLayout()
        title = QLabel(tr("defect.logTitle"))
        title.setObjectName("defectCardTitle")
        hint = QLabel(tr("defect.logHint"))
        hint.setObjectName("defectMutedText")
        text = QVBoxLayout()
        text.addWidget(title)
        text.addWidget(hint)
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header.addLayout(text, 1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._log, 1)
        return panel

    @staticmethod
    def _preview(code: str) -> str:
        """Возвращает компактное отображение кода маркировки."""

        if not code:
            return "-"
        compact = code.strip().replace("\n", "")
        if len(compact) <= 36:
            return compact
        return f"{compact[:18]}...{compact[-12:]}"
