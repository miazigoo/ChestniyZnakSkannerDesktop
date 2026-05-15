"""Контроллер экрана диагностики."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.services.log_service import LogService


@dataclass(frozen=True, slots=True)
class DiagnosticsUiState:
    """Состояние экрана диагностики приложения."""

    api_base_url: str
    websocket_url: str
    device_id: str
    data_dir: str
    log_file: str
    log_text: str = ""
    status_message: str = "Диагностика готова"
    error_message: str = ""


class DiagnosticsController(QObject):
    """Готовит диагностическую информацию и последние строки логов."""

    state_changed = Signal(DiagnosticsUiState)

    def __init__(
        self,
        config: AppConfig,
        log_service: LogService,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер диагностики."""

        super().__init__(parent)
        self._config = config
        self._log_service = log_service
        self._state = self._base_state()

    @property
    def state(self) -> DiagnosticsUiState:
        """Возвращает текущее состояние диагностики."""

        return self._state

    def publish_state(self) -> None:
        """Публикует начальное состояние диагностики."""

        self._set_state(self._state)

    def refresh_logs(self) -> None:
        """Обновляет последние строки лог-файла."""

        try:
            log_text = self._log_service.tail()
        except OSError as exc:
            self._set_state(
                self._base_state(
                    log_text=self._state.log_text,
                    status_message="Ошибка чтения логов",
                    error_message=str(exc),
                )
            )
            return
        self._set_state(
            self._base_state(
                log_text=log_text,
                status_message="Логи обновлены",
            )
        )

    def clear_logs(self) -> None:
        """Очищает лог-файл и обновляет диагностический экран."""

        try:
            self._log_service.clear()
        except OSError as exc:
            self._set_state(
                self._base_state(
                    log_text=self._state.log_text,
                    status_message="Ошибка очистки логов",
                    error_message=str(exc),
                )
            )
            return
        self._set_state(
            self._base_state(
                log_text="",
                status_message="Логи очищены",
            )
        )

    def _base_state(
        self,
        log_text: str = "",
        status_message: str = "Диагностика готова",
        error_message: str = "",
    ) -> DiagnosticsUiState:
        """Создает состояние с неизменяемыми параметрами приложения."""

        return DiagnosticsUiState(
            api_base_url=self._config.api_base_url,
            websocket_url=self._config.websocket_url,
            device_id=self._config.device_id,
            data_dir=str(self._config.data_dir),
            log_file=str(self._log_service.log_file),
            log_text=log_text,
            status_message=status_message,
            error_message=error_message,
        )

    def _set_state(self, state: DiagnosticsUiState) -> None:
        """Сохраняет и публикует состояние диагностики."""

        self._state = state
        self.state_changed.emit(state)
