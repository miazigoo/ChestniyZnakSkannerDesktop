"""Контроллер отправки кодов в брак."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.verify import DefectResponseDto
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent


class DefectBackend(Protocol):
    """Контракт backend-сервиса брака."""

    def mark_defect(self, code: str, scanner_id: str) -> DefectResponseDto:
        """Отмечает код как брак."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class DefectUiState:
    """Состояние экрана отправки кода в брак."""

    is_busy: bool = False
    status_message: str = field(default_factory=lambda: tr("defect.waitScan"))
    result_message: str = ""
    error_message: str = ""
    last_visible_code: str = ""
    order_name: str = ""
    device_name: str = ""
    removed_box_message: str = ""
    warnings: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


class DefectController(QObject):
    """Обрабатывает сканы на экране брака."""

    state_changed = Signal(DefectUiState)

    def __init__(
        self,
        defect_service: DefectBackend,
        task_runner: TaskRunner,
        scanner_id: str = "desktop-com-defect",
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер брака."""

        super().__init__(parent)
        self._defect_service = defect_service
        self._task_runner = task_runner
        self._scanner_id = scanner_id
        self._sound_service = sound_service
        self._state = DefectUiState()

    @property
    def state(self) -> DefectUiState:
        """Возвращает текущее состояние брака."""

        return self._state

    def on_code_scanned(self, code: str) -> None:
        """Отправляет скан в backend-сценарий брака."""

        if self._state.is_busy:
            return
        self._set_state(
            DefectUiState(
                is_busy=True,
                status_message=tr("defect.sending"),
                last_visible_code=code,
                log=self._state.log,
            )
        )
        self._task_runner.submit(
            lambda: self._defect_service.mark_defect(code, self._scanner_id),
            self._on_defect_marked,
            self._on_error,
        )

    def clear_state(self) -> None:
        """Полностью очищает данные экрана брака."""

        self._set_state(DefectUiState())

    def _on_defect_marked(self, result: object) -> None:
        """Обрабатывает результат отметки брака."""

        if not isinstance(result, DefectResponseDto):
            raise TypeError("Ожидался результат DefectResponseDto")
        self._play(self._sound_for_result(result))
        result_message = self._result_message(result)
        visible_code = self._visible_code(result) or self._state.last_visible_code
        log = [f"{visible_code}: {result_message}", *self._state.log][:50]
        self._set_state(
            DefectUiState(
                status_message=tr("defect.processed"),
                result_message=result_message,
                error_message="" if result.ok else result_message,
                last_visible_code=visible_code,
                order_name=self._order_name(result),
                device_name=self._device_name(result),
                removed_box_message=self._removed_box_message(result),
                warnings=result.verify.warnings if result.verify is not None else [],
                log=log,
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку backend-сценария брака."""

        self._play(SoundEvent.ERROR)
        log = [f"{self._state.last_visible_code}: {exc}", *self._state.log][:50]
        self._set_state(
            DefectUiState(
                status_message=tr("defect.errorStatus"),
                error_message=str(exc),
                last_visible_code=self._state.last_visible_code,
                log=log,
            )
        )

    def _set_state(self, state: DefectUiState) -> None:
        """Сохраняет и публикует состояние брака."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    @staticmethod
    def _sound_for_result(result: DefectResponseDto) -> SoundEvent:
        """Выбирает звук по результату backend."""

        if result.ok:
            return SoundEvent.WARNING
        if result.reason_code == "scan_rejected":
            return SoundEvent.WARNING
        return SoundEvent.ERROR

    @staticmethod
    def _result_message(result: DefectResponseDto) -> str:
        """Возвращает человекочитаемый текст результата."""

        if result.ok:
            return result.error or tr("defect.sent")
        if result.error:
            return result.error
        if result.verify is not None:
            return result.verify.message
        return tr("defect.failed")

    @staticmethod
    def _visible_code(result: DefectResponseDto) -> str:
        """Возвращает видимый код из результата проверки."""

        if result.verify is None or result.verify.code is None:
            return ""
        return result.verify.code.visible_code

    @staticmethod
    def _order_name(result: DefectResponseDto) -> str:
        """Возвращает заказ из результата проверки."""

        if result.verify is None or result.verify.code is None:
            return ""
        return result.verify.code.order_name or result.verify.code.order_dnp_name

    @staticmethod
    def _device_name(result: DefectResponseDto) -> str:
        """Возвращает устройство из результата проверки."""

        if result.verify is None or result.verify.code is None:
            return ""
        return result.verify.code.device_name

    @staticmethod
    def _removed_box_message(result: DefectResponseDto) -> str:
        """Возвращает текст удаления кода из коробки."""

        if result.removed_from_box is None:
            return ""
        box = result.removed_from_box
        sscc = f" | {box.sscc}" if box.sscc else ""
        return tr("defect.removedLog", box_id=box.box_id, sscc=sscc, filled=box.filled)
