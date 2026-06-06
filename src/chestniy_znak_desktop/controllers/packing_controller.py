"""Контроллер рабочего сценария упаковки."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Protocol, TypeVar

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.orders import LocalCodePoolPageDto, WorkOrderPageDto
from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxDto,
    BoxItemDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.api.models.printers import PackageLabelPrintResultDto
from chestniy_znak_desktop.domain.scanner_normalizer import visible
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent

TPackingResult = TypeVar("TPackingResult")
logger = logging.getLogger(__name__)


class PackingBackend(Protocol):
    """Контракт backend-сервиса упаковки."""

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую открытую коробку."""

    def open_box(
        self,
        device_id: str,
        count_in_packing: bool = True,
        order_id: str | None = None,
        order_line_id: str | None = None,
        code_value: str | None = None,
        sscc: str | None = None,
    ) -> OpenBoxResultDto:
        """Открывает новую коробку."""

    def scan_to_box(self, box_id: int, code: str, scanner_id: str) -> ScanToBoxResultDto:
        """Добавляет код в коробку."""

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает коробку."""

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Переключает учет коробки в упаковке."""


class OrderBackend(Protocol):
    """Контракт сервиса рабочих заказов."""

    def list_orders(
        self,
        status: str | None = None,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> WorkOrderPageDto:
        """Возвращает заказы с доступными строками номенклатуры."""

    def download_local_pool(
        self,
        order_id: str,
        limit: int = 5000,
        offset: int = 0,
    ) -> LocalCodePoolPageDto:
        """Возвращает страницу кодов заказа для локального сканирования."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


class PackageLabelPrinter(Protocol):
    """Контракт сервиса локальной печати SSCC-этикетки коробки."""

    def print_box_label(self, box_id: int, device_id: str) -> PackageLabelPrintResultDto:
        """Печатает SSCC-этикетку закрытой коробки."""


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
    items: list[PackingItemUi] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OrderLineOptionUi:
    """UI-модель выбранной строки заказа/номенклатуры."""

    order_id: str
    order_line_id: str
    order_number: str
    sku: str
    product_name: str
    label: str
    scan_required: bool = True
    package_capacity: int | None = None


@dataclass(frozen=True, slots=True)
class PackingUiState:
    """Состояние экрана упаковки."""

    is_busy: bool = False
    current_box: PackingBoxUi | None = None
    status_message: str = field(default_factory=lambda: tr("packing.noOpenBox"))
    result_message: str = ""
    error_message: str = ""
    last_scanned_code: str = ""
    count_in_packing: bool = True
    order_options: list[OrderLineOptionUi] = field(default_factory=list)
    selected_order_line_id: str = ""
    selected_order_scan_required: bool = True
    order_search: str = ""
    orders_loading: bool = False


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
    print_printer_name: str = ""


@dataclass(frozen=True, slots=True)
class CloseBoxTaskResult:
    """Результат закрытия коробки и последующей печати SSCC."""

    close: CloseBoxResultDto
    print_result: PackageLabelPrintResultDto | None = None


class PackingController(QObject):
    """Связывает экран упаковки, backend и сканер."""

    state_changed = Signal(PackingUiState)
    close_completed = Signal(CloseBoxUiEvent)

    def __init__(
        self,
        packing_service: PackingBackend,
        task_runner: TaskRunner,
        device_id: str,
        order_service: OrderBackend | None = None,
        scanner_id: str = "desktop-com",
        sound_service: SoundPlayer | None = None,
        label_printer: PackageLabelPrinter | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер упаковки."""

        super().__init__(parent)
        self._packing_service = packing_service
        self._order_service = order_service
        self._task_runner = task_runner
        self._device_id = device_id
        self._scanner_id = scanner_id
        self._sound_service = sound_service
        self._label_printer = label_printer
        self._state = PackingUiState()
        self._scan_queue: deque[str] = deque()

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

    def refresh_orders(self, search: str | None = None) -> None:
        """Загружает доступные заказы и строки номенклатуры."""

        if self._order_service is None:
            return
        order_service = self._order_service
        normalized_search = self._state.order_search if search is None else search.strip()
        self._set_state(
            replace(
                self._state,
                order_search=normalized_search,
                orders_loading=True,
                error_message="",
            )
        )
        self._task_runner.submit(
            lambda: order_service.list_orders(
                search=normalized_search,
                page=1,
                per_page=50,
            ),
            self._on_orders_loaded,
            self._on_orders_error,
        )

    def select_order_line(self, order_line_id: str) -> None:
        """Выбирает строку заказа для следующей коробки."""

        if self._state.current_box is not None:
            return
        selected = self._find_order_option(order_line_id)
        if selected is None:
            return
        self._set_state(
            replace(
                self._state,
                selected_order_line_id=selected.order_line_id,
                selected_order_scan_required=selected.scan_required,
                status_message=self._selected_order_status(selected),
                result_message=self._selected_order_result(selected),
                error_message="",
            )
        )

    def open_box(self) -> None:
        """Открывает новую коробку для сканирования."""

        if self._state.is_busy:
            return
        selected = self._selected_order_option()
        if selected is None and self._order_service is not None:
            self._play(SoundEvent.WARNING)
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("packing.selectOrder"),
                    error_message=tr("packing.openRequiresOrder"),
                )
            )
            return
        if selected is not None and not selected.scan_required:
            self._play(SoundEvent.WARNING)
            self._set_state(
                replace(
                    self._state,
                    selected_order_scan_required=False,
                    status_message=tr("packing.scanDisabled"),
                    result_message=self._selected_order_result(selected),
                    error_message=tr("packing.openNotNeeded"),
                )
            )
            return
        self._set_busy(tr("packing.openingBox"))
        count_in_packing = self._state.count_in_packing
        self._task_runner.submit(
            lambda: self._packing_service.open_box(
                device_id=self._device_id,
                count_in_packing=count_in_packing,
                order_id=selected.order_id if selected else None,
                order_line_id=selected.order_line_id if selected else None,
            ),
            self._on_box_opened,
            self._on_error,
        )

    def close_current_box(self) -> None:
        """Закрывает текущую коробку."""

        if self._state.is_busy or self._state.current_box is None:
            return
        box_id = self._state.current_box.box_id
        self._set_busy(tr("packing.closingBox"))
        self._task_runner.submit(
            lambda: self._close_and_print_box(box_id),
            self._on_box_closed,
            self._on_close_error,
        )

    def _close_and_print_box(self, box_id: int) -> CloseBoxTaskResult:
        """Закрывает коробку и печатает SSCC, если закрытие прошло успешно."""

        closed = self._packing_service.close_box(
            box_id=box_id,
            device_id=self._device_id,
        )
        if not closed.ok or self._label_printer is None:
            return CloseBoxTaskResult(close=closed)
        try:
            print_result = self._label_printer.print_box_label(box_id, self._device_id)
        except Exception as exc:
            print_result = PackageLabelPrintResultDto(
                ok=False,
                reason_code="label_print_failed",
                print_status="failed",
                print_ok=False,
                print_error_code="printer_job_failed",
                print_error=str(exc),
            )
        return CloseBoxTaskResult(close=closed, print_result=print_result)

    def set_count_in_packing(self, enabled: bool) -> None:
        """Обновляет флаг учета коробки в упаковке."""

        if self._state.is_busy:
            return
        if self._state.current_box is not None:
            box_id = self._state.current_box.box_id
            self._set_busy(tr("packing.updatingCountMode"))
            self._task_runner.submit(
                lambda: self._packing_service.set_count_in_packing(box_id, enabled),
                self._on_count_in_packing_changed,
                self._on_error,
            )
            return
        self._set_state(replace(self._state, count_in_packing=enabled))

    def on_code_scanned(self, code: str) -> None:
        """Отправляет скан в текущую коробку."""

        logger.info(
            "Packing scan captured length=%s sha256=%s value=%s",
            len(code),
            sha256(code.encode("utf-8")).hexdigest()[:24],
            visible(code),
        )
        if self._state.is_busy:
            self._scan_queue.append(code)
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("packing.scanQueued"),
                    result_message=tr("packing.scanQueuedResult", count=len(self._scan_queue)),
                    error_message="",
                    last_scanned_code=code,
                )
            )
            return
        if self._state.current_box is None:
            self._play(SoundEvent.WARNING)
            self._set_state(
                replace(
                    self._state,
                    current_box=None,
                    status_message=tr("packing.openBoxFirst"),
                    result_message=tr("packing.codeNotSent"),
                    error_message=tr("packing.noOpenBox"),
                    last_scanned_code=code,
                    count_in_packing=self._state.count_in_packing,
                )
            )
            return
        box_id = self._state.current_box.box_id
        self._set_busy(tr("packing.sendingCode"), last_scanned_code=code)
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
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    current_box=None,
                    status_message=tr("packing.noOpenBox"),
                )
            )
            self._process_next_queued_scan()
            return
        detail = self._expect(result, BoxDetailDto)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_detail_to_ui(detail),
                status_message=tr("packing.boxLoaded"),
                count_in_packing=detail.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_box_opened(self, result: object) -> None:
        """Обрабатывает результат открытия коробки."""

        opened = self._expect(result, OpenBoxResultDto)
        self._play(SoundEvent.OK if opened.ok else SoundEvent.WARNING)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(opened.box),
                status_message=(
                    tr("packing.boxOpened") if opened.created else tr("packing.boxAlreadyOpened")
                ),
                result_message=tr("packing.summary.boxTitle", box_id=opened.box.box_id),
                count_in_packing=opened.box.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_scan_result(self, result: object) -> None:
        """Обрабатывает результат добавления кода в коробку."""

        scan_result = self._expect(result, ScanToBoxResultDto)
        logger.info(
            "Packing scan result ok=%s reason=%s error=%s box_id=%s",
            scan_result.ok,
            scan_result.reason_code,
            scan_result.error or "",
            scan_result.box.box_id,
        )
        self._play(self._sound_for_scan(scan_result))
        message = self._scan_result_message(scan_result)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(scan_result.box),
                status_message=(
                    tr("packing.codeAdded") if scan_result.ok else tr("packing.codeNotAdded")
                ),
                result_message=message,
                error_message="" if scan_result.ok else message,
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=scan_result.box.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_count_in_packing_changed(self, result: object) -> None:
        """Обрабатывает результат переключения учета текущей коробки."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    current_box=self._state.current_box,
                    status_message=tr("packing.countModeNotChanged"),
                    result_message=self._state.result_message,
                    error_message=message,
                    last_scanned_code=self._state.last_scanned_code,
                    count_in_packing=self._state.count_in_packing,
                )
            )
            self._process_next_queued_scan()
            return
        count_in_packing = edit_result.box.count_in_packing
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_with_count_in_packing(count_in_packing),
                status_message=tr("packing.countModeUpdated"),
                result_message=self._count_in_packing_message(count_in_packing),
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_box_closed(self, result: object) -> None:
        """Обрабатывает результат закрытия коробки."""

        close_result = self._expect(result, CloseBoxTaskResult)
        closed = close_result.close
        self._play(self._sound_for_close(close_result))
        message = closed.error or closed.reason_code
        event = self._close_event(closed, close_result.print_result)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=None if closed.ok else self._box_to_ui(closed.box),
                status_message=(
                    tr("closeBox.closedTitle") if closed.ok else tr("closeBox.notClosedTitle")
                ),
                result_message=message,
                error_message="" if closed.ok else message,
                count_in_packing=self._state.count_in_packing,
            )
        )
        self.close_completed.emit(event)
        self._process_next_queued_scan()

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
                is_full=current_box.capacity > 0 and current_box.filled >= current_box.capacity,
                title=tr("closeBox.notClosedTitle"),
                message=tr("closeBox.notClosedMessage"),
                error_message=str(exc),
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку backend-сценария упаковки."""

        self._play(SoundEvent.ERROR)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._state.current_box,
                status_message=tr("packing.operationError"),
                error_message=str(exc),
                last_scanned_code=self._state.last_scanned_code,
                count_in_packing=self._state.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _set_busy(self, message: str, last_scanned_code: str | None = None) -> None:
        """Переводит экран в состояние ожидания backend."""

        self._set_state(
            replace(
                self._state,
                is_busy=True,
                current_box=self._state.current_box,
                status_message=message,
                result_message=self._state.result_message,
                last_scanned_code=last_scanned_code or self._state.last_scanned_code,
                count_in_packing=self._state.count_in_packing,
            )
        )

    def _on_orders_loaded(self, result: object) -> None:
        """Обрабатывает загрузку заказов для выбора номенклатуры."""

        page = self._expect(result, WorkOrderPageDto)
        options = self._order_options(page)
        selected_id = self._state.selected_order_line_id
        if selected_id and not any(option.order_line_id == selected_id for option in options):
            selected_id = ""
        if not selected_id and options:
            selected_id = options[0].order_line_id
        selected = self._find_option_in(options, selected_id)
        status_message = (
            self._selected_order_status(selected) if selected else self._state.status_message
        )
        result_message = (
            self._selected_order_result(selected) if selected else self._state.result_message
        )
        if not options:
            status_message = tr("packing.noAvailableOrders")
            result_message = ""
        self._set_state(
            replace(
                self._state,
                order_options=options,
                selected_order_line_id=selected_id,
                selected_order_scan_required=selected.scan_required if selected else True,
                orders_loading=False,
                status_message=status_message,
                result_message=result_message,
            )
        )

    def _on_orders_error(self, exc: Exception) -> None:
        """Показывает ошибку загрузки заказов без сброса текущей коробки."""

        self._set_state(
            replace(
                self._state,
                orders_loading=False,
                error_message=tr("packing.ordersLoadFailed", error=exc),
            )
        )

    def _selected_order_option(self) -> OrderLineOptionUi | None:
        """Возвращает выбранную строку заказа."""

        return self._find_order_option(self._state.selected_order_line_id)

    def _find_order_option(self, order_line_id: str) -> OrderLineOptionUi | None:
        """Ищет строку заказа в текущем списке выбора."""

        return next(
            (
                option
                for option in self._state.order_options
                if option.order_line_id == order_line_id
            ),
            None,
        )

    @staticmethod
    def _order_options(page: WorkOrderPageDto) -> list[OrderLineOptionUi]:
        """Преобразует заказы backend в варианты выбора строки заказа."""

        options: list[OrderLineOptionUi] = []
        for order in page.data:
            for line in order.lines:
                if line.status != "active":
                    continue
                product = line.product
                sku = product.sku if product else line.product_id
                product_name = product.name if product else tr("packing.product")
                label = f"{order.order_number} · {sku} · {product_name}"
                if line.package_capacity:
                    label = (
                        f"{label} · "
                        f"{tr('packing.capacityShort', capacity=line.package_capacity)}"
                    )
                if not order.scan_required:
                    label = f"{label} · {tr('packing.noScanSuffix')}"
                options.append(
                    OrderLineOptionUi(
                        order_id=order.id,
                        order_line_id=line.id,
                        order_number=order.order_number,
                        sku=sku,
                        product_name=product_name,
                        scan_required=order.scan_required,
                        package_capacity=line.package_capacity,
                        label=label,
                    )
                )
        return options

    @staticmethod
    def _find_option_in(
        options: list[OrderLineOptionUi],
        order_line_id: str,
    ) -> OrderLineOptionUi | None:
        """Ищет выбранную строку в переданном списке."""

        return next(
            (option for option in options if option.order_line_id == order_line_id),
            None,
        )

    @staticmethod
    def _selected_order_status(selected: OrderLineOptionUi | None) -> str:
        """Возвращает статус выбранного заказа для оператора."""

        if selected is None:
            return tr("packing.selectOrder")
        if selected.scan_required:
            return tr("packing.selectedOrder", order=selected.order_number)
        return tr("packing.scanDisabled")

    @staticmethod
    def _selected_order_result(selected: OrderLineOptionUi | None) -> str:
        """Возвращает пояснение по выбранному заказу."""

        if selected is None:
            return ""
        if selected.scan_required:
            product = selected.product_name or selected.sku
            if selected.package_capacity:
                return (
                    f"{product} · "
                    f"{tr('packing.capacityShort', capacity=selected.package_capacity)}"
                )
            return product
        return tr("packing.noScanOrderResult", order=selected.order_number)

    def _set_state(self, state: PackingUiState) -> None:
        """Сохраняет и публикует состояние упаковки."""

        self._state = state
        self.state_changed.emit(state)

    def _process_next_queued_scan(self) -> None:
        """Отправляет следующий скан, который пришел во время фоновой операции."""

        if self._state.is_busy or not self._scan_queue:
            return
        next_code = self._scan_queue.popleft()
        self.on_code_scanned(next_code)

    def _play(self, event: SoundEvent) -> None:
        """Проигрывает звук, если сервис звука подключен."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    @staticmethod
    def _close_event(
        result: CloseBoxResultDto,
        print_result: PackageLabelPrintResultDto | None = None,
    ) -> CloseBoxUiEvent:
        """Преобразует backend-результат закрытия в UI-событие."""

        box = result.box
        is_full = box.capacity > 0 and box.filled >= box.capacity
        print_ok = print_result.print_ok if print_result is not None else None
        print_error = print_result.print_error if print_result is not None else ""
        print_printer_name = (
            print_result.printer.name
            if print_result is not None and print_result.printer is not None
            else ""
        )
        if result.ok:
            title = tr("closeBox.closedTitle")
            message = tr("closeBox.closedMessage", box_id=box.box_id)
        else:
            title = tr("closeBox.notClosedTitle")
            message = result.error or tr("closeBox.notClosedMessage")
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
            print_ok=print_ok,
            print_error=print_error,
            print_printer_name=print_printer_name,
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
            items=self._state.current_box.items,
        )

    @staticmethod
    def _count_in_packing_message(enabled: bool) -> str:
        """Возвращает понятный оператору текст режима учета коробки."""

        if enabled:
            return tr("packing.modeCounted")
        return tr("packing.modeNotCounted")

    @staticmethod
    def _scan_result_message(result: ScanToBoxResultDto) -> str:
        """Возвращает понятный оператору текст результата сканирования."""

        code = result.message_code or result.reason_code
        if result.ok:
            if result.duplicate or code in {"duplicate_in_box", "duplicate_in_package"}:
                return tr("packing.scan.duplicateInBox")
            if result.box_full_signal:
                return tr("packing.scan.acceptedFull")
            return tr("packing.scan.accepted")
        messages = {
            "code_in_other_box": "packing.scan.codeInOtherBox",
            "mark_code_already_packed": "packing.scan.codeInOtherBox",
            "wrong_order": "packing.scan.wrongOrder",
            "mark_code_wrong_order": "packing.scan.wrongOrder",
            "box_capacity_reached": "packing.scan.capacityReached",
            "package_capacity_exceeded": "packing.scan.capacityReached",
            "mark_code_not_found": "packing.scan.notFound",
            "mark_code_not_issued": "packing.scan.notIssued",
            "invalid_code_format": "packing.scan.invalidFormat",
            "package_is_not_open": "packing.scan.packageClosed",
            "package_capacity_required": "packing.scan.capacityMissing",
            "scan_rejected": "packing.scan.rejected",
        }
        key = messages.get(code) or messages.get(result.reason_code)
        if key is not None:
            return tr(key)
        return result.error or code or tr("packing.scan.rejected")

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
            if result.duplicate:
                return SoundEvent.WARNING
            return SoundEvent.OK
        if result.reason_code in {
            "wrong_order",
            "mark_code_wrong_order",
            "duplicate_in_box",
            "code_in_other_box",
            "mark_code_already_packed",
        }:
            return SoundEvent.WARNING
        return SoundEvent.ERROR

    @staticmethod
    def _sound_for_close(result: CloseBoxTaskResult) -> SoundEvent:
        """Выбирает звук по закрытию коробки и печати SSCC."""

        if not result.close.ok:
            return SoundEvent.ERROR
        if result.print_result is not None and not result.print_result.print_ok:
            return SoundEvent.WARNING
        return SoundEvent.VICTORY

    @staticmethod
    def _expect(result: object, expected_type: type[TPackingResult]) -> TPackingResult:
        """Проверяет тип результата фоновой задачи."""

        if not isinstance(result, expected_type):
            raise TypeError(f"Ожидался результат {expected_type.__name__}")
        return result
