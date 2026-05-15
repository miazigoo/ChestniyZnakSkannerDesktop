"""Контроллер списка коробок."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import (
    BoxDetailDto,
    BoxDto,
    BoxListDto,
    CloseBoxResultDto,
)
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent


class BoxesBackend(Protocol):
    """Контракт backend-сервиса для списка коробок."""

    def list_boxes(
        self,
        status: str = "all",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> BoxListDto:
        """Возвращает страницу коробок."""

    def get_box(self, box_id: int) -> BoxDetailDto:
        """Возвращает детальную карточку коробки."""


class PrinterBackend(Protocol):
    """Контракт сервиса повторной печати этикеток."""

    def print_box_label(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Печатает этикетку коробки."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class BoxRowUi:
    """UI-модель строки таблицы коробок."""

    box_id: int
    order_name: str
    sscc: str
    filled: str
    status: str
    operator: str
    print_status: str


@dataclass(frozen=True, slots=True)
class BoxDetailItemUi:
    """UI-модель кода внутри выбранной коробки."""

    id: int
    gtin: str
    serial: str
    visible_code: str


@dataclass(frozen=True, slots=True)
class BoxDetailUi:
    """UI-модель детальной карточки выбранной коробки."""

    box_id: int
    order_name: str
    sscc: str
    filled: int
    capacity: int
    status: str
    count_in_packing: str
    operator: str
    print_status: str
    items: list[BoxDetailItemUi] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoxesUiState:
    """Состояние экрана списка коробок."""

    is_busy: bool = False
    status_filter: str = "all"
    query: str = ""
    limit: int = 50
    offset: int = 0
    total: int = 0
    has_more: bool = False
    rows: list[BoxRowUi] = field(default_factory=list)
    selected_box_id: int | None = None
    detail: BoxDetailUi | None = None
    is_detail_busy: bool = False
    is_action_busy: bool = False
    status_message: str = "Загрузите список коробок"
    error_message: str = ""
    detail_status_message: str = "Выберите коробку для просмотра состава"
    detail_error_message: str = ""

    @property
    def page_title(self) -> str:
        """Возвращает текст текущей страницы."""

        if self.total == 0:
            return "0 / 0"
        first_item = self.offset + 1
        last_item = min(self.offset + len(self.rows), self.total)
        return f"{first_item}-{last_item} / {self.total}"

    @property
    def has_previous(self) -> bool:
        """Возвращает `True`, если есть предыдущая страница."""

        return self.offset > 0


class BoxesController(QObject):
    """Загружает и фильтрует список коробок."""

    state_changed = Signal(BoxesUiState)

    def __init__(
        self,
        boxes_service: BoxesBackend,
        printer_service: PrinterBackend,
        task_runner: TaskRunner,
        device_id: str,
        page_limit: int = 50,
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер списка коробок."""

        super().__init__(parent)
        self._boxes_service = boxes_service
        self._printer_service = printer_service
        self._task_runner = task_runner
        self._device_id = device_id
        self._sound_service = sound_service
        self._state = BoxesUiState(limit=page_limit)

    @property
    def state(self) -> BoxesUiState:
        """Возвращает текущее состояние списка коробок."""

        return self._state

    def refresh(self) -> None:
        """Перезагружает текущую страницу коробок."""

        if self._state.is_busy:
            return
        self._load_page(self._state.offset)

    def set_status_filter(self, status_filter: str) -> None:
        """Меняет фильтр статуса и загружает первую страницу."""

        self._set_state(
            BoxesUiState(
                status_filter=status_filter,
                query=self._state.query,
                limit=self._state.limit,
                status_message=self._state.status_message,
            )
        )
        self._load_page(0)

    def set_query(self, query: str) -> None:
        """Меняет поисковую строку и загружает первую страницу."""

        self._set_state(
            BoxesUiState(
                status_filter=self._state.status_filter,
                query=query.strip(),
                limit=self._state.limit,
                status_message=self._state.status_message,
            )
        )
        self._load_page(0)

    def next_page(self) -> None:
        """Загружает следующую страницу, если она есть."""

        if self._state.is_busy or not self._state.has_more:
            return
        self._load_page(self._state.offset + self._state.limit)

    def previous_page(self) -> None:
        """Загружает предыдущую страницу, если она есть."""

        if self._state.is_busy or not self._state.has_previous:
            return
        self._load_page(max(0, self._state.offset - self._state.limit))

    def load_detail(self, box_id: int) -> None:
        """Загружает детальную карточку выбранной коробки."""

        if self._state.is_detail_busy:
            return
        self._set_state(
            BoxesUiState(
                status_filter=self._state.status_filter,
                query=self._state.query,
                limit=self._state.limit,
                offset=self._state.offset,
                total=self._state.total,
                has_more=self._state.has_more,
                rows=self._state.rows,
                selected_box_id=box_id,
                detail=self._state.detail,
                is_detail_busy=True,
                status_message=self._state.status_message,
                detail_status_message=f"Загружаем коробку #{box_id}...",
            )
        )
        self._task_runner.submit(
            lambda: self._boxes_service.get_box(box_id),
            self._on_detail_loaded,
            self._on_detail_error,
        )

    def clear_detail(self, message: str = "Выберите коробку для просмотра состава") -> None:
        """Сбрасывает выбранную коробку и правую панель состава."""

        self._set_state(
            replace(
                self._state,
                selected_box_id=None,
                detail=None,
                is_detail_busy=False,
                detail_status_message=message,
                detail_error_message="",
            )
        )

    def print_selected_label(self, box_id: int) -> None:
        """Запускает повторную печать этикетки выбранной коробки."""

        if self._state.is_action_busy:
            return
        self._set_state(
            replace(
                self._state,
                selected_box_id=box_id,
                is_action_busy=True,
                detail_status_message=f"Печатаем этикетку коробки #{box_id}...",
                detail_error_message="",
            )
        )
        self._task_runner.submit(
            lambda: self._printer_service.print_box_label(box_id, self._device_id),
            self._on_label_printed,
            self._on_print_error,
        )

    def _load_page(self, offset: int) -> None:
        """Запускает загрузку страницы коробок."""

        status_filter = self._state.status_filter
        query = self._state.query
        limit = self._state.limit
        self._set_state(
            replace(
                self._state,
                is_busy=True,
                offset=offset,
                status_message="Загружаем коробки...",
                error_message="",
            )
        )
        self._task_runner.submit(
            lambda: self._boxes_service.list_boxes(
                status=status_filter,
                query=query,
                limit=limit,
                offset=offset,
            ),
            self._on_boxes_loaded,
            self._on_error,
        )

    def _on_boxes_loaded(self, result: object) -> None:
        """Обрабатывает загруженную страницу коробок."""

        if not isinstance(result, BoxListDto):
            raise TypeError("Ожидался результат BoxListDto")
        rows = [self._box_to_row(box) for box in result.items]
        row_ids = {row.box_id for row in rows}
        selected_box_id = self._state.selected_box_id
        selected_exists = selected_box_id is not None and selected_box_id in row_ids
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_filter=self._state.status_filter,
                query=self._state.query,
                limit=result.limit,
                offset=result.offset,
                total=result.total,
                has_more=result.has_more,
                rows=rows,
                selected_box_id=selected_box_id if selected_exists else None,
                detail=self._state.detail if selected_exists else None,
                status_message="Коробки загружены",
                error_message="",
                detail_status_message=(
                    self._state.detail_status_message
                    if selected_exists
                    else "Выберите коробку для просмотра состава"
                ),
                detail_error_message=self._state.detail_error_message if selected_exists else "",
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку загрузки списка коробок."""

        self._set_state(
            replace(
                self._state,
                is_busy=False,
                selected_box_id=self._state.selected_box_id,
                detail=self._state.detail,
                status_message="Ошибка загрузки коробок",
                error_message=str(exc),
            )
        )

    def _on_detail_loaded(self, result: object) -> None:
        """Обрабатывает загруженную детальную карточку коробки."""

        if not isinstance(result, BoxDetailDto):
            raise TypeError("Ожидался результат BoxDetailDto")
        self._set_state(
            replace(
                self._state,
                is_detail_busy=False,
                selected_box_id=result.box_id,
                detail=self._box_detail_to_ui(result),
                detail_status_message=f"Коробка #{result.box_id} загружена",
                detail_error_message="",
            )
        )

    def _on_detail_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку загрузки выбранной коробки."""

        self._set_state(
            replace(
                self._state,
                is_detail_busy=False,
                detail=None,
                detail_status_message="Ошибка загрузки коробки",
                detail_error_message=str(exc),
            )
        )

    def _on_label_printed(self, result: object) -> None:
        """Обрабатывает результат повторной печати этикетки."""

        if not isinstance(result, CloseBoxResultDto):
            raise TypeError("Ожидался результат CloseBoxResultDto")
        self._play(SoundEvent.OK if result.ok and result.print_ok else SoundEvent.ERROR)
        error_message = result.error or result.print_error or ""
        detail = self._update_detail_print_status(result)
        self._set_state(
            replace(
                self._state,
                is_action_busy=False,
                detail=detail,
                detail_status_message=(
                    "Этикетка отправлена на печать"
                    if result.ok and result.print_ok
                    else "Печать не выполнена"
                ),
                detail_error_message=error_message,
            )
        )

    def _on_print_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку повторной печати этикетки."""

        self._play(SoundEvent.ERROR)
        self._set_state(
            replace(
                self._state,
                is_action_busy=False,
                detail_status_message="Ошибка печати",
                detail_error_message=str(exc),
            )
        )

    def _set_state(self, state: BoxesUiState) -> None:
        """Сохраняет и публикует состояние списка коробок."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    def _update_detail_print_status(self, result: CloseBoxResultDto) -> BoxDetailUi | None:
        """Обновляет статус печати в уже загруженной детальной карточке."""

        if self._state.detail is None:
            return None
        return replace(
            self._state.detail,
            print_status=self._print_status(result.box),
        )

    @staticmethod
    def _box_to_row(box: BoxDto) -> BoxRowUi:
        """Преобразует DTO коробки в строку таблицы."""

        return BoxRowUi(
            box_id=box.box_id,
            order_name=box.order_name or "-",
            sscc=box.sscc or "-",
            filled=f"{box.filled} / {box.capacity}",
            status="Закрыта" if box.is_closed else "Открыта",
            operator=box.active_user_name or box.created_by_name or "-",
            print_status=BoxesController._print_status(box),
        )

    @staticmethod
    def _box_detail_to_ui(box: BoxDetailDto) -> BoxDetailUi:
        """Преобразует детальную DTO коробки в UI-модель."""

        return BoxDetailUi(
            box_id=box.box_id,
            order_name=box.order_name or "-",
            sscc=box.sscc or "-",
            filled=box.filled,
            capacity=box.capacity,
            status="Закрыта" if box.is_closed else "Открыта",
            count_in_packing="Да" if box.count_in_packing else "Нет",
            operator=box.active_user_name or box.created_by_name or "-",
            print_status=BoxesController._print_status(box),
            items=[
                BoxDetailItemUi(
                    id=item.id,
                    gtin=item.gtin,
                    serial=item.serial,
                    visible_code=item.visible_code,
                )
                for item in box.items
            ],
        )

    @staticmethod
    def _print_status(box: BoxDto) -> str:
        """Возвращает человекочитаемый статус печати."""

        if box.print_ok:
            return "Напечатано"
        if box.print_error:
            return box.print_error
        return "-"
