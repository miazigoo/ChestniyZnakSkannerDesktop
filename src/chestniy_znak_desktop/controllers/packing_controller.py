"""Контроллер рабочего сценария упаковки."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxDto,
    BoxItemDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent

TPackingResult = TypeVar("TPackingResult")


class PackingBackend(Protocol):
    """Контракт backend-сервиса упаковки."""

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую открытую коробку."""

    def open_box(self, device_id: str, count_in_packing: bool = True) -> OpenBoxResultDto:
        """Открывает новую коробку."""

    def scan_to_box(self, box_id: int, code: str, scanner_id: str) -> ScanToBoxResultDto:
        """Добавляет код в коробку."""

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает коробку."""

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Переключает учет коробки в упаковке."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class PackingItemUi:
    """UI-модель одного кода внутри коробки."""

    id: int
    gtin: str
    serial: str
    visible_code: str
    code_id: int = 0


@dataclass(frozen=True, slots=True)
class PackingBoxUi:
    """UI-модель текущей коробки."""

    box_id: int
    order_name: str
    sscc: str
    filled: int
    capacity: int
    count_in_packing: bool
    is_closed: bool
    print_ok: bool
    print_error: str
    items: list[PackingItemUi] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PackingUiState:
    """Состояние экрана упаковки."""

    is_busy: bool = False
    current_box: PackingBoxUi | None = None
    status_message: str = "Открытая коробка не найдена"
    result_message: str = ""
    error_message: str = ""
    last_scanned_code: str = ""
    count_in_packing: bool = True


@dataclass(frozen=True, slots=True)
class CloseBoxUiEvent:
    """Итог закрытия коробки для пользовательской модалки."""

    ok: bool
    box_id: int
    sscc: str
    filled: int
    capacity: int
    is_full: bool
    title: str
    message: str
    error_message: str = ""
    print_ok: bool | None = None
    print_error: str = ""


class PackingController(QObject):
    """Связывает экран упаковки, backend и сканер."""

    state_changed = Signal(PackingUiState)
    close_completed = Signal(CloseBoxUiEvent)

    def __init__(
        self,
        packing_service: PackingBackend,
        task_runner: TaskRunner,
        device_id: str,
        scanner_id: str = "desktop-com",
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер упаковки."""

        super().__init__(parent)
        self._packing_service = packing_service
        self._task_runner = task_runner
        self._device_id = device_id
        self._scanner_id = scanner_id
        self._sound_service = sound_service
        self._state = PackingUiState()

    @property
    def state(self) -> PackingUiState:
        """Возвращает текущее состояние экрана упаковки."""

        return self._state

    def refresh_current_box(self) -> None:
        """Загружает текущую открытую коробку пользователя."""

        self._set_busy("Загружаем текущую коробку...")
        self._task_runner.submit(
            self._packing_service.current_box,
            self._on_current_box_loaded,
            self._on_error,
        )

    def open_box(self) -> None:
        """Открывает новую коробку для сканирования."""

        if self._state.is_busy:
            return
        self._set_busy("Открываем коробку...")
        count_in_packing = self._state.count_in_packing
        self._task_runner.submit(
            lambda: self._packing_service.open_box(
                device_id=self._device_id,
                count_in_packing=count_in_packing,
            ),
            self._on_box_opened,
            self._on_error,
        )

    def close_current_box(self) -> None:
        """Закрывает текущую коробку."""

        if self._state.is_busy or self._state.current_box is None:
            return
        box_id = self._state.current_box.box_id
        self._set_busy("Закрываем коробку и ждем печать этикетки...")
        self._task_runner.submit(
            lambda: self._packing_service.close_box(
                box_id=box_id,
                device_id=self._device_id,
            ),
            self._on_box_closed,
            self._on_close_error,
        )

    def set_count_in_packing(self, enabled: bool) -> None:
        """Обновляет флаг учета коробки в упаковке."""

        if self._state.is_busy:
            return
        if self._state.current_box is not None:
            box_id = self._state.current_box.box_id
            self._set_busy("Обновляем учет коробки в упаковке...")
            self._task_runner.submit(
                lambda: self._packing_service.set_count_in_packing(box_id, enabled),
                self._on_count_in_packing_changed,
                self._on_error,
            )
            return
        self._state = PackingUiState(
            is_busy=self._state.is_busy,
            current_box=self._state.current_box,
            status_message=self._state.status_message,
            result_message=self._state.result_message,
            error_message=self._state.error_message,
            last_scanned_code=self._state.last_scanned_code,
            count_in_packing=enabled,
        )
        self.state_changed.emit(self._state)

    def on_code_scanned(self, code: str) -> None:
        """Отправляет скан в текущую коробку."""

        if self._state.is_busy:
            return
        if self._state.current_box is None:
            self._play(SoundEvent.WARNING)
            self._set_state(
                PackingUiState(
                    current_box=None,
                    status_message="Сначала откройте коробку",
                    result_message="Код не отправлен",
                    error_message="Открытая коробка не найдена",
                    last_scanned_code=code,
                    count_in_packing=self._state.count_in_packing,
                )
            )
            return
        box_id = self._state.current_box.box_id
        self._set_busy("Отправляем код в коробку...", last_scanned_code=code)
        self._task_runner.submit(
            lambda: self._packing_service.scan_to_box(
                box_id=box_id,
                code=code,
                scanner_id=self._scanner_id,
            ),
            self._on_scan_result,
            self._on_error,
        )

    def _on_current_box_loaded(self, result: object) -> None:
        """Обрабатывает результат загрузки текущей коробки."""

        if result is None:
            self._set_state(PackingUiState(status_message="Открытая коробка не найдена"))
            return
        detail = self._expect(result, BoxDetailDto)
        self._set_state(
            PackingUiState(
                current_box=self._box_detail_to_ui(detail),
                status_message="Коробка загружена",
                count_in_packing=detail.count_in_packing,
            )
        )

    def _on_box_opened(self, result: object) -> None:
        """Обрабатывает результат открытия коробки."""

        opened = self._expect(result, OpenBoxResultDto)
        self._play(SoundEvent.OK if opened.ok else SoundEvent.WARNING)
        self._set_state(
            PackingUiState(
                current_box=self._box_to_ui(opened.box),
                status_message=(
                    "Коробка открыта" if opened.created else "Активная коробка уже была открыта"
                ),
                result_message=f"Коробка #{opened.box.box_id}",
                count_in_packing=opened.box.count_in_packing,
            )
        )

    def _on_scan_result(self, result: object) -> None:
        """Обрабатывает результат добавления кода в коробку."""

        scan_result = self._expect(result, ScanToBoxResultDto)
        self._play(self._sound_for_scan(scan_result))
        message = scan_result.error or scan_result.reason_code
        self._set_state(
            PackingUiState(
                current_box=self._box_to_ui(scan_result.box),
                status_message="Код добавлен" if scan_result.ok else "Код не добавлен",
                result_message=message,
                error_message="" if scan_result.ok else message,
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=scan_result.box.count_in_packing,
            )
        )

    def _on_count_in_packing_changed(self, result: object) -> None:
        """Обрабатывает результат переключения учета текущей коробки."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                PackingUiState(
                    current_box=self._state.current_box,
                    status_message="Учет коробки не изменен",
                    result_message=self._state.result_message,
                    error_message=message,
                    last_scanned_code=self._state.last_scanned_code,
                    count_in_packing=self._state.count_in_packing,
                )
            )
            return
        count_in_packing = edit_result.box.count_in_packing
        self._set_state(
            PackingUiState(
                current_box=self._box_with_count_in_packing(count_in_packing),
                status_message="Учет коробки обновлен",
                result_message=message,
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=count_in_packing,
            )
        )

    def _on_box_closed(self, result: object) -> None:
        """Обрабатывает результат закрытия коробки."""

        closed = self._expect(result, CloseBoxResultDto)
        self._play(SoundEvent.VICTORY if closed.ok else SoundEvent.ERROR)
        message = closed.error or closed.print_error or closed.reason_code
        event = self._close_event(closed)
        self._set_state(
            PackingUiState(
                current_box=None if closed.ok else self._box_to_ui(closed.box),
                status_message="Коробка закрыта" if closed.ok else "Коробка не закрыта",
                result_message=message,
                error_message="" if closed.ok else message,
                count_in_packing=self._state.count_in_packing,
            )
        )
        self.close_completed.emit(event)

    def _on_close_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку закрытия коробки и публикует модалку."""

        current_box = self._state.current_box
        self._on_error(exc)
        if current_box is None:
            return
        self.close_completed.emit(
            CloseBoxUiEvent(
                ok=False,
                box_id=current_box.box_id,
                sscc=current_box.sscc,
                filled=current_box.filled,
                capacity=current_box.capacity,
                is_full=current_box.filled >= current_box.capacity,
                title="Коробка не закрыта",
                message="Не удалось закрыть коробку",
                error_message=str(exc),
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку backend-сценария упаковки."""

        self._play(SoundEvent.ERROR)
        self._set_state(
            PackingUiState(
                current_box=self._state.current_box,
                status_message="Ошибка операции",
                error_message=str(exc),
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=self._state.count_in_packing,
            )
        )

    def _set_busy(self, message: str, last_scanned_code: str | None = None) -> None:
        """Переводит экран в состояние ожидания backend."""

        self._set_state(
            PackingUiState(
                is_busy=True,
                current_box=self._state.current_box,
                status_message=message,
                result_message=self._state.result_message,
                last_scanned_code=last_scanned_code or self._state.last_scanned_code,
                count_in_packing=self._state.count_in_packing,
            )
        )

    def _set_state(self, state: PackingUiState) -> None:
        """Сохраняет и публикует состояние упаковки."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    @staticmethod
    def _close_event(result: CloseBoxResultDto) -> CloseBoxUiEvent:
        """Преобразует backend-результат закрытия в UI-событие."""

        box = result.box
        is_full = box.filled >= box.capacity
        print_error = result.print_error or ""
        if result.ok and result.print_ok is False and print_error:
            title = "Коробка закрыта, печать с ошибкой"
            message = print_error
        elif result.ok:
            title = "Коробка закрыта"
            message = f"Коробка #{box.box_id} закрыта"
        else:
            title = "Коробка не закрыта"
            message = result.error or print_error or "Не удалось закрыть коробку"
        return CloseBoxUiEvent(
            ok=result.ok,
            box_id=box.box_id,
            sscc=box.sscc or "",
            filled=box.filled,
            capacity=box.capacity,
            is_full=is_full,
            title=title,
            message=message,
            error_message="" if result.ok else message,
            print_ok=result.print_ok,
            print_error=print_error,
        )

    @staticmethod
    def _box_detail_to_ui(detail: BoxDetailDto) -> PackingBoxUi:
        """Преобразует детальную коробку backend в UI-модель."""

        box = PackingController._box_to_ui(detail)
        return PackingBoxUi(
            box_id=box.box_id,
            order_name=box.order_name,
            sscc=box.sscc,
            filled=box.filled,
            capacity=box.capacity,
            count_in_packing=box.count_in_packing,
            is_closed=box.is_closed,
            print_ok=box.print_ok,
            print_error=box.print_error,
            items=[PackingController._item_to_ui(item) for item in detail.items],
        )

    @staticmethod
    def _box_to_ui(box: BoxDto) -> PackingBoxUi:
        """Преобразует краткую коробку backend в UI-модель."""

        return PackingBoxUi(
            box_id=box.box_id,
            order_name=box.order_name or "",
            sscc=box.sscc or "",
            filled=box.filled,
            capacity=box.capacity,
            count_in_packing=box.count_in_packing,
            is_closed=box.is_closed,
            print_ok=box.print_ok,
            print_error=box.print_error,
            items=[],
        )

    def _box_with_count_in_packing(self, count_in_packing: bool) -> PackingBoxUi | None:
        """Возвращает текущую коробку с обновленным флагом учета."""

        if self._state.current_box is None:
            return None
        return PackingBoxUi(
            box_id=self._state.current_box.box_id,
            order_name=self._state.current_box.order_name,
            sscc=self._state.current_box.sscc,
            filled=self._state.current_box.filled,
            capacity=self._state.current_box.capacity,
            count_in_packing=count_in_packing,
            is_closed=self._state.current_box.is_closed,
            print_ok=self._state.current_box.print_ok,
            print_error=self._state.current_box.print_error,
            items=self._state.current_box.items,
        )

    @staticmethod
    def _item_to_ui(item: BoxItemDto) -> PackingItemUi:
        """Преобразует элемент коробки backend в UI-модель."""

        return PackingItemUi(
            id=item.id,
            gtin=item.gtin,
            serial=item.serial,
            visible_code=item.visible_code,
        )

    @staticmethod
    def _sound_for_scan(result: ScanToBoxResultDto) -> SoundEvent:
        """Выбирает звук по результату сканирования в коробку."""

        if result.ok:
            return SoundEvent.OK
        if result.reason_code in {"wrong_order", "duplicate_in_box", "code_in_other_box"}:
            return SoundEvent.WARNING
        return SoundEvent.ERROR

    @staticmethod
    def _expect(result: object, expected_type: type[TPackingResult]) -> TPackingResult:
        """Проверяет тип результата фоновой задачи."""

        if not isinstance(result, expected_type):
            raise TypeError(f"Ожидался результат {expected_type.__name__}")
        return result
