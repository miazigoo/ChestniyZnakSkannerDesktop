"""Экран диагностики приложения."""

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

from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsUiState
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName


class DiagnosticsScreen(QWidget):
    """Показывает runtime-состояние, конфигурацию и последние логи."""

    logs_refresh_requested = Signal()
    logs_clear_requested = Signal()

    def __init__(self) -> None:
        """Создает современный экран диагностики."""

        super().__init__()
        self.setObjectName("diagnosticsScreen")
        self._title = QLabel("Диагностика")
        self._status = QLabel("Диагностика готова")
        self._error = QLabel("")
        self._backend_value = QLabel("-")
        self._websocket_value = QLabel("-")
        self._device_value = QLabel("-")
        self._data_dir_value = QLabel("-")
        self._connection_value = QLabel("-")
        self._session_value = QLabel("-")
        self._scanner_value = QLabel("-")
        self._log_path = QLabel("Лог: -")
        self._refresh_button = QPushButton("Обновить логи")
        self._clear_button = QPushButton("Очистить логи")
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)

        self._configure_widgets()
        self._build_layout()

    def apply_state(self, state: DiagnosticsUiState) -> None:
        """Обновляет статическую диагностику и логи."""

        self._status.setText(state.status_message)
        self._error.setText(state.error_message)
        self._error.setVisible(bool(state.error_message))
        self._backend_value.setText(state.api_base_url)
        self._websocket_value.setText(state.websocket_url)
        self._device_value.setText(state.device_id)
        self._data_dir_value.setText(state.data_dir)
        self._log_path.setText(f"Лог: {state.log_file}")
        self._log_view.setPlainText(state.log_text)

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет runtime-состояние приложения."""

        self._connection_value.setText(
            f"{snapshot.connection.status.value} | {snapshot.connection.message}"
        )
        self._session_value.setText(
            f"{snapshot.session.status.value} | {snapshot.session.user_name or '-'}"
        )
        self._scanner_value.setText(
            (
                f"{snapshot.scanner.status.value} | "
                f"{snapshot.scanner.port or '-'} | {snapshot.scanner.message}"
            )
        )

    def _configure_widgets(self) -> None:
        """Настраивает objectName, переносы и сигналы."""

        self._title.setObjectName("diagnosticsHeroTitle")
        self._status.setObjectName("diagnosticsStatusText")
        self._error.setObjectName("diagnosticsErrorText")
        self._log_path.setObjectName("diagnosticsMutedText")
        self._refresh_button.setObjectName("diagnosticsPrimaryButton")
        self._clear_button.setObjectName("diagnosticsDangerButton")
        self._log_view.setObjectName("diagnosticsLog")
        self._refresh_button.clicked.connect(self.logs_refresh_requested.emit)
        self._clear_button.clicked.connect(self.logs_clear_requested.emit)
        for label in (
            self._status,
            self._error,
            self._backend_value,
            self._websocket_value,
            self._device_value,
            self._data_dir_value,
            self._connection_value,
            self._session_value,
            self._scanner_value,
            self._log_path,
        ):
            label.setWordWrap(True)
        self._error.setVisible(False)

    def _build_layout(self) -> None:
        """Собирает визуальную структуру диагностики."""

        hero = self._create_hero()
        config_panel = self._create_config_panel()
        runtime_panel = self._create_runtime_panel()
        logs_panel = self._create_logs_panel()

        cards = QGridLayout()
        cards.setSpacing(18)
        cards.addWidget(config_panel, 0, 0)
        cards.addWidget(runtime_panel, 0, 1)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(hero)
        layout.addLayout(cards)
        layout.addWidget(logs_panel, 1)

    def _create_hero(self) -> QFrame:
        """Создает верхний блок диагностики."""

        hero = QFrame()
        hero.setObjectName("diagnosticsHero")
        icon = VectorIcon(VectorIconName.DIAGNOSTICS, "#66d2c7")
        subtitle = QLabel("Состояние backend, WebSocket, сессии, сканера и последние строки логов.")
        subtitle.setObjectName("diagnosticsHeroSubtitle")
        subtitle.setWordWrap(True)
        text = QVBoxLayout()
        text.addWidget(self._title)
        text.addWidget(subtitle)

        status_block = QVBoxLayout()
        status_block.addWidget(self._status)
        status_block.addWidget(self._error)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)
        layout.addWidget(icon)
        layout.addLayout(text, 1)
        layout.addLayout(status_block, 1)
        return hero

    def _create_config_panel(self) -> QFrame:
        """Создает панель параметров приложения."""

        panel = QFrame()
        panel.setObjectName("diagnosticsPanel")
        header = self._create_panel_header(
            icon_name=VectorIconName.SETTINGS,
            icon_color="#8fb8ff",
            title="Конфигурация",
            subtitle="Параметры, с которыми запущено приложение",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        self._add_row(grid, 0, "Backend", self._backend_value)
        self._add_row(grid, 1, "WebSocket", self._websocket_value)
        self._add_row(grid, 2, "Device ID", self._device_value)
        self._add_row(grid, 3, "Data dir", self._data_dir_value)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addLayout(grid)
        return panel

    def _create_runtime_panel(self) -> QFrame:
        """Создает панель runtime-состояния."""

        panel = QFrame()
        panel.setObjectName("diagnosticsPanel")
        header = self._create_panel_header(
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
            title="Runtime",
            subtitle="Текущее состояние соединения, сессии и сканера",
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)
        self._add_row(grid, 0, "Связь", self._connection_value)
        self._add_row(grid, 1, "Сессия", self._session_value)
        self._add_row(grid, 2, "Сканер", self._scanner_value)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addLayout(grid)
        return panel

    def _create_logs_panel(self) -> QFrame:
        """Создает панель просмотра логов."""

        panel = QFrame()
        panel.setObjectName("diagnosticsLogsPanel")
        header = QHBoxLayout()
        header.addWidget(VectorIcon(VectorIconName.TOKEN, "#f3c969"))
        header_text = QVBoxLayout()
        title = QLabel("Логи")
        title.setObjectName("diagnosticsPanelTitle")
        header_text.addWidget(title)
        header_text.addWidget(self._log_path)
        header.addLayout(header_text, 1)
        header.addWidget(self._refresh_button)
        header.addWidget(self._clear_button)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addWidget(self._log_view, 1)
        return panel

    @staticmethod
    def _create_panel_header(
        *,
        icon_name: VectorIconName,
        icon_color: str,
        title: str,
        subtitle: str,
    ) -> QHBoxLayout:
        """Создает заголовок диагностической панели."""

        header = QHBoxLayout()
        header.addWidget(VectorIcon(icon_name, icon_color))
        text = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("diagnosticsPanelTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("diagnosticsMutedText")
        subtitle_label.setWordWrap(True)
        text.addWidget(title_label)
        text.addWidget(subtitle_label)
        header.addLayout(text, 1)
        return header

    @staticmethod
    def _add_row(
        grid: QGridLayout,
        row: int,
        title: str,
        value: QLabel,
    ) -> None:
        """Добавляет строку диагностического параметра."""

        title_label = QLabel(title)
        title_label.setObjectName("diagnosticsMetaTitle")
        value.setObjectName("diagnosticsMetaValue")
        value.setWordWrap(True)
        grid.addWidget(title_label, row, 0)
        grid.addWidget(value, row, 1)
