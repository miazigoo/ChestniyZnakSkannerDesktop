"""Контроллер проверки DataMatrix-кодов."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.verify import VerifyExistsResponseDto
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent

VERIFY_LOG_LIMIT = 30


class VerifyBackend(Protocol):
    """Контракт backend-сервиса проверки кодов."""

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
    ) -> VerifyExistsResponseDto:
        """Проверяет наличие кода в базе."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class VerifyUiState:
    """Состояние экрана проверки DataMatrix-кода."""

    is_busy: bool = False
    status_message: str = field(default_factory=lambda: tr("verify.waitScan"))
    result_message: str = ""
    error_message: str = ""
    last_visible_code: str = ""
    technical_status: str = ""
    order_name: str = ""
    device_name: str = ""
    exists: bool | None = None
    check_duplicates: bool = False
    warnings: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class VerifyController(QObject):
    """Обрабатывает сканы на экране проверки кодов."""

    state_changed = Signal(VerifyUiState)

    def __init__(
        self,
        verify_service: VerifyBackend,
        task_runner: TaskRunner,
        scanner_id: str = "desktop-com-verify",
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер проверки кодов."""

        super().__init__(parent)
        self._verify_service = verify_service
        self._task_runner = task_runner
        self._scanner_id = scanner_id
        self._sound_service = sound_service
        self._state = VerifyUiState()

    @property
    def state(self) -> VerifyUiState:
        """Возвращает текущее состояние проверки."""

        return self._state

    def on_code_scanned(self, code: str) -> None:
        """Отправляет отсканированный код на проверку."""

        if self._state.is_busy:
            return
        check_duplicates = self._state.check_duplicates
        allow_duplicate = not check_duplicates
        self._set_state(
            VerifyUiState(
                is_busy=True,
                status_message=tr("verify.checking"),
                last_visible_code=code,
                check_duplicates=check_duplicates,
                log=self._state.log,
            )
        )
        self._task_runner.submit(
            lambda: self._verify_service.verify_exists(
                code,
                self._scanner_id,
                allow_duplicate=allow_duplicate,
            ),
            self._on_code_verified,
            self._on_error,
        )

    def set_check_duplicates(self, enabled: bool) -> None:
        """Включает или отключает учет дублей при проверке."""

        if self._state.check_duplicates == enabled:
            return
        self._set_state(replace(self._state, check_duplicates=enabled))

    def _on_code_verified(self, result: object) -> None:
        """Обрабатывает результат проверки кода."""

        if not isinstance(result, VerifyExistsResponseDto):
            raise TypeError("Ожидался результат VerifyExistsResponseDto")
        self._play(SoundEvent.OK if result.ok else SoundEvent.ERROR)
        visible_code = self._visible_code(result) or self._state.last_visible_code
        result_message = self._result_message(result)
        log = self._prepend_log(f"{visible_code}: {result_message}")
        self._set_state(
            VerifyUiState(
                status_message=tr("verify.processed"),
                result_message=result_message,
                error_message="" if result.ok else result_message,
                last_visible_code=visible_code,
                technical_status=result.status,
                order_name=self._order_name(result),
                device_name=self._device_name(result),
                exists=result.exists,
                check_duplicates=self._state.check_duplicates,
                warnings=result.warnings,
                log=log,
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку проверки кода."""

        self._play(SoundEvent.ERROR)
        log = self._prepend_log(f"{self._state.last_visible_code}: {exc}")
        self._set_state(
            VerifyUiState(
                status_message=tr("verify.errorStatus"),
                error_message=str(exc),
                last_visible_code=self._state.last_visible_code,
                check_duplicates=self._state.check_duplicates,
                log=log,
            )
        )

    def _set_state(self, state: VerifyUiState) -> None:
        """Сохраняет и публикует состояние проверки."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    def _prepend_log(self, message: str) -> list[str]:
        """Добавляет запись в журнал, оставляя только последние события."""

        return [message, *self._state.log][:VERIFY_LOG_LIMIT]

    @staticmethod
    def _result_message(result: VerifyExistsResponseDto) -> str:
        """Возвращает человекочитаемый результат проверки."""

        if result.ok:
            return result.message or tr("verify.found")
        return result.message or tr("verify.notFound")

    @staticmethod
    def _visible_code(result: VerifyExistsResponseDto) -> str:
        """Возвращает видимый код из результата проверки."""

        if result.code is None:
            return ""
        return result.code.visible_code

    @staticmethod
    def _order_name(result: VerifyExistsResponseDto) -> str:
        """Возвращает заказ из результата проверки."""

        if result.order_name:
            return result.order_name
        if result.code is None:
            return ""
        return result.code.order_name or result.code.order_dnp_name

    @staticmethod
    def _device_name(result: VerifyExistsResponseDto) -> str:
        """Возвращает устройство из результата проверки."""

        if result.device_name:
            return result.device_name
        if result.code is None:
            return ""
        return result.code.device_name
