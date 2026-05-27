"""Контроллер поиска коробки по скану."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import BoxDto, BoxListDto
from chestniy_znak_desktop.domain.box_lookup import build_box_lookup_candidates
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent


class BoxLookupBackend(Protocol):
    """Контракт backend-сервиса списка коробок."""

    def list_boxes(
        self,
        status: str = "all",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> BoxListDto:
        """Возвращает страницу коробок по строке поиска."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class BoxLookupUiState:
    """Состояние экрана поиска коробки."""

    is_busy: bool = False
    status_message: str = field(default_factory=lambda: tr("lookup.scanBox"))
    error_message: str = ""
    last_scanned_code: str = ""
    found_box_id: int | None = None
    found_box_summary: str = ""
    log: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoxLookupResult:
    """Внутренний результат поиска коробки."""

    scanned_code: str
    box: BoxDto | None


class BoxLookupController(QObject):
    """Обрабатывает сканы на экране поиска коробки."""

    state_changed = Signal(BoxLookupUiState)
    box_found = Signal(int)

    def __init__(
        self,
        boxes_service: BoxLookupBackend,
        task_runner: TaskRunner,
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер поиска коробки."""

        super().__init__(parent)
        self._boxes_service = boxes_service
        self._task_runner = task_runner
        self._sound_service = sound_service
        self._state = BoxLookupUiState()

    @property
    def state(self) -> BoxLookupUiState:
        """Возвращает текущее состояние поиска."""

        return self._state

    def on_code_scanned(self, code: str) -> None:
        """Запускает поиск коробки по входящему скану."""

        normalized = code.strip()
        if self._state.is_busy or not normalized:
            return
        self._set_state(
            BoxLookupUiState(
                is_busy=True,
                status_message=tr("lookup.searching"),
                last_scanned_code=normalized,
                log=self._state.log,
            )
        )
        self._task_runner.submit(
            lambda: self._find_box(normalized),
            self._on_lookup_finished,
            self._on_error,
        )

    def reset_status(self) -> None:
        """Сбрасывает статус последнего поиска."""

        self._set_state(BoxLookupUiState(log=self._state.log))

    def clear_state(self) -> None:
        """Полностью очищает данные экрана поиска коробки."""

        self._set_state(BoxLookupUiState())

    def _find_box(self, code: str) -> BoxLookupResult:
        """Ищет коробку по всем кандидатам из скана."""

        for candidate in build_box_lookup_candidates(code):
            page = self._boxes_service.list_boxes(query=candidate, limit=10)
            exact = next(
                (
                    box
                    for box in page.items
                    if box.sscc == candidate or str(box.box_id) == candidate
                ),
                None,
            )
            if exact is not None:
                return BoxLookupResult(scanned_code=code, box=exact)
            if page.items:
                return BoxLookupResult(scanned_code=code, box=page.items[0])
        return BoxLookupResult(scanned_code=code, box=None)

    def _on_lookup_finished(self, result: object) -> None:
        """Обрабатывает результат поиска коробки."""

        if not isinstance(result, BoxLookupResult):
            raise TypeError("Ожидался результат BoxLookupResult")
        if result.box is None:
            self._play(SoundEvent.ERROR)
            log = [
                tr("lookup.notFoundLog", code=result.scanned_code),
                *self._state.log,
            ][:50]
            self._set_state(
                BoxLookupUiState(
                    status_message=tr("lookup.notFound"),
                    error_message=tr("lookup.notFound"),
                    last_scanned_code=result.scanned_code,
                    log=log,
                )
            )
            return

        self._play(SoundEvent.OK)
        summary = self._box_summary(result.box)
        log = [f"{result.scanned_code}: {summary}", *self._state.log][:50]
        self._set_state(
            BoxLookupUiState(
                status_message=tr("lookup.foundStatus", box_id=result.box.box_id),
                last_scanned_code=result.scanned_code,
                found_box_id=result.box.box_id,
                found_box_summary=summary,
                log=log,
            )
        )
        self.box_found.emit(result.box.box_id)

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку поиска коробки."""

        self._play(SoundEvent.ERROR)
        log = [f"{self._state.last_scanned_code}: {exc}", *self._state.log][:50]
        self._set_state(
            BoxLookupUiState(
                status_message=tr("lookup.errorStatus"),
                error_message=str(exc),
                last_scanned_code=self._state.last_scanned_code,
                log=log,
            )
        )

    def _set_state(self, state: BoxLookupUiState) -> None:
        """Сохраняет и публикует состояние поиска."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    @staticmethod
    def _box_summary(box: BoxDto) -> str:
        """Формирует краткое описание найденной коробки."""

        sscc = box.sscc or tr("lookup.ssccMissing")
        order = box.order_name or tr("lookup.noOrder")
        return f"#{box.box_id} | {order} | {sscc} | {box.filled}/{box.capacity}"
