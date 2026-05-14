"""Контроллер списка коробок."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import BoxDto, BoxListDto
from chestniy_znak_desktop.runtime.task_runner import TaskRunner


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
    status_message: str = "Загрузите список коробок"
    error_message: str = ""

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
        task_runner: TaskRunner,
        page_limit: int = 50,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер списка коробок."""

        super().__init__(parent)
        self._boxes_service = boxes_service
        self._task_runner = task_runner
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

    def _load_page(self, offset: int) -> None:
        """Запускает загрузку страницы коробок."""

        status_filter = self._state.status_filter
        query = self._state.query
        limit = self._state.limit
        self._set_state(
            BoxesUiState(
                is_busy=True,
                status_filter=status_filter,
                query=query,
                limit=limit,
                offset=offset,
                total=self._state.total,
                rows=self._state.rows,
                status_message="Загружаем коробки...",
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
        self._set_state(
            BoxesUiState(
                status_filter=self._state.status_filter,
                query=self._state.query,
                limit=result.limit,
                offset=result.offset,
                total=result.total,
                has_more=result.has_more,
                rows=[self._box_to_row(box) for box in result.items],
                status_message="Коробки загружены",
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку загрузки списка коробок."""

        self._set_state(
            BoxesUiState(
                status_filter=self._state.status_filter,
                query=self._state.query,
                limit=self._state.limit,
                offset=self._state.offset,
                total=self._state.total,
                has_more=self._state.has_more,
                rows=self._state.rows,
                status_message="Ошибка загрузки коробок",
                error_message=str(exc),
            )
        )

    def _set_state(self, state: BoxesUiState) -> None:
        """Сохраняет и публикует состояние списка коробок."""

        self._state = state
        self.state_changed.emit(state)

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
    def _print_status(box: BoxDto) -> str:
        """Возвращает человекочитаемый статус печати."""

        if box.print_ok:
            return "Напечатано"
        if box.print_error:
            return box.print_error
        return "-"
