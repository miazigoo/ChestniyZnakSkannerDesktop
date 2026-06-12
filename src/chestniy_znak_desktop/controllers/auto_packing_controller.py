"""Контроллер упаковки через автосканер мультиплат."""

from __future__ import annotations

import logging
import json
import re
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Any, Protocol, TypeVar, cast

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.orders import (
    LocalCodePoolPageDto,
    LocalPoolCodeDto,
    WorkOrderPageDto,
)
from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanBatchToBoxResultDto,
)
from chestniy_znak_desktop.api.models.printers import PackageLabelPrintResultDto
from chestniy_znak_desktop.api.models.verify import VerifyExistsResponseDto
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.packing_controller import (
    CloseBoxTaskResult,
    CloseBoxUiEvent,
    OrderBackend,
    OrderLineOptionUi,
    PackageLabelPrinter,
    PackingBoxUi,
    PackingItemUi,
    PackingController,
)
from chestniy_znak_desktop.domain.scanner_normalizer import (
    MarkingCodeParseError,
    parse_marking_code,
)
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent

TAutoPackingResult = TypeVar("TAutoPackingResult")
logger = logging.getLogger(__name__)
GS1_CODE_START_RE = re.compile(r"01\d{14}21")
SCAN_QUEUE_STATUS_STEP = 25


class AutoPackingBackend(Protocol):
    """Контракт backend-сервиса коробок для автосканера."""

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

    def scan_batch_to_box(
        self,
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Атомарно добавляет пачку кодов в коробку."""

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает коробку."""

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Переключает учет коробки в упаковке."""


class AutoPackingVerifier(Protocol):
    """Контракт сервиса проверки DataMatrix перед локальным боксом."""

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        save_scan: bool = True,
    ) -> VerifyExistsResponseDto:
        """Проверяет код по backend перед добавлением в локальный бокс."""


class AutoPackingBoxEditor(Protocol):
    """Контракт backend-сервиса быстрых правок текущей коробки."""

    def remove_item(self, box_id: int, item_id: int) -> BoxActionResultDto:
        """Удаляет один код из открытой коробки."""

    def clear_box(self, box_id: int) -> BoxActionResultDto:
        """Очищает открытую коробку от всех кодов."""

    def delete_empty_box(self, box_id: int) -> BoxActionResultDto:
        """Удаляет пустую открытую коробку."""


class AutoPackingWsVerifier(Protocol):
    """Контракт WS-сервиса быстрой проверки автоскана."""

    verified: Any
    failed: Any

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        box_id: int | None = None,
    ) -> str | None:
        """Отправляет проверку кода по WebSocket."""


class SoundPlayer(Protocol):
    """Контракт сервиса звуковой обратной связи."""

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""


@dataclass(frozen=True, slots=True)
class AutoPackingBoxItemUi:
    """UI-модель кода внутри локального автоскана-бокса."""

    code_id: int
    raw_code: str
    gtin: str
    serial: str
    visible_code: str
    order_key: str


@dataclass(frozen=True, slots=True)
class AutoPackingUiState:
    """Состояние экрана автосканера."""

    is_busy: bool = False
    codes_per_item: int = 1
    pending_items: list[AutoPackingBoxItemUi] = field(default_factory=list)
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

    @property
    def pending_count(self) -> int:
        """Возвращает количество кодов в локальном боксе."""

        return len(self.pending_items)

    @property
    def is_pending_full(self) -> bool:
        """Проверяет, заполнен ли локальный бокс мультиплаты."""

        return self.pending_count >= self.codes_per_item


class AutoPackingController(QObject):
    """Копит коды мультиплаты и отправляет заполненную пачку в коробку."""

    state_changed = Signal(AutoPackingUiState)
    close_completed = Signal(CloseBoxUiEvent)

    def __init__(
        self,
        packing_service: AutoPackingBackend,
        verify_service: AutoPackingVerifier,
        box_edit_service: AutoPackingBoxEditor | None,
        task_runner: TaskRunner,
        settings_store: SettingsStore,
        settings_defaults: AppConfig,
        device_id: str,
        order_service: OrderBackend | None = None,
        scanner_id: str = "desktop-com",
        ws_verify_service: AutoPackingWsVerifier | None = None,
        sound_service: SoundPlayer | None = None,
        label_printer: PackageLabelPrinter | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер автосканерной упаковки."""

        super().__init__(parent)
        self._packing_service = packing_service
        self._verify_service = verify_service
        self._box_edit_service = box_edit_service
        self._order_service = order_service
        self._task_runner = task_runner
        self._settings_store = settings_store
        self._settings_defaults = settings_defaults
        self._device_id = device_id
        self._scanner_id = scanner_id
        self._ws_verify_service = ws_verify_service
        self._sound_service = sound_service
        self._label_printer = label_printer
        self._scan_queue: deque[str] = deque()
        self._queued_raw_codes: set[str] = set()
        self._active_scan_code = ""
        self._accepted_raw_codes: set[str] = set()
        self._accepted_box_id: int | None = None
        self._box_code_ids: set[int] = set()
        self._box_visible_codes: set[str] = set()
        self._local_pool_order_id = ""
        self._local_pool_codes: dict[str, LocalPoolCodeDto] = {}
        self._local_pool_identity_codes: dict[str, LocalPoolCodeDto] = {}
        self._local_pool_loaded = False
        self._open_box_after_pool_order_id = ""
        self._retry_scan_after_pool_refresh = ""
        self._pool_miss_retry_codes: set[str] = set()
        settings = settings_store.load(settings_defaults)
        self._state = AutoPackingUiState(
            codes_per_item=max(1, settings.auto_pack_codes_per_item),
        )
        if self._ws_verify_service is not None:
            self._ws_verify_service.verified.connect(self._on_ws_verify_result)
            self._ws_verify_service.failed.connect(self._on_ws_verify_error)

    @property
    def state(self) -> AutoPackingUiState:
        """Возвращает текущее состояние экрана."""

        return self._state

    def refresh_current_box(self) -> None:
        """Загружает текущую открытую коробку пользователя."""

        self._set_busy(tr("packing.loadingCurrentBox"))
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

    def handle_realtime_message(self, message: str) -> None:
        """Обновляет локальный пул при realtime-событиях по коробкам."""

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        message_type = str(payload.get("type") or "")
        if not message_type.startswith("package."):
            return
        selected = self._selected_order_option()
        if selected is None or not selected.scan_required:
            return
        event_order_id = str(payload.get("order_id") or "")
        if event_order_id and event_order_id != selected.order_id:
            return
        self._local_pool_loaded = False
        self._download_local_pool_for(selected)

    def select_order_line(self, order_line_id: str) -> None:
        """Выбирает строку заказа для следующей коробки."""

        selected = self._find_order_option(order_line_id)
        if selected is None:
            if order_line_id and order_line_id != self._state.selected_order_line_id:
                self._set_state(
                    replace(
                        self._state,
                        selected_order_line_id=order_line_id,
                        status_message=tr("packing.selectOrder"),
                        result_message="",
                        error_message="",
                    )
                )
            return
        self.sync_selected_order(selected)

    def sync_selected_order(self, selected: OrderLineOptionUi) -> None:
        """Синхронизирует глобально выбранный заказ с автоупаковкой."""

        options = self._order_options_with_selected(self._state.order_options, selected)
        self._set_state(
            replace(
                self._state,
                order_options=options,
                selected_order_line_id=selected.order_line_id,
                selected_order_scan_required=selected.scan_required,
                status_message=PackingController._selected_order_status(selected),
                result_message=PackingController._selected_order_result(selected),
                error_message="",
            )
        )
        self._download_local_pool_for(selected)

    def open_box(self) -> None:
        """Открывает коробку для приема заполненных автоскана-боксов."""

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
                    result_message=PackingController._selected_order_result(selected),
                    error_message=tr("packing.openNotNeeded"),
                )
            )
            return
        if selected is not None and not self._is_local_pool_ready_for(selected.order_id):
            if self._download_local_pool_for(selected, open_after=True):
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
        """Закрывает текущую открытую коробку автоскана."""

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
        """Закрывает коробку автоскана и печатает SSCC, если можно."""

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

    def set_codes_per_item(self, value: int) -> None:
        """Сохраняет вместимость локального бокса мультиплаты."""

        value = max(1, int(value))
        if value == self._state.codes_per_item:
            return
        current_settings = self._settings_store.load(self._settings_defaults)
        self._settings_store.save(replace(current_settings, auto_pack_codes_per_item=value))
        self._set_state(
            replace(
                self._state,
                codes_per_item=value,
                status_message=tr("autoPacking.capacityUpdated"),
                result_message=tr("autoPacking.waitCodesCount", count=value),
                error_message="",
            )
        )
        if (
            not self._state.is_busy
            and self._state.current_box is not None
            and self._state.is_pending_full
        ):
            self._submit_pending_batch()

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
        self._set_state(
            replace(
                self._state,
                count_in_packing=enabled,
                status_message=tr("autoPacking.nextCountUpdated"),
                result_message=(
                    tr("autoPacking.nextCounted") if enabled else tr("autoPacking.nextNotCounted")
                ),
                error_message="",
            )
        )

    def clear_pending(self) -> None:
        """Очищает локальный автоскана-бокс без изменения коробки."""

        if self._state.is_busy:
            return
        self._set_state(
            replace(
                self._state,
                pending_items=[],
                status_message=tr("autoPacking.localCleared"),
                result_message=tr("autoPacking.rescanAllowed"),
                error_message="",
            )
        )

    def remove_pending_at(self, row: int) -> None:
        """Удаляет один код из локального бокса по индексу строки."""

        if self._state.is_busy or row < 0 or row >= len(self._state.pending_items):
            return
        items = list(self._state.pending_items)
        removed = items.pop(row)
        self._set_state(
            replace(
                self._state,
                pending_items=items,
                status_message=tr("autoPacking.removedFromLocal"),
                result_message=removed.serial,
                error_message="",
            )
        )

    def remove_box_item_at(self, row: int) -> None:
        """Удаляет выбранный код из текущей открытой коробки."""

        if (
            self._state.is_busy
            or self._state.current_box is None
            or self._box_edit_service is None
            or row < 0
            or row >= len(self._state.current_box.items)
        ):
            return
        editor = self._box_edit_service
        box_id = self._state.current_box.box_id
        item_id = self._state.current_box.items[row].id
        self._set_busy(tr("boxes.edit.removingCode", item_id=item_id, box_id=box_id))
        self._task_runner.submit(
            lambda: editor.remove_item(box_id, item_id),
            self._on_box_edit_result,
            self._on_error,
        )

    def clear_current_box(self) -> None:
        """Очищает текущую открытую коробку от уже добавленных кодов."""

        if self._state.is_busy or self._state.current_box is None or self._box_edit_service is None:
            return
        editor = self._box_edit_service
        box_id = self._state.current_box.box_id
        self._set_busy(tr("boxes.edit.clearing", box_id=box_id))
        self._task_runner.submit(
            lambda: editor.clear_box(box_id),
            self._on_box_edit_result,
            self._on_error,
        )

    def delete_current_box(self) -> None:
        """Удаляет текущую открытую коробку, если она пустая."""

        if self._state.is_busy or self._state.current_box is None or self._box_edit_service is None:
            return
        editor = self._box_edit_service
        box_id = self._state.current_box.box_id
        self._set_busy(tr("boxes.edit.deletingEmpty", box_id=box_id))
        self._task_runner.submit(
            lambda: editor.delete_empty_box(box_id),
            self._on_box_delete_result,
            self._on_error,
        )

    def on_code_scanned(self, code: str) -> None:
        """Добавляет скан в локальный бокс после быстрых локальных проверок."""

        normalized = (code or "").strip()
        if not normalized:
            return
        parts = self._split_scanner_payload(normalized)
        if not parts:
            self._reject_malformed_scan(normalized)
            return
        if len(parts) > 1:
            logger.warning(
                "Auto packing split glued scanner payload into %s codes: %r",
                len(parts),
                normalized,
            )
        for part in parts:
            self._handle_single_code_scanned(part)

    def _handle_single_code_scanned(self, normalized: str) -> None:
        """Обрабатывает один уже выделенный код маркировки."""

        selected = self._selected_order_option()
        if self._should_refresh_pool_before_reject(normalized, selected):
            return
        local_pool_code = self._code_from_selected_local_pool(normalized, selected)
        if local_pool_code is None:
            return
        normalized = local_pool_code
        if self._box_contains_visible_code(normalized):
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("autoPacking.codeAlreadyInBox"),
                    result_message=tr("autoPacking.duplicateSkipped"),
                    error_message="",
                    last_scanned_code=normalized,
                )
            )
            return
        if self._box_contains_accepted_raw_code(normalized):
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("autoPacking.codeAlreadyInBox"),
                    result_message=tr("autoPacking.duplicateSkipped"),
                    error_message="",
                    last_scanned_code=normalized,
                )
            )
            return
        if self._is_local_raw_duplicate(normalized):
            self._set_state(
                replace(
                    self._state,
                    result_message=tr("autoPacking.duplicateInLocalOrQueue"),
                    error_message=tr("autoPacking.localDuplicateNotAdded"),
                    last_scanned_code=normalized,
                )
            )
            return
        if self._state.is_busy:
            self._enqueue_scan(normalized)
            return
        if self._state.current_box is None:
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("packing.openBoxFirst"),
                    error_message=tr("packing.noOpenBox"),
                    last_scanned_code=normalized,
                )
            )
            return
        if self._state.is_pending_full:
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("autoPacking.localFull"),
                    error_message=tr("autoPacking.waitBatchOrClear"),
                    last_scanned_code=normalized,
                )
            )
            return
        self._add_code_to_pending(normalized)

    def _split_scanner_payload(self, code: str) -> list[str]:
        """Разделяет склеенные DataMatrix и отбрасывает обрезанные хвосты."""

        starts = [match.start() for match in GS1_CODE_START_RE.finditer(code)]
        if not starts:
            return [] if code[0].isdigit() else [code]
        starts.append(len(code))
        return [
            code[start:end].strip()
            for start, end in zip(starts, starts[1:])
            if code[start:end].strip()
        ]

    def _reject_malformed_scan(self, code: str) -> None:
        """Показывает ошибку по обрезанному скану, не добавляя его в ВБ."""

        logger.warning("Auto packing rejected malformed scanner payload: %r", code)
        self._play(SoundEvent.WARNING)
        self._set_state(
            replace(
                self._state,
                status_message=tr("autoPacking.scanRejected"),
                result_message="",
                error_message=tr("autoPacking.truncatedScan"),
                last_scanned_code=code,
            )
        )

    def _verify_code_http(self, code: str) -> None:
        """Проверяет код через HTTP, если WS недоступен или не ответил."""

        self._set_busy(tr("autoPacking.checkingHttp"), code)
        self._task_runner.submit(
            lambda: self._verify_service.verify_exists(
                code=code,
                scanner_id=self._scanner_id,
                allow_duplicate=True,
                save_scan=False,
            ),
            lambda result: self._on_verify_result(result, code),
            self._on_error,
        )

    def _add_code_to_pending(self, raw_code: str) -> None:
        """Добавляет raw-код в ВБ без предварительной серверной проверки."""

        item = AutoPackingBoxItemUi(
            code_id=0,
            raw_code=raw_code,
            gtin="",
            serial=tr("autoPacking.pendingSerial"),
            visible_code=raw_code,
            order_key=tr("autoPacking.pendingOrder"),
        )
        pending_items = [*self._state.pending_items, item]
        next_state = replace(
            self._state,
            is_busy=False,
            pending_items=pending_items,
            status_message=tr("autoPacking.addedToLocal"),
            result_message=f"{len(pending_items)} / {self._state.codes_per_item}",
            error_message="",
            last_scanned_code=raw_code,
        )
        self._set_state(next_state)
        if next_state.is_pending_full:
            self._submit_pending_batch()
            return
        self._process_next_queued_scan()

    def _on_ws_verify_result(
        self,
        _request_id: str,
        raw_code: str,
        result: object,
    ) -> None:
        """Игнорирует устаревшие WS-ответы предварительной проверки."""

        return None

    def _on_ws_verify_error(self, _request_id: str, raw_code: str, _error: str) -> None:
        """Игнорирует устаревшие ошибки WS-предпроверки."""

        return None

    def _on_verify_result(self, result: object, raw_code: str) -> None:
        """Обрабатывает проверку кода и при заполнении отправляет пачку."""

        self._active_scan_code = ""
        verify = self._expect(result, VerifyExistsResponseDto)
        if not verify.ok or not verify.exists or verify.code is None:
            if self._is_current_box_duplicate_response(verify):
                self._set_state(
                    replace(
                        self._state,
                        is_busy=False,
                        status_message=tr("autoPacking.codeAlreadyInBox"),
                        result_message=tr("autoPacking.duplicateSkipped"),
                        error_message="",
                        last_scanned_code=raw_code,
                    )
                )
                self._process_next_queued_scan()
                return
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.verifyFailed"),
                    error_message=verify.message,
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        if self._box_contains_code(verify.code.id):
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.codeAlreadyInBox"),
                    result_message=tr("autoPacking.duplicateSkipped"),
                    error_message="",
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        order_key = (verify.code.order_dnp_name or verify.order_name or "").strip()
        if not order_key or order_key in {"Не привязан", tr("autoPacking.unbound")}:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.notAddedToLocal"),
                    error_message=tr("autoPacking.notLinkedToOrder"),
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        if any(item.code_id == verify.code.id for item in self._state.pending_items):
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.localDuplicate"),
                    error_message=tr("autoPacking.alreadyInLocal"),
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        current_order = self._state.pending_items[0].order_key if self._state.pending_items else ""
        if current_order and current_order != order_key:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.wrongOrder"),
                    error_message=tr("autoPacking.oneOrderOnly"),
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        item = AutoPackingBoxItemUi(
            code_id=verify.code.id,
            raw_code=raw_code,
            gtin=verify.code.gtin,
            serial=verify.code.serial,
            visible_code=verify.code.visible_code,
            order_key=order_key,
        )
        pending_items = [*self._state.pending_items, item]
        next_state = replace(
            self._state,
            is_busy=False,
            pending_items=pending_items,
            status_message=tr("autoPacking.addedToLocal"),
            result_message=f"{len(pending_items)} / {self._state.codes_per_item}",
            error_message="",
            last_scanned_code=raw_code,
        )
        self._set_state(next_state)
        if next_state.is_pending_full:
            self._submit_pending_batch()
            return
        self._process_next_queued_scan()

    def _submit_pending_batch(self) -> None:
        """Отправляет заполненный локальный бокс в текущую коробку."""

        if self._state.current_box is None or not self._state.pending_items:
            return
        box_id = self._state.current_box.box_id
        codes = [item.raw_code for item in self._state.pending_items]
        self._set_busy(tr("autoPacking.addingBatch"))
        self._task_runner.submit(
            lambda: self._packing_service.scan_batch_to_box(
                box_id=box_id,
                codes=codes,
                scanner_id=self._scanner_id,
            ),
            self._on_batch_added,
            self._on_error,
        )

    def _on_batch_added(self, result: object) -> None:
        """Обрабатывает результат атомарного добавления пачки."""

        batch = self._expect(result, ScanBatchToBoxResultDto)
        if not batch.ok:
            message = batch.error or batch.reason_code
            pending_items = self._pending_without_rejected_batch_item(batch)
            self._remember_rejected_current_box_duplicate(batch)
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    pending_items=pending_items,
                    current_box=self._merge_box_summary(batch.box),
                    status_message=tr("autoPacking.batchNotAdded"),
                    result_message=(
                        tr("autoPacking.pendingLeft", count=len(pending_items))
                        if len(pending_items) != len(self._state.pending_items)
                        else self._state.result_message
                    ),
                    error_message=self._batch_error_message(message, batch),
                )
            )
            return
        self._remember_accepted_batch(self._state.current_box, self._state.pending_items)
        self._mark_pending_codes_packed_in_local_pool(batch)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                pending_items=[],
                current_box=self._merge_box_summary(batch.box),
                status_message=tr("autoPacking.batchAdded"),
                result_message=tr("autoPacking.addedCount", count=batch.added),
                error_message="",
            )
        )
        self._play(SoundEvent.OK)
        self._continue_after_batch(batch)

    def _on_box_edit_result(self, result: object) -> None:
        """Обрабатывает быструю правку текущей коробки автоскана."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.boxNotChanged"),
                    error_message=message,
                )
            )
            return
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(edit_result.box),
                status_message=self._status_for_edit_reason(edit_result.reason_code),
                result_message=message,
                error_message="",
            )
        )
        self._forget_accepted_codes_after_box_edit()
        self.refresh_current_box()

    def _on_box_delete_result(self, result: object) -> None:
        """Обрабатывает удаление пустой текущей коробки."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("autoPacking.boxNotDeleted"),
                    error_message=message,
                )
            )
            return
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=None,
                status_message=tr("autoPacking.emptyDeleted"),
                result_message=message,
                error_message="",
            )
        )
        self._forget_accepted_codes()

    def _on_count_in_packing_changed(self, result: object) -> None:
        """Обрабатывает результат переключения учета текущей коробки."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message=tr("packing.countModeNotChanged"),
                    error_message=message,
                )
            )
            return
        count_in_packing = edit_result.box.count_in_packing
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_with_count_in_packing(count_in_packing),
                count_in_packing=count_in_packing,
                status_message=tr("packing.countModeUpdated"),
                result_message=self._count_in_packing_message(count_in_packing),
                error_message="",
            )
        )

    def _on_box_closed(self, result: object) -> None:
        """Обрабатывает результат закрытия коробки автоскана."""

        close_result = self._expect(result, CloseBoxTaskResult)
        closed = close_result.close
        self._play(PackingController._sound_for_close(close_result))
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
            )
        )
        if closed.ok:
            self._forget_accepted_codes()
            self._refresh_selected_local_pool()
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
                is_full=current_box.capacity > 0 and current_box.filled >= current_box.capacity,
                title=tr("closeBox.notClosedTitle"),
                message=tr("closeBox.notClosedMessage"),
                error_message=str(exc),
            )
        )

    def _on_current_box_loaded(self, result: object) -> None:
        """Обрабатывает загрузку текущей коробки."""

        if result is None:
            self._forget_accepted_codes()
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    current_box=None,
                    status_message=tr("packing.noOpenBox"),
                )
            )
            return
        detail = self._expect(result, BoxDetailDto)
        self._sync_accepted_box(detail.box_id)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(detail),
                status_message=tr("packing.boxLoaded"),
                error_message="",
                count_in_packing=detail.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_box_opened(self, result: object) -> None:
        """Обрабатывает открытие коробки."""

        opened = self._expect(result, OpenBoxResultDto)
        self._sync_accepted_box(opened.box.box_id)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(opened.box),
                status_message=(
                    tr("packing.boxOpened") if opened.created else tr("packing.boxAlreadyOpened")
                ),
                result_message=tr("packing.summary.boxTitle", box_id=opened.box.box_id),
                error_message="",
                count_in_packing=opened.box.count_in_packing,
            )
        )
        self._process_next_queued_scan()

    def _on_orders_loaded(self, result: object) -> None:
        """Обрабатывает загрузку заказов для выбора номенклатуры."""

        page = self._expect(result, WorkOrderPageDto)
        options = PackingController._order_options(page)
        selected_id = self._state.selected_order_line_id
        selected = self._selected_order_option()
        if selected is not None:
            options = self._order_options_with_selected(options, selected)
        selected = PackingController._find_option_in(options, selected_id)
        status_message = (
            PackingController._selected_order_status(selected)
            if selected
            else self._state.status_message
        )
        result_message = (
            PackingController._selected_order_result(selected)
            if selected
            else self._state.result_message
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
        if selected is not None and selected.scan_required and self._state.current_box is None:
            self._download_local_pool_for(selected)

    def _on_orders_error(self, exc: Exception) -> None:
        """Показывает ошибку загрузки заказов без сброса текущей коробки."""

        self._set_state(
            replace(
                self._state,
                orders_loading=False,
                error_message=tr("packing.ordersLoadFailed", error=exc),
            )
        )

    def _download_local_pool_for(
        self,
        selected: OrderLineOptionUi | None,
        *,
        open_after: bool = False,
        force: bool = False,
    ) -> bool:
        """Скачивает локальный пул кодов выбранного заказа, если backend это поддерживает."""

        if selected is None or not selected.scan_required:
            return False
        if not force and self._is_local_pool_ready_for(selected.order_id):
            return False
        download_method = getattr(self._order_service, "download_local_pool", None)
        if not callable(download_method):
            return False
        self._local_pool_order_id = selected.order_id
        self._local_pool_codes.clear()
        self._local_pool_identity_codes.clear()
        self._local_pool_loaded = False
        if open_after:
            self._open_box_after_pool_order_id = selected.order_id
        self._set_busy(tr("autoPacking.localPoolDownloading"))
        self._task_runner.submit(
            lambda: self._download_local_pool_codes(selected.order_id, download_method),
            lambda codes: self._on_local_pool_loaded(
                selected.order_id,
                cast(dict[str, LocalPoolCodeDto], codes),
            ),
            self._on_local_pool_error,
        )
        return True

    def _refresh_selected_local_pool(self) -> None:
        """Принудительно обновляет snapshot выбранного заказа после изменения коробок."""

        selected = self._selected_order_option()
        if selected is None or not selected.scan_required:
            return
        self._local_pool_loaded = False
        self._download_local_pool_for(selected, force=True)

    def _mark_pending_codes_packed_in_local_pool(self, batch: ScanBatchToBoxResultDto) -> None:
        """Сразу исключает принятые batch-коды из локального snapshot без полного скачивания."""

        package_code = batch.box.sscc or str(batch.box.box_id)
        for item in self._state.pending_items:
            normalized = self._normalize_pool_code(item.raw_code)
            pool_code = self._local_pool_codes.get(normalized)
            if pool_code is None:
                continue
            self._local_pool_codes[normalized] = pool_code.model_copy(
                update={
                    "status": "packed",
                    "package_unit_id": str(batch.box.box_id),
                    "package_code": package_code,
                    "package_status": "open",
                }
            )

    def _download_local_pool_codes(
        self,
        order_id: str,
        download_method: object,
    ) -> dict[str, LocalPoolCodeDto]:
        """Постранично скачивает и нормализует локальный пул кодов заказа."""

        if not callable(download_method):
            return {}
        limit = 5000
        offset = 0
        codes: dict[str, LocalPoolCodeDto] = {}
        while True:
            page = download_method(order_id, limit=limit, offset=offset)
            pool_page = self._expect(page, LocalCodePoolPageDto)
            pool = pool_page.data
            for code in pool.codes:
                normalized = self._normalize_pool_code(code.code)
                if normalized:
                    codes[normalized] = code
            if not pool.has_more or pool.next_offset is None:
                break
            next_offset = int(pool.next_offset)
            if next_offset <= offset:
                break
            offset = next_offset
        return codes

    def _on_local_pool_loaded(self, order_id: str, codes: dict[str, LocalPoolCodeDto]) -> None:
        """Применяет загруженный локальный пул и продолжает открытие коробки при необходимости."""

        self._local_pool_order_id = order_id
        self._local_pool_codes = codes
        self._local_pool_identity_codes = self._index_local_pool_by_identity(codes)
        self._local_pool_loaded = True
        open_after = self._open_box_after_pool_order_id == order_id
        self._open_box_after_pool_order_id = ""
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_message=tr("autoPacking.localPoolLoaded"),
                result_message=tr("autoPacking.localPoolLoadedCount", count=len(codes)),
                error_message="",
            )
        )
        retry_scan = self._retry_scan_after_pool_refresh
        self._retry_scan_after_pool_refresh = ""
        if retry_scan:
            self._handle_single_code_scanned(retry_scan)
            return
        selected = self._selected_order_option()
        if open_after and selected is not None and selected.order_id == order_id:
            self.open_box()

    def _on_local_pool_error(self, exc: Exception) -> None:
        """Показывает ошибку загрузки локального пула заказа."""

        self._local_pool_loaded = False
        self._local_pool_codes.clear()
        self._local_pool_identity_codes.clear()
        self._open_box_after_pool_order_id = ""
        self._retry_scan_after_pool_refresh = ""
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_message=tr("autoPacking.localPoolFailed"),
                error_message=tr("autoPacking.localPoolFailedWithError", error=exc),
            )
        )

    def _is_local_pool_ready_for(self, order_id: str) -> bool:
        """Проверяет, что кэш пула относится к нужному заказу."""

        return self._local_pool_loaded and self._local_pool_order_id == order_id

    def _code_from_selected_local_pool(
        self,
        code: str,
        selected: OrderLineOptionUi | None,
    ) -> str | None:
        """Возвращает нормализованный код, если он есть в пуле выбранного заказа."""

        if selected is None or not self._is_local_pool_ready_for(selected.order_id):
            return code
        normalized, pool_code = self._lookup_local_pool_code(code)
        if pool_code is not None and self._is_pool_code_available(pool_code):
            return self._normalize_pool_code(pool_code.code) or normalized
        if pool_code is not None:
            self._play(SoundEvent.WARNING)
            package_code = pool_code.package_code or pool_code.package_unit_id or ""
            self._set_state(
                replace(
                    self._state,
                    status_message=tr("autoPacking.codeInOtherBox", package_code=package_code),
                    result_message="",
                    error_message=tr("autoPacking.codeInOtherBoxHint"),
                    last_scanned_code=code,
                )
            )
            return None
        self._play(SoundEvent.WARNING)
        self._set_state(
            replace(
                self._state,
                status_message=tr("autoPacking.notInLocalPool"),
                result_message="",
                error_message=tr("autoPacking.notInLocalPoolHint"),
                last_scanned_code=code,
            )
        )
        return None

    def _should_refresh_pool_before_reject(
        self,
        code: str,
        selected: OrderLineOptionUi | None,
    ) -> bool:
        """Обновляет локальный пул один раз перед ошибкой `код не из заказа`."""

        if selected is None or not self._is_local_pool_ready_for(selected.order_id):
            return False
        normalized, pool_code = self._lookup_local_pool_code(code)
        if pool_code is not None:
            return False
        retry_key = normalized or code
        if retry_key in self._pool_miss_retry_codes:
            return False
        self._pool_miss_retry_codes.add(retry_key)
        self._retry_scan_after_pool_refresh = code
        return self._download_local_pool_for(selected, force=True)

    def _lookup_local_pool_code(self, code: str) -> tuple[str, LocalPoolCodeDto | None]:
        """Ищет код в локальном пуле по raw-коду и fallback identity."""

        normalized = self._normalize_pool_code(code)
        pool_code = self._local_pool_codes.get(normalized)
        if pool_code is None:
            pool_code = self._local_pool_identity_codes.get(self._pool_identity_key(code))
        return normalized, pool_code

    @staticmethod
    def _is_pool_code_available(code: LocalPoolCodeDto) -> bool:
        """Проверяет, что код из snapshot еще можно класть в локальную коробку."""

        return (
            code.status not in {"packed", "exported"}
            and not (code.package_code or "").strip()
            and not (code.package_unit_id or "").strip()
        )

    @staticmethod
    def _normalize_pool_code(code: str) -> str:
        """Нормализует код ЧЗ так же, как scanner input, сохраняя fallback для тестовых строк."""

        raw_code = (code or "").strip()
        if not raw_code:
            return ""
        try:
            return parse_marking_code(raw_code).raw_code
        except MarkingCodeParseError:
            return raw_code

    @classmethod
    def _index_local_pool_by_identity(
        cls,
        codes: dict[str, LocalPoolCodeDto],
    ) -> dict[str, LocalPoolCodeDto]:
        """Индексирует локальный пул по GTIN+serial для HID-сканов без GS."""

        indexed: dict[str, LocalPoolCodeDto] = {}
        for code in codes.values():
            identity = cls._pool_identity_key(code.code)
            if identity:
                indexed[identity] = code
        return indexed

    @staticmethod
    def _pool_identity_key(code: str) -> str:
        """Возвращает стабильный ключ GTIN+serial для кода из пула или скана."""

        try:
            return parse_marking_code(code).identity_key
        except MarkingCodeParseError:
            return ""

    def _selected_order_option(self) -> OrderLineOptionUi | None:
        """Возвращает выбранную строку заказа."""

        return self._find_order_option(self._state.selected_order_line_id)

    @staticmethod
    def _order_options_with_selected(
        options: list[OrderLineOptionUi],
        selected: OrderLineOptionUi,
    ) -> list[OrderLineOptionUi]:
        """Добавляет выбранный заказ в список, если страница заказов его не вернула."""

        if any(option.order_line_id == selected.order_line_id for option in options):
            return options
        return [selected, *options]

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

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку backend-сценария."""

        self._active_scan_code = ""
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_message=tr("packing.operationError"),
                error_message=str(exc),
            )
        )

    def _set_busy(self, message: str, last_scanned_code: str | None = None) -> None:
        """Переводит экран в состояние ожидания backend."""

        self._set_state(
            replace(
                self._state,
                is_busy=True,
                status_message=message,
                error_message="",
                last_scanned_code=last_scanned_code or self._state.last_scanned_code,
            )
        )

    def _box_with_count_in_packing(self, count_in_packing: bool) -> PackingBoxUi | None:
        """Возвращает текущую коробку с обновленным флагом учета."""

        if self._state.current_box is None:
            return None
        return replace(self._state.current_box, count_in_packing=count_in_packing)

    @staticmethod
    def _count_in_packing_message(enabled: bool) -> str:
        """Возвращает понятный оператору текст режима учета коробки."""

        if enabled:
            return tr("packing.modeCounted")
        return tr("packing.modeNotCounted")

    def _set_state(self, state: AutoPackingUiState) -> None:
        """Сохраняет и публикует состояние автосканера."""

        self._state = state
        self._rebuild_box_indexes(state.current_box)
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Безопасно проигрывает звуковое событие."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    def _enqueue_scan(self, code: str) -> None:
        """Кладет скан в очередь, если контроллер занят предыдущей операцией."""

        normalized = (code or "").strip()
        if (
            not normalized
            or self._box_contains_accepted_raw_code(normalized)
            or self._is_local_raw_duplicate(normalized)
        ):
            return
        self._scan_queue.append(normalized)
        self._queued_raw_codes.add(normalized)
        if self._should_publish_queue_status():
            self._set_state(
                replace(
                    self._state,
                    result_message=tr("autoPacking.queued", count=len(self._scan_queue)),
                    last_scanned_code=normalized,
                )
            )

    def _process_next_queued_scan(self) -> None:
        """Запускает следующий скан из очереди после завершения операции."""

        if self._state.is_busy or self._state.is_pending_full or not self._scan_queue:
            return
        next_code = self._scan_queue.popleft()
        self._queued_raw_codes.discard(next_code)
        self.on_code_scanned(next_code)

    def _should_publish_queue_status(self) -> bool:
        """Ограничивает частоту UI-обновлений при быстром HID/COM потоке."""

        queued = len(self._scan_queue)
        return queued == 1 or queued % SCAN_QUEUE_STATUS_STEP == 0

    def _is_local_raw_duplicate(self, code: str) -> bool:
        """Проверяет повтор raw-кода в активном скане, очереди и локальном боксе."""

        normalized = code.strip()
        if not normalized:
            return False
        if self._active_scan_code == normalized:
            return True
        if normalized in self._queued_raw_codes:
            return True
        return any(item.raw_code.strip() == normalized for item in self._state.pending_items)

    def _box_contains_code(self, code_id: int) -> bool:
        """Проверяет, лежит ли код уже в текущей открытой коробке."""

        return code_id in self._box_code_ids

    def _is_current_box_duplicate_response(self, verify: VerifyExistsResponseDto) -> bool:
        """Проверяет, что backend сообщил об уже добавленном коде текущей коробки."""

        if verify.code is not None and self._box_contains_code(verify.code.id):
            return True
        message = (verify.message or "").lower()
        return verify.status == "DUPLICATE_SCAN" and "текущей коробке" in message

    def _box_contains_visible_code(self, code: str) -> bool:
        """Проверяет raw-совпадение с кодами, уже показанными в текущей коробке."""

        normalized = code.strip()
        return bool(normalized) and normalized in self._box_visible_codes

    def _box_contains_accepted_raw_code(self, code: str) -> bool:
        """Проверяет raw-код среди уже принятых в текущую коробку пачек."""

        normalized = code.strip()
        if self._state.current_box is None or not normalized:
            return False
        if self._accepted_box_id != self._state.current_box.box_id:
            return False
        return normalized in self._accepted_raw_codes

    def _remember_accepted_batch(
        self,
        current_box: PackingBoxUi | None,
        pending_items: list[AutoPackingBoxItemUi],
    ) -> None:
        """Запоминает raw-коды пачки, которую backend принял в текущую коробку."""

        if current_box is None:
            return
        self._sync_accepted_box(current_box.box_id)
        self._accepted_raw_codes.update(
            item.raw_code.strip() for item in pending_items if item.raw_code.strip()
        )

    def _remember_rejected_current_box_duplicate(self, batch: ScanBatchToBoxResultDto) -> None:
        """Запоминает код, который backend признал дублем текущей коробки."""

        if batch.reason_code not in {"duplicate_in_box", "batch_already_in_box"}:
            return
        rejected_codes = self._rejected_raw_codes(batch)
        if self._state.current_box is None or not rejected_codes:
            return
        self._sync_accepted_box(self._state.current_box.box_id)
        self._accepted_raw_codes.update(rejected_codes)

    def _sync_accepted_box(self, box_id: int) -> None:
        """Сбрасывает raw-кеш при переходе на другую коробку."""

        if self._accepted_box_id == box_id:
            return
        self._accepted_box_id = box_id
        self._accepted_raw_codes.clear()

    def _forget_accepted_codes_after_box_edit(self) -> None:
        """Сбрасывает raw-кеш после ручного изменения коробки."""

        self._accepted_raw_codes.clear()

    def _forget_accepted_codes(self) -> None:
        """Полностью сбрасывает raw-кеш принятой коробки."""

        self._accepted_box_id = None
        self._accepted_raw_codes.clear()
        self._scan_queue.clear()
        self._queued_raw_codes.clear()

    def _continue_after_batch(self, batch: ScanBatchToBoxResultDto) -> None:
        """Продолжает очередь сканов или обновляет детали коробки, когда поток стих."""

        if self._scan_queue:
            self._process_next_queued_scan()
            return
        if not self._should_refresh_current_box_after_batch(batch):
            return
        self._refresh_current_box_after_batch()

    @staticmethod
    def _should_refresh_current_box_after_batch(batch: ScanBatchToBoxResultDto) -> bool:
        """Ограничивает detail-refresh, чтобы быстрый автосканер не удваивал HTTP-поток."""

        if batch.added != 1:
            return True
        capacity = batch.box.capacity
        if capacity > 0 and batch.box.filled >= capacity:
            return True
        return batch.box.filled > 0 and batch.box.filled % 10 == 0

    def _refresh_current_box_after_batch(self) -> None:
        """Фоново обновляет подробности коробки, не блокируя следующие сканы."""

        self._task_runner.submit(
            self._packing_service.current_box,
            self._on_current_box_refreshed_after_batch,
            self._on_background_refresh_error,
        )

    def _on_current_box_refreshed_after_batch(self, result: object) -> None:
        """Применяет неблокирующий refresh, если экран уже не занят следующей пачкой."""

        if self._state.is_busy or self._state.pending_items or result is None:
            return
        detail = self._expect(result, BoxDetailDto)
        if self._state.current_box is not None and detail.box_id != self._state.current_box.box_id:
            return
        self._sync_accepted_box(detail.box_id)
        self._set_state(
            replace(
                self._state,
                current_box=self._box_to_ui(detail),
                count_in_packing=detail.count_in_packing,
            )
        )

    @staticmethod
    def _on_background_refresh_error(exc: Exception) -> None:
        """Логирует ошибку фонового refresh без остановки автоскана."""

        logger.debug("Auto packing background current-box refresh failed: %s", exc)

    def _rebuild_box_indexes(self, box: PackingBoxUi | None) -> None:
        """Обновляет O(1)-индексы кодов текущей коробки."""

        if box is None:
            self._box_code_ids.clear()
            self._box_visible_codes.clear()
            return
        self._box_code_ids = {item.code_id for item in box.items}
        self._box_visible_codes = {
            item.visible_code.strip() for item in box.items if item.visible_code.strip()
        }

    def _pending_without_known_box_duplicates(self) -> list[AutoPackingBoxItemUi]:
        """Удаляет из локального бокса коды, которые уже видны в текущей коробке."""

        if self._state.current_box is None:
            return self._state.pending_items
        box_code_ids = {item.code_id for item in self._state.current_box.items}
        if not box_code_ids:
            return self._state.pending_items
        return [item for item in self._state.pending_items if item.code_id not in box_code_ids]

    def _pending_without_rejected_batch_item(
        self,
        batch: ScanBatchToBoxResultDto,
    ) -> list[AutoPackingBoxItemUi]:
        """Удаляет из локального бокса только коды, которые backend отклонил."""

        rejected_code_ids = set(batch.rejected_code_ids)
        if batch.rejected_code_id is not None:
            rejected_code_ids.add(batch.rejected_code_id)
        rejected_raw_codes = self._rejected_raw_codes(batch)
        if not rejected_code_ids and not rejected_raw_codes:
            return self._pending_without_known_box_duplicates()
        return [
            item
            for item in self._state.pending_items
            if item.code_id not in rejected_code_ids
            and item.raw_code.strip() not in rejected_raw_codes
        ]

    def _merge_box_summary(self, box: BoxDto) -> PackingBoxUi:
        """Обновляет сводку коробки, не затирая локальный список кодов."""

        if self._state.current_box is None or self._state.current_box.box_id != box.box_id:
            return self._box_to_ui(box)
        current = self._state.current_box
        return replace(
            current,
            order_name=box.order_name or current.order_name,
            sscc=box.sscc or current.sscc,
            filled=box.filled,
            capacity=box.capacity,
            count_in_packing=box.count_in_packing,
            is_closed=box.is_closed,
        )

    @staticmethod
    def _batch_error_message(message: str, batch: ScanBatchToBoxResultDto) -> str:
        """Формирует понятную ошибку пачки с проблемным кодом."""

        package_code = str(batch.details.get("package_code") or "").strip()
        if package_code and batch.reason_code == "code_in_other_box":
            message = tr("autoPacking.codeInOtherBox", package_code=package_code)
        rejected = batch.rejected_raw_code or ""
        rejected_codes = sorted(AutoPackingController._rejected_raw_codes(batch))
        if rejected_codes:
            codes_preview = ", ".join(rejected_codes[:3])
            if len(rejected_codes) > 3:
                codes_preview = f"{codes_preview} и еще {len(rejected_codes) - 3}"
            return f"{message}. Удалено из автоскана-бокса: {codes_preview}"
        if rejected:
            return f"{message}. Код удален из автоскана-бокса: {rejected}"
        return message

    @staticmethod
    def _rejected_raw_codes(batch: ScanBatchToBoxResultDto) -> set[str]:
        """Возвращает набор raw-кодов, которые backend попросил убрать из ВБ."""

        rejected_codes = {code.strip() for code in batch.rejected_raw_codes if code.strip()}
        single_code = (batch.rejected_raw_code or "").strip()
        if single_code:
            rejected_codes.add(single_code)
        return rejected_codes

    @staticmethod
    def _close_event(
        result: CloseBoxResultDto,
        print_result: PackageLabelPrintResultDto | None = None,
    ) -> CloseBoxUiEvent:
        """Преобразует backend-результат закрытия в UI-событие."""

        return PackingController._close_event(result, print_result)

    @staticmethod
    def _box_to_ui(box: BoxDto | BoxDetailDto) -> PackingBoxUi:
        """Преобразует DTO коробки в UI-модель."""

        items = []
        if isinstance(box, BoxDetailDto):
            items = [
                PackingItemUi(
                    id=item.id,
                    code_id=item.code_id,
                    gtin=item.gtin,
                    serial=item.serial,
                    visible_code=item.visible_code,
                )
                for item in box.items
            ]
        return PackingBoxUi(
            box_id=box.box_id,
            order_name=box.order_name or "Заказ не определен",
            sscc=box.sscc or "",
            filled=box.filled,
            capacity=box.capacity,
            count_in_packing=box.count_in_packing,
            is_closed=box.is_closed,
            items=items,
        )

    @staticmethod
    def _expect(
        result: object,
        expected_type: type[TAutoPackingResult],
    ) -> TAutoPackingResult:
        """Проверяет тип результата фоновой операции."""

        if not isinstance(result, expected_type):
            raise TypeError(f"Неожиданный результат операции: {type(result)!r}")
        return result

    @staticmethod
    def _status_for_edit_reason(reason_code: str) -> str:
        """Возвращает статус быстрой правки коробки по reason_code."""

        messages = {
            "item_removed": "Код удален из коробки",
            "box_cleared": "Коробка очищена",
        }
        return messages.get(reason_code, reason_code)
