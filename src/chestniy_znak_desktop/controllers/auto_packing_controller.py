"""Контроллер упаковки через автосканер мультиплат."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Protocol, TypeVar

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxDto,
    OpenBoxResultDto,
    ScanBatchToBoxResultDto,
)
from chestniy_znak_desktop.api.models.verify import VerifyExistsResponseDto
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.packing_controller import PackingBoxUi, PackingItemUi
from chestniy_znak_desktop.runtime.task_runner import TaskRunner
from chestniy_znak_desktop.services.sound_service import SoundEvent

TAutoPackingResult = TypeVar("TAutoPackingResult")


class AutoPackingBackend(Protocol):
    """Контракт backend-сервиса коробок для автосканера."""

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую открытую коробку."""

    def open_box(self, device_id: str, count_in_packing: bool = True) -> OpenBoxResultDto:
        """Открывает новую коробку."""

    def scan_batch_to_box(
        self,
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Атомарно добавляет пачку кодов в коробку."""


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
    status_message: str = "Открытая коробка не найдена"
    result_message: str = ""
    error_message: str = ""
    last_scanned_code: str = ""

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

    def __init__(
        self,
        packing_service: AutoPackingBackend,
        verify_service: AutoPackingVerifier,
        box_edit_service: AutoPackingBoxEditor | None,
        task_runner: TaskRunner,
        settings_store: SettingsStore,
        settings_defaults: AppConfig,
        device_id: str,
        scanner_id: str = "desktop-com",
        ws_verify_service: AutoPackingWsVerifier | None = None,
        sound_service: SoundPlayer | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер автосканерной упаковки."""

        super().__init__(parent)
        self._packing_service = packing_service
        self._verify_service = verify_service
        self._box_edit_service = box_edit_service
        self._task_runner = task_runner
        self._settings_store = settings_store
        self._settings_defaults = settings_defaults
        self._device_id = device_id
        self._scanner_id = scanner_id
        self._ws_verify_service = ws_verify_service
        self._sound_service = sound_service
        self._scan_queue: list[str] = []
        self._active_scan_code = ""
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

        self._set_busy("Загружаем текущую коробку...")
        self._task_runner.submit(
            self._packing_service.current_box,
            self._on_current_box_loaded,
            self._on_error,
        )

    def open_box(self) -> None:
        """Открывает коробку для приема заполненных автоскана-боксов."""

        if self._state.is_busy:
            return
        self._set_busy("Открываем коробку...")
        self._task_runner.submit(
            lambda: self._packing_service.open_box(device_id=self._device_id),
            self._on_box_opened,
            self._on_error,
        )

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
                status_message="Вместимость автоскана-бокса обновлена",
                result_message=f"Ожидаем {value} код(ов) на изделие",
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
                status_message="Автоскана-бокс очищен",
                result_message="Можно сканировать изделие заново",
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
                status_message="Код удален из автоскана-бокса",
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
        self._set_busy(f"Удаляем код #{item_id} из коробки #{box_id}...")
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
        self._set_busy(f"Очищаем коробку #{box_id}...")
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
        self._set_busy(f"Удаляем пустую коробку #{box_id}...")
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
        if self._box_contains_visible_code(normalized):
            self._set_state(
                replace(
                    self._state,
                    status_message="Код уже есть в текущей коробке",
                    result_message="Повторный скан пропущен",
                    error_message="",
                    last_scanned_code=normalized,
                )
            )
            return
        if self._is_local_raw_duplicate(normalized):
            self._set_state(
                replace(
                    self._state,
                    result_message="Повторный скан уже есть в автоскана-боксе или очереди",
                    error_message="Дубль локального бокса не добавлен",
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
                    status_message="Сначала откройте коробку",
                    error_message="Открытая коробка не найдена",
                    last_scanned_code=normalized,
                )
            )
            return
        if self._state.is_pending_full:
            self._set_state(
                replace(
                    self._state,
                    status_message="Автоскана-бокс уже заполнен",
                    error_message="Дождитесь отправки пачки или очистите бокс",
                    last_scanned_code=normalized,
                )
            )
            return
        self._add_code_to_pending(normalized)

    def _verify_code_http(self, code: str) -> None:
        """Проверяет код через HTTP, если WS недоступен или не ответил."""

        self._set_busy("Проверяем код через HTTP...", code)
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
            serial="Ожидает проверки",
            visible_code=raw_code,
            order_key="Проверка при отправке",
        )
        pending_items = [*self._state.pending_items, item]
        next_state = replace(
            self._state,
            is_busy=False,
            pending_items=pending_items,
            status_message="Код добавлен в автоскана-бокс",
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
                        status_message="Код уже есть в текущей коробке",
                        result_message="Повторный скан пропущен",
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
                    status_message="Код не прошел проверку",
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
                    status_message="Код уже есть в текущей коробке",
                    result_message="Повторный скан пропущен",
                    error_message="",
                    last_scanned_code=raw_code,
                )
            )
            self._process_next_queued_scan()
            return

        order_key = (verify.code.order_dnp_name or verify.order_name or "").strip()
        if not order_key or order_key == "Не привязан":
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message="Код не добавлен в автоскана-бокс",
                    error_message="Код не привязан к заказу",
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
                    status_message="Повтор в автоскана-боксе",
                    error_message="Этот код уже есть в локальном боксе",
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
                    status_message="Код другого заказа",
                    error_message="В автоскана-боксе могут быть коды только одного заказа",
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
            status_message="Код добавлен в автоскана-бокс",
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
        self._set_busy("Автоскана-бокс заполнен. Добавляем пачку в коробку...")
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
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    pending_items=pending_items,
                    current_box=self._merge_box_summary(batch.box),
                    status_message="Пачка не добавлена",
                    result_message=(
                        f"В автоскана-боксе осталось: {len(pending_items)}"
                        if len(pending_items) != len(self._state.pending_items)
                        else self._state.result_message
                    ),
                    error_message=self._batch_error_message(message, batch),
                )
            )
            return
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                pending_items=[],
                current_box=self._merge_box_summary(batch.box),
                status_message="Пачка добавлена в коробку",
                result_message=f"Добавлено кодов: {batch.added}",
                error_message="",
            )
        )
        self._play(SoundEvent.OK)
        self.refresh_current_box()

    def _on_box_edit_result(self, result: object) -> None:
        """Обрабатывает быструю правку текущей коробки автоскана."""

        edit_result = self._expect(result, BoxActionResultDto)
        message = edit_result.error or edit_result.reason_code
        if not edit_result.ok:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    status_message="Коробка не изменена",
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
                    status_message="Коробка не удалена",
                    error_message=message,
                )
            )
            return
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=None,
                status_message="Пустая коробка удалена",
                result_message=message,
                error_message="",
            )
        )

    def _on_current_box_loaded(self, result: object) -> None:
        """Обрабатывает загрузку текущей коробки."""

        if result is None:
            self._set_state(
                replace(
                    self._state,
                    is_busy=False,
                    current_box=None,
                    status_message="Открытая коробка не найдена",
                )
            )
            return
        detail = self._expect(result, BoxDetailDto)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(detail),
                status_message="Коробка загружена",
                error_message="",
            )
        )
        self._process_next_queued_scan()

    def _on_box_opened(self, result: object) -> None:
        """Обрабатывает открытие коробки."""

        opened = self._expect(result, OpenBoxResultDto)
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                current_box=self._box_to_ui(opened.box),
                status_message=(
                    "Коробка открыта" if opened.created else "Активная коробка уже была открыта"
                ),
                result_message=f"Коробка #{opened.box.box_id}",
                error_message="",
            )
        )
        self._process_next_queued_scan()

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку backend-сценария."""

        self._active_scan_code = ""
        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_message="Ошибка операции",
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

    def _set_state(self, state: AutoPackingUiState) -> None:
        """Сохраняет и публикует состояние автосканера."""

        self._state = state
        self.state_changed.emit(state)

    def _play(self, event: SoundEvent) -> None:
        """Безопасно проигрывает звуковое событие."""

        if self._sound_service is not None:
            self._sound_service.play(event)

    def _enqueue_scan(self, code: str) -> None:
        """Кладет скан в очередь, если контроллер занят предыдущей операцией."""

        normalized = (code or "").strip()
        if not normalized or self._is_local_raw_duplicate(normalized):
            return
        self._scan_queue.append(normalized)
        self._set_state(
            replace(
                self._state,
                result_message=f"Сканов в очереди: {len(self._scan_queue)}",
                last_scanned_code=normalized,
            )
        )

    def _process_next_queued_scan(self) -> None:
        """Запускает следующий скан из очереди после завершения операции."""

        if self._state.is_busy or self._state.is_pending_full or not self._scan_queue:
            return
        next_code = self._scan_queue.pop(0)
        self.on_code_scanned(next_code)

    def _is_local_raw_duplicate(self, code: str) -> bool:
        """Проверяет повтор raw-кода в активном скане, очереди и локальном боксе."""

        normalized = code.strip()
        if not normalized:
            return False
        if self._active_scan_code == normalized:
            return True
        if normalized in self._scan_queue:
            return True
        return any(item.raw_code.strip() == normalized for item in self._state.pending_items)

    def _box_contains_code(self, code_id: int) -> bool:
        """Проверяет, лежит ли код уже в текущей открытой коробке."""

        if self._state.current_box is None:
            return False
        return any(item.code_id == code_id for item in self._state.current_box.items)

    def _is_current_box_duplicate_response(self, verify: VerifyExistsResponseDto) -> bool:
        """Проверяет, что backend сообщил об уже добавленном коде текущей коробки."""

        if verify.code is not None and self._box_contains_code(verify.code.id):
            return True
        message = (verify.message or "").lower()
        return verify.status == "DUPLICATE_SCAN" and "текущей коробке" in message

    def _box_contains_visible_code(self, code: str) -> bool:
        """Проверяет raw-совпадение с кодами, уже показанными в текущей коробке."""

        normalized = code.strip()
        if self._state.current_box is None or not normalized:
            return False
        return any(
            item.visible_code.strip() == normalized for item in self._state.current_box.items
        )

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
        """Удаляет из локального бокса только код, который backend отклонил."""

        rejected_code_id = batch.rejected_code_id
        rejected_raw_code = (batch.rejected_raw_code or "").strip()
        if rejected_code_id is None and not rejected_raw_code:
            return self._pending_without_known_box_duplicates()
        return [
            item
            for item in self._state.pending_items
            if item.code_id != rejected_code_id and item.raw_code.strip() != rejected_raw_code
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
            print_ok=box.print_ok,
            print_error=box.print_error,
        )

    @staticmethod
    def _batch_error_message(message: str, batch: ScanBatchToBoxResultDto) -> str:
        """Формирует понятную ошибку пачки с проблемным кодом."""

        rejected = batch.rejected_raw_code or ""
        if rejected:
            return f"{message}. Код удален из автоскана-бокса: {rejected}"
        return message

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
            print_ok=box.print_ok,
            print_error=box.print_error,
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
