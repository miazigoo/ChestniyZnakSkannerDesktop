"""Контроллер редактирования коробки."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import BoxActionResultDto
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent


class BoxEditBackend(Protocol):
    """Контракт backend-сервиса редактирования коробки."""

    def open_edit(self, box_id: int, reason: str = "") -> BoxActionResultDto:
        """Открывает коробку в режиме редактирования."""

    def close_edit(self, box_id: int) -> BoxActionResultDto:
        """Закрывает режим редактирования коробки."""

    def remove_item(self, box_id: int, item_id: int) -> BoxActionResultDto:
        """Удаляет один код из коробки."""

    def clear_box(self, box_id: int) -> BoxActionResultDto:
        """Очищает коробку."""

    def delete_empty_box(self, box_id: int) -> BoxActionResultDto:
        """Удаляет пустую коробку."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class BoxEditUiState:
    """Состояние действий редактирования коробки."""

    is_busy: bool = False
    status_message: str = "Редактирование не запущено"
    error_message: str = ""


class BoxEditController(QObject):
    """Выполняет действия режима редактирования выбранной коробки."""

    state_changed = Signal(BoxEditUiState)
    box_changed = Signal(int)
    box_deleted = Signal(int)

    def __init__(
        self,
        edit_service: BoxEditBackend,
        task_runner: TaskRunner,
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер редактирования коробки."""

        super().__init__(parent)
        self._edit_service = edit_service
        self._task_runner = task_runner
        self._sound_service = sound_service
        self._state = BoxEditUiState()
        self._current_action_box_id: int | None = None
        self._delete_action = False

    @property
    def state(self) -> BoxEditUiState:
        """Возвращает текущее состояние редактирования."""

        return self._state

    def open_edit(self, box_id: int, reason: str = "") -> None:
        """Открывает выбранную коробку в режиме редактирования."""

        self._submit_box_action(
            box_id=box_id,
            message=f"Открываем редактирование коробки #{box_id}...",
            task=lambda: self._edit_service.open_edit(box_id, reason),
        )

    def close_edit(self, box_id: int) -> None:
        """Закрывает режим редактирования выбранной коробки."""

        self._submit_box_action(
            box_id=box_id,
            message=f"Закрываем редактирование коробки #{box_id}...",
            task=lambda: self._edit_service.close_edit(box_id),
        )

    def remove_item(self, box_id: int, item_id: int) -> None:
        """Удаляет выбранный код из коробки."""

        self._submit_box_action(
            box_id=box_id,
            message=f"Удаляем код #{item_id} из коробки #{box_id}...",
            task=lambda: self._edit_service.remove_item(box_id, item_id),
        )

    def clear_box(self, box_id: int) -> None:
        """Очищает выбранную коробку."""

        self._submit_box_action(
            box_id=box_id,
            message=f"Очищаем коробку #{box_id}...",
            task=lambda: self._edit_service.clear_box(box_id),
        )

    def delete_empty_box(self, box_id: int) -> None:
        """Удаляет выбранную пустую коробку."""

        self._submit_box_action(
            box_id=box_id,
            message=f"Удаляем пустую коробку #{box_id}...",
            task=lambda: self._edit_service.delete_empty_box(box_id),
            delete_action=True,
        )

    def _submit_box_action(
        self,
        box_id: int,
        message: str,
        task: Callable[[], BoxActionResultDto],
        delete_action: bool = False,
    ) -> None:
        """Запускает действие редактирования коробки."""

        if self._state.is_busy:
            return
        self._current_action_box_id = box_id
        self._delete_action = delete_action
        self._set_state(BoxEditUiState(is_busy=True, status_message=message))
        self._task_runner.submit(task, self._on_action_finished, self._on_action_error)

    def _on_action_finished(self, result: object) -> None:
        """Обрабатывает результат действия редактирования."""

        if not isinstance(result, BoxActionResultDto):
            raise TypeError("Ожидался результат BoxActionResultDto")
        message = result.error or self._status_for_reason(result.reason_code)
        self._play(SoundEvent.OK if result.ok else SoundEvent.ERROR)
        self._set_state(
            BoxEditUiState(
                status_message=message,
                error_message="" if result.ok else message,
            )
        )
        if result.ok and self._current_action_box_id is not None:
            if self._delete_action and result.removed:
                self.box_deleted.emit(self._current_action_box_id)
                return
            self.box_changed.emit(self._current_action_box_id)

    def _on_action_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку действия редактирования."""

        self._play(SoundEvent.ERROR)
        self._set_state(
            BoxEditUiState(
                status_message="Ошибка редактирования коробки",
                error_message=str(exc),
            )
        )

    def _set_state(self, state: BoxEditUiState) -> None:
        """Сохраняет и публикует состояние редактирования."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    @staticmethod
    def _status_for_reason(reason_code: str) -> str:
        """Возвращает текст статуса по backend reason_code."""

        messages = {
            "edit_opened": "Редактирование открыто",
            "edit_already_open": "Редактирование уже открыто",
            "box_already_open": "Коробка уже открыта",
            "edit_closed": "Редактирование закрыто",
            "edit_already_closed": "Редактирование уже закрыто",
            "item_removed": "Код удален из коробки",
            "box_cleared": "Коробка очищена",
            "empty_box_deleted": "Пустая коробка удалена",
        }
        return messages.get(reason_code, reason_code)
