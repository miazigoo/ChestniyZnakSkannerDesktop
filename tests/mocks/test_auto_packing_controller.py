"""Mock-тесты контроллера автоупаковки."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from chestniy_znak_desktop.api.models.orders import (
    LocalCodePoolDto,
    LocalCodePoolPageDto,
    LocalPoolCodeDto,
    OrderLineDto,
    OrderProductDto,
    WorkOrderDto,
    WorkOrderPageDto,
)
from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxDto,
    BoxItemDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanBatchToBoxResultDto,
)
from chestniy_znak_desktop.api.models.verify import RemoteCodeDto, VerifyExistsResponseDto
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.auto_packing_controller import AutoPackingController
from chestniy_znak_desktop.controllers.packing_controller import CloseBoxUiEvent
from chestniy_znak_desktop.services.sound_service import SoundEvent


class ImmediateTaskRunner:
    """TaskRunner, который выполняет задачу сразу."""

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Синхронно выполняет задачу."""

        try:
            result = task()
        except Exception as exc:
            on_error(exc)
            return
        on_success(result)


class ManualTaskRunner:
    """TaskRunner, который выполняет задачи по команде теста."""

    def __init__(self) -> None:
        """Создает пустую очередь задач."""

        self.tasks: list[
            tuple[
                Callable[[], object],
                Callable[[object], None],
                Callable[[Exception], None],
            ]
        ] = []

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Кладет задачу в очередь без немедленного выполнения."""

        self.tasks.append((task, on_success, on_error))

    def run_next(self) -> None:
        """Выполняет следующую задачу и вызывает нужный callback."""

        task, on_success, on_error = self.tasks.pop(0)
        try:
            result = task()
        except Exception as exc:
            on_error(exc)
            return
        on_success(result)


class FakeSoundService:
    """Fake sound service для проверки звуковых событий."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


class FakeSignal:
    """Минимальная замена Qt Signal для fake WS-сервиса."""

    def __init__(self) -> None:
        """Создает пустой список подписчиков."""

        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        """Подписывает callback на событие."""

        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        """Вызывает всех подписчиков с переданными аргументами."""

        for callback in self._callbacks:
            callback(*args)


class FakeWsVerifyService:
    """Fake WebSocket-проверка автоскана."""

    def __init__(self) -> None:
        """Создает fake-сервис с сигналами ответа."""

        self.verified = FakeSignal()
        self.failed = FakeSignal()
        self.calls: list[tuple[str, int | None]] = []

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        box_id: int | None = None,
    ) -> str | None:
        """Запоминает WS-запрос и возвращает request_id."""

        self.calls.append((code, box_id))
        return f"ws-{len(self.calls)}"


class FakePackingService:
    """Fake backend коробок для автоупаковки."""

    def __init__(self) -> None:
        """Создает fake-сервис с состоянием вызовов."""

        self.current_box_result: BoxDetailDto | None = None
        self.batch_calls: list[tuple[int, list[str], str]] = []
        self.close_calls: list[tuple[int, str]] = []
        self.count_calls: list[tuple[int, bool]] = []
        self.open_calls: list[tuple[str, bool, str | None, str | None]] = []

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую коробку."""

        return self.current_box_result

    def open_box(
        self,
        device_id: str,
        count_in_packing: bool = True,
        order_id: str | None = None,
        order_line_id: str | None = None,
        code_value: str | None = None,
        sscc: str | None = None,
    ) -> OpenBoxResultDto:
        """Возвращает открытую коробку."""

        self.open_calls.append((device_id, count_in_packing, order_id, order_line_id))
        return OpenBoxResultDto(
            ok=True,
            created=True,
            has_active_boxes=False,
            box=_box(filled=0, count_in_packing=count_in_packing),
        )

    def scan_batch_to_box(
        self,
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Запоминает пачку и возвращает обновленную коробку."""

        self.batch_calls.append((box_id, codes, scanner_id))
        self.current_box_result = BoxDetailDto(
            **_box(filled=len(codes)).model_dump(),
            items=[
                BoxItemDto(
                    id=index,
                    code_id=index,
                    scan_id=index,
                    gtin="04646151697261",
                    serial=f"SERIAL{index}",
                    visible_code=code,
                )
                for index, code in enumerate(codes, start=1)
            ],
        )
        return ScanBatchToBoxResultDto(
            ok=True,
            reason_code="batch_added",
            added=len(codes),
            box=_box(filled=len(codes)),
        )

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Запоминает закрытие коробки и возвращает успешный результат."""

        self.close_calls.append((box_id, device_id))
        return CloseBoxResultDto(
            ok=True,
            reason_code="box_closed",
            box=_box(filled=12, capacity=12),
        )

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Запоминает переключение учета коробки."""

        self.count_calls.append((box_id, count_in_packing))
        return BoxActionResultDto(
            ok=True,
            reason_code="count_in_packing_updated",
            box=_box(count_in_packing=count_in_packing),
        )


class FakeVerifyService:
    """Fake проверка кодов для локального бокса."""

    def __init__(self) -> None:
        """Создает счетчик проверок."""

        self.calls: list[str] = []
        self._ids_by_code: dict[str, int] = {}

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        save_scan: bool = True,
    ) -> VerifyExistsResponseDto:
        """Возвращает успешную проверку с одним заказом."""

        self.calls.append(code)
        code_id = self._ids_by_code.setdefault(code, self._code_id_for(code))
        return VerifyExistsResponseDto(
            ok=True,
            exists=True,
            status="ok",
            message="Код найден",
            order_name="26-0001/0001",
            code=RemoteCodeDto(
                id=code_id,
                gtin="04646151697261",
                serial=f"SERIAL{code_id}",
                visible_code=code,
                order_dnp_name="26-0001/0001",
            ),
        )

    def _code_id_for(self, code: str) -> int:
        """Возвращает стабильный ID кода для fake-проверки."""

        suffix = code.removeprefix("CODE")
        if suffix.isdigit():
            return int(suffix)
        return len(self._ids_by_code) + 1


class FakeBoxEditService:
    """Fake backend быстрых правок коробки в автоупаковке."""

    def __init__(self, packing_service: FakePackingService) -> None:
        """Создает fake-сервис поверх состояния fake упаковки."""

        self._packing_service = packing_service
        self.remove_calls: list[tuple[int, int]] = []
        self.clear_calls: list[int] = []
        self.delete_calls: list[int] = []

    def remove_item(self, box_id: int, item_id: int) -> BoxActionResultDto:
        """Удаляет один fake-код из текущей коробки."""

        self.remove_calls.append((box_id, item_id))
        box = self._packing_service.current_box_result or _detail_box(items_count=2)
        items = [item for item in box.items if item.id != item_id]
        self._packing_service.current_box_result = _detail_box(items_count=len(items))
        return BoxActionResultDto(
            ok=True,
            reason_code="item_removed",
            box=_box(filled=len(items)),
        )

    def clear_box(self, box_id: int) -> BoxActionResultDto:
        """Очищает fake-коробку."""

        self.clear_calls.append(box_id)
        self._packing_service.current_box_result = _detail_box(items_count=0)
        return BoxActionResultDto(
            ok=True,
            reason_code="box_cleared",
            box=_box(filled=0),
        )

    def delete_empty_box(self, box_id: int) -> BoxActionResultDto:
        """Удаляет fake-пустую коробку."""

        self.delete_calls.append(box_id)
        self._packing_service.current_box_result = None
        return BoxActionResultDto(
            ok=True,
            reason_code="box_deleted",
            box=_box(filled=0),
        )


class FakeOrderService:
    """Fake сервис рабочих заказов для проверки выбора номенклатуры."""

    def __init__(self, page: WorkOrderPageDto, pool_codes: list[str] | None = None) -> None:
        """Создает сервис с фиксированной страницей заказов."""

        self.page = page
        self.pool_codes = pool_codes
        self.pool_calls: list[tuple[str, int, int]] = []

    def list_orders(
        self,
        status: str | None = None,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> WorkOrderPageDto:
        """Возвращает заданную страницу заказов."""

        return self.page

    def download_local_pool(
        self,
        order_id: str,
        limit: int = 5000,
        offset: int = 0,
    ) -> LocalCodePoolPageDto:
        """Возвращает локальный пул кодов выбранного заказа."""

        self.pool_calls.append((order_id, limit, offset))
        codes = self.pool_codes or []
        page_codes = codes[offset : offset + limit]
        next_offset = offset + limit if offset + limit < len(codes) else None
        return LocalCodePoolPageDto(
            data=LocalCodePoolDto(
                order=self.page.data[0],
                codes=[
                    LocalPoolCodeDto(
                        id=f"code-{index}",
                        code=code,
                        status="issued",
                    )
                    for index, code in enumerate(page_codes, start=offset + 1)
                ],
                total=len(codes),
                count=len(page_codes),
                limit=limit,
                offset=offset,
                next_offset=next_offset,
                has_more=next_offset is not None,
            )
        )


def _box(
    *,
    filled: int = 0,
    capacity: int = 20,
    count_in_packing: bool = True,
) -> BoxDto:
    """Создает DTO коробки для тестов."""

    return BoxDto(
        box_id=1,
        order_name="26-0001/0001",
        sscc="",
        capacity=capacity,
        filled=filled,
        count_in_packing=count_in_packing,
        allow_duplicate_scans=False,
        is_closed=False,
        is_edit_mode=False,
    )


def _work_order(*, scan_required: bool = True) -> WorkOrderPageDto:
    """Создает страницу с одной активной строкой заказа."""

    return WorkOrderPageDto(
        data=[
            WorkOrderDto(
                id="order-1",
                plant_id="plant-1",
                supplier_id="supplier-1",
                order_number="ORDER-1",
                status="issued_to_supplier",
                scan_required=scan_required,
                lines=[
                    OrderLineDto(
                        id="line-1",
                        order_id="order-1",
                        product_id="product-1",
                        quantity=10,
                        required_code_quantity=10,
                        status="active",
                        product=OrderProductDto(
                            id="product-1",
                            sku="SKU-1",
                            name="Номенклатура 1",
                        ),
                    ),
                ],
            )
        ],
    )


def _detail_box(*, items_count: int = 2) -> BoxDetailDto:
    """Создает детальную DTO коробки с кодами для тестов."""

    return BoxDetailDto(
        **_box(filled=items_count).model_dump(),
        items=[
            BoxItemDto(
                id=index,
                code_id=index,
                scan_id=index,
                gtin="04646151697261",
                serial=f"SERIAL{index}",
                visible_code=f"CODE{index}",
            )
            for index in range(1, items_count + 1)
        ],
    )


def _controller_pair(
    tmp_path: Path,
) -> tuple[AutoPackingController, FakePackingService, FakeVerifyService, FakeSoundService]:
    """Создает контроллер с fake-зависимостями."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    sounds = FakeSoundService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
        sound_service=sounds,
    )
    return controller, service, verifier, sounds


def test_auto_packing_sends_batch_only_when_local_box_is_full(tmp_path: Path) -> None:
    """Проверяет отправку пачки только после заполнения локального бокса."""

    controller, service, _verifier, sounds = _controller_pair(tmp_path)
    controller.open_box()
    controller.set_codes_per_item(2)
    controller.on_code_scanned("CODE1")

    assert controller.state.pending_count == 1
    assert service.batch_calls == []

    controller.on_code_scanned("CODE2")

    assert controller.state.pending_count == 0
    assert service.batch_calls == [(1, ["CODE1", "CODE2"], "desktop-com")]
    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 2
    assert len(controller.state.current_box.items) == 2
    assert sounds.events == [SoundEvent.OK]


def test_auto_packing_splits_glued_gs1_codes(tmp_path: Path) -> None:
    """Проверяет разделение двух DataMatrix, склеенных HID-вводом."""

    controller, service, _verifier, sounds = _controller_pair(tmp_path)
    code1 = "0104646151697261215WsaP?q-'MzgeTtRBYt"
    code2 = '01046461516972612158h"-QaBSDXPDPMrMBXP93LtwN'
    controller.open_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned(code1 + code2)

    assert controller.state.pending_count == 0
    assert service.batch_calls == [(1, [code1, code2], "desktop-com")]
    assert sounds.events == [SoundEvent.OK]


def test_auto_packing_rejects_truncated_numeric_tail(tmp_path: Path) -> None:
    """Проверяет, что хвост DataMatrix без начала не попадает в ВБ."""

    controller, service, _verifier, sounds = _controller_pair(tmp_path)
    controller.open_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned('1215+"D(vJVn,zB?qKXlgXr93TgSh')

    assert controller.state.pending_count == 0
    assert service.batch_calls == []
    assert sounds.events == [SoundEvent.WARNING]
    assert "обрезанный DataMatrix" in controller.state.error_message


def test_auto_packing_sends_batch_after_capacity_reduction(tmp_path: Path) -> None:
    """Проверяет отправку ВБ, который стал полным после смены вместимости."""

    controller, service, _verifier, sounds = _controller_pair(tmp_path)
    controller.open_box()
    controller.set_codes_per_item(12)

    for index in range(13, 19):
        controller.on_code_scanned(f"CODE{index}")

    assert controller.state.pending_count == 6
    assert service.batch_calls == []

    controller.set_codes_per_item(6)

    assert controller.state.pending_count == 0
    assert service.batch_calls == [
        (
            1,
            ["CODE13", "CODE14", "CODE15", "CODE16", "CODE17", "CODE18"],
            "desktop-com",
        )
    ]
    assert sounds.events == [SoundEvent.OK]


def test_auto_packing_closes_current_box(tmp_path: Path) -> None:
    """Проверяет закрытие текущей коробки из сценария автоскана."""

    controller, service, _verifier, sounds = _controller_pair(tmp_path)
    events: list[CloseBoxUiEvent] = []
    controller.close_completed.connect(events.append)
    controller.open_box()

    controller.close_current_box()

    assert service.close_calls == [(1, "pc-1")]
    assert controller.state.current_box is None
    assert len(events) == 1
    assert events[0].ok is True
    assert sounds.events == [SoundEvent.VICTORY]


def test_auto_packing_uses_count_flag_when_opening_box(tmp_path: Path) -> None:
    """Проверяет, что чекбокс учета влияет на открытие коробки автоскана."""

    controller, _service, _verifier, _sounds = _controller_pair(tmp_path)
    controller.set_count_in_packing(False)

    controller.open_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.count_in_packing is False
    assert controller.state.count_in_packing is False


def test_auto_packing_updates_count_flag_for_open_box(tmp_path: Path) -> None:
    """Проверяет переключение учета уже открытой коробки автоскана."""

    controller, service, _verifier, _sounds = _controller_pair(tmp_path)
    controller.open_box()

    controller.set_count_in_packing(False)

    assert service.count_calls == [(1, False)]
    assert controller.state.current_box is not None
    assert controller.state.current_box.count_in_packing is False
    assert controller.state.count_in_packing is False
    assert controller.state.status_message == "Учет коробки обновлен"
    assert controller.state.result_message == "Без учета упаковки"


def test_auto_packing_blocks_box_for_no_scan_order(tmp_path: Path) -> None:
    """Проверяет, что автоупаковка не открывает коробку для заказа без сканирования."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    sounds = FakeSoundService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        order_service=FakeOrderService(_work_order(scan_required=False)),
        scanner_id="desktop-com",
        sound_service=sounds,
    )

    controller.refresh_orders()
    controller.open_box()

    assert controller.state.selected_order_scan_required is False
    assert service.open_calls == []
    assert controller.state.status_message == "Сканирование по заказу отключено"
    assert "web-кабинете поставщика" in controller.state.result_message
    assert sounds.events == [SoundEvent.WARNING]


def test_auto_packing_accepts_only_downloaded_local_pool_codes(tmp_path: Path) -> None:
    """Проверяет, что Desktop сканирует только коды из скачанного пула заказа."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    sounds = FakeSoundService()
    order_service = FakeOrderService(_work_order(), pool_codes=["CODE1"])
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        order_service=order_service,
        scanner_id="desktop-com",
        sound_service=sounds,
    )

    controller.refresh_orders()
    controller.open_box()
    controller.set_codes_per_item(2)
    controller.on_code_scanned("CODE1")
    controller.on_code_scanned("CODE2")

    assert order_service.pool_calls == [("order-1", 5000, 0)]
    assert [item.raw_code for item in controller.state.pending_items] == ["CODE1"]
    assert service.batch_calls == []
    assert verifier.calls == []
    assert controller.state.status_message == "Код не относится к выбранному заказу"
    assert "не будет добавлен" in controller.state.error_message
    assert sounds.events == [SoundEvent.WARNING]


def test_auto_packing_queues_fast_scans_while_batch_is_busy(tmp_path: Path) -> None:
    """Проверяет очередь быстрых HID-сканов во время отправки ВБ."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    sounds = FakeSoundService()
    runner = ManualTaskRunner()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=runner,
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
        sound_service=sounds,
    )
    controller.open_box()
    runner.run_next()
    controller.set_codes_per_item(1)

    controller.on_code_scanned("CODE1")
    controller.on_code_scanned("CODE2")

    assert len(runner.tasks) == 1
    assert bool(controller.state.is_busy)
    assert controller.state.result_message == "Сканов в очереди: 1"

    runner.run_next()

    assert len(runner.tasks) == 1
    assert verifier.calls == []
    assert service.batch_calls == [(1, ["CODE1"], "desktop-com")]

    runner.run_next()

    assert len(runner.tasks) == 1
    assert not bool(controller.state.is_busy)
    runner.run_next()

    assert controller.state.pending_count == 0
    assert service.batch_calls == [
        (1, ["CODE1"], "desktop-com"),
        (1, ["CODE2"], "desktop-com"),
    ]
    assert controller.state.current_box is not None
    assert controller.state.is_busy is False


def test_auto_packing_does_not_preverify_before_local_box_is_full(tmp_path: Path) -> None:
    """Проверяет, что автоскан не дергает verify до отправки полного ВБ."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    ws_verifier = FakeWsVerifyService()
    sounds = FakeSoundService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
        ws_verify_service=ws_verifier,
        sound_service=sounds,
    )
    controller.open_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned("CODE1")

    assert ws_verifier.calls == []
    assert verifier.calls == []
    assert service.batch_calls == []
    assert controller.state.pending_count == 1
    assert sounds.events == []


def test_auto_packing_ignores_ws_failures_without_active_precheck(tmp_path: Path) -> None:
    """Проверяет, что WS-failure не влияет на ВБ без предварительной проверки."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    ws_verifier = FakeWsVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
        ws_verify_service=ws_verifier,
    )
    controller.open_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned("CODE1")
    ws_verifier.failed.emit("ws-1", "CODE1", "timeout")

    assert verifier.calls == []
    assert controller.state.pending_count == 1


def test_auto_packing_does_not_use_ws_duplicate_for_local_box(tmp_path: Path) -> None:
    """Проверяет, что старые WS-ответы не меняют ВБ без active request."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    ws_verifier = FakeWsVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
        ws_verify_service=ws_verifier,
    )
    controller.open_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned("CODE1")
    result = VerifyExistsResponseDto(
        ok=False,
        exists=True,
        status="DUPLICATE_SCAN",
        message="Код уже лежит в текущей коробке",
        order_name="26-0001/0001",
        code=RemoteCodeDto(
            id=777,
            gtin="04646151697261",
            serial="SERIAL777",
            visible_code="CODE1",
            order_dnp_name="26-0001/0001",
        ),
    )
    ws_verifier.verified.emit("ws-1", "CODE1", result)

    assert controller.state.pending_count == 1
    assert service.batch_calls == []
    assert controller.state.error_message == ""
    assert controller.state.result_message == "1 / 2"


def test_auto_packing_drops_duplicate_raw_scan_while_busy(tmp_path: Path) -> None:
    """Проверяет, что быстрый дубль raw-кода не попадает в очередь."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    runner = ManualTaskRunner()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=runner,
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )
    controller.open_box()
    runner.run_next()
    controller.set_codes_per_item(1)

    controller.on_code_scanned("CODE1")
    controller.on_code_scanned("CODE1")

    assert "Дубль" in controller.state.error_message
    runner.run_next()

    assert verifier.calls == []
    assert controller.state.pending_count == 0
    assert len(runner.tasks) == 1


def test_auto_packing_skips_visible_code_already_in_current_box(tmp_path: Path) -> None:
    """Проверяет идемпотентный пропуск кода, уже видимого в коробке."""

    service = FakePackingService()
    service.current_box_result = _detail_box(items_count=1)
    verifier = FakeVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )
    controller.refresh_current_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned("CODE1")

    assert controller.state.pending_count == 0
    assert service.batch_calls == []
    assert verifier.calls == []
    assert "текущей коробке" in controller.state.status_message
    assert controller.state.error_message == ""


def test_auto_packing_removes_only_rejected_item_after_batch_error(tmp_path: Path) -> None:
    """Проверяет, что ошибка пачки удаляет только проблемный код из ВБ."""

    service = FakePackingService()
    service.current_box_result = _detail_box(items_count=1)
    verifier = FakeVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )

    def reject_batch(
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Возвращает отказ backend по одному коду пачки."""

        service.batch_calls.append((box_id, codes, scanner_id))
        return ScanBatchToBoxResultDto(
            ok=False,
            reason_code="code_in_other_box",
            error="Код уже лежит в коробке SSCC-1",
            box=_box(filled=1),
            rejected_code_id=2,
            rejected_raw_code="CODE2",
        )

    service.scan_batch_to_box = reject_batch  # type: ignore[method-assign]
    controller.refresh_current_box()
    controller.set_codes_per_item(2)

    controller.on_code_scanned("CODE2")
    controller.on_code_scanned("CODE3")

    assert service.batch_calls == [(1, ["CODE2", "CODE3"], "desktop-com")]
    assert [item.raw_code for item in controller.state.pending_items] == ["CODE3"]
    assert controller.state.current_box is not None
    assert len(controller.state.current_box.items) == 1
    assert "CODE2" in controller.state.error_message
    assert "SSCC-1" in controller.state.error_message


def test_auto_packing_removes_multiple_rejected_items_after_batch_error(tmp_path: Path) -> None:
    """Проверяет удаление всех rejected-кодов из ВБ одним ответом backend."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )

    def reject_batch(
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Возвращает отказ backend по нескольким кодам пачки."""

        service.batch_calls.append((box_id, codes, scanner_id))
        return ScanBatchToBoxResultDto(
            ok=False,
            reason_code="duplicate_in_box",
            error="Часть кодов уже лежит в этой коробке",
            box=_box(filled=12),
            rejected_raw_codes=[f"CODE{index}" for index in range(1, 7)],
        )

    service.scan_batch_to_box = reject_batch  # type: ignore[method-assign]
    controller.open_box()
    controller.set_codes_per_item(12)

    for index in range(1, 13):
        controller.on_code_scanned(f"CODE{index}")

    assert service.batch_calls == [
        (
            1,
            [
                "CODE1",
                "CODE2",
                "CODE3",
                "CODE4",
                "CODE5",
                "CODE6",
                "CODE7",
                "CODE8",
                "CODE9",
                "CODE10",
                "CODE11",
                "CODE12",
            ],
            "desktop-com",
        )
    ]
    assert [item.raw_code for item in controller.state.pending_items] == [
        "CODE7",
        "CODE8",
        "CODE9",
        "CODE10",
        "CODE11",
        "CODE12",
    ]
    assert "Удалено" in controller.state.error_message


def test_auto_packing_filters_accepted_batch_codes_while_refreshing(tmp_path: Path) -> None:
    """Проверяет, что повторы принятой пачки не добивают следующий ВБ."""

    service = FakePackingService()
    verifier = FakeVerifyService()
    runner = ManualTaskRunner()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=runner,
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )
    controller.open_box()
    runner.run_next()
    controller.set_codes_per_item(12)

    for index in range(1, 13):
        controller.on_code_scanned(f"CODE{index}")

    assert len(runner.tasks) == 1
    runner.run_next()
    assert controller.state.pending_count == 0
    assert controller.state.is_busy is False

    for index in range(1, 19):
        controller.on_code_scanned(f"CODE{index}")

    assert len(runner.tasks) == 1
    runner.run_next()

    assert [item.raw_code for item in controller.state.pending_items] == [
        "CODE13",
        "CODE14",
        "CODE15",
        "CODE16",
        "CODE17",
        "CODE18",
    ]
    assert service.batch_calls == [
        (
            1,
            [
                "CODE1",
                "CODE2",
                "CODE3",
                "CODE4",
                "CODE5",
                "CODE6",
                "CODE7",
                "CODE8",
                "CODE9",
                "CODE10",
                "CODE11",
                "CODE12",
            ],
            "desktop-com",
        )
    ]


def test_auto_packing_can_remove_item_from_open_box(tmp_path: Path) -> None:
    """Проверяет удаление кода из открытой коробки на экране автоскана."""

    service = FakePackingService()
    service.current_box_result = _detail_box(items_count=2)
    editor = FakeBoxEditService(service)
    verifier = FakeVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=editor,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )
    controller.refresh_current_box()

    controller.remove_box_item_at(0)

    assert editor.remove_calls == [(1, 1)]
    assert controller.state.current_box is not None
    assert len(controller.state.current_box.items) == 1


def test_auto_packing_can_clear_and_delete_open_box(tmp_path: Path) -> None:
    """Проверяет очистку и удаление открытой коробки из автоупаковки."""

    service = FakePackingService()
    service.current_box_result = _detail_box(items_count=2)
    editor = FakeBoxEditService(service)
    verifier = FakeVerifyService()
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=editor,
        task_runner=ImmediateTaskRunner(),
        settings_store=store,
        settings_defaults=config,
        device_id="pc-1",
        scanner_id="desktop-com",
    )
    controller.refresh_current_box()

    controller.clear_current_box()

    assert editor.clear_calls == [1]
    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 0

    controller.delete_current_box()

    assert editor.delete_calls == [1]
    assert controller.state.current_box is None


def test_auto_packing_sends_mixed_order_to_backend_batch(tmp_path: Path) -> None:
    """Проверяет, что разные заказы проверяются только сервером полного ВБ."""

    controller, service, verifier, sounds = _controller_pair(tmp_path)
    controller.open_box()
    controller.set_codes_per_item(2)
    controller.on_code_scanned("CODE1")
    controller.on_code_scanned("CODE2")

    assert controller.state.pending_count == 0
    assert verifier.calls == []
    assert service.batch_calls == [(1, ["CODE1", "CODE2"], "desktop-com")]
    assert sounds.events == [SoundEvent.OK]
