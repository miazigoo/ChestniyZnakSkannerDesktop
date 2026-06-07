"""Нагрузочные тесты рабочих сценариев Desktop-упаковки."""

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
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.api.models.verify import VerifyExistsResponseDto
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.app.settings_store import SettingsStore
from chestniy_znak_desktop.controllers.auto_packing_controller import AutoPackingController
from chestniy_znak_desktop.controllers.packing_controller import PackingController


class ManualTaskRunner:
    """TaskRunner, имитирующий задержку backend до явного drain."""

    def __init__(self) -> None:
        """Создает пустую очередь фоновых задач."""

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
        """Ставит задачу в очередь."""

        self.tasks.append((task, on_success, on_error))

    def run_next(self) -> None:
        """Выполняет следующую задачу."""

        task, on_success, on_error = self.tasks.pop(0)
        try:
            result = task()
        except Exception as exc:
            on_error(exc)
            return
        on_success(result)

    def drain(self, *, limit: int = 100_000) -> None:
        """Выполняет очередь до пустого состояния с защитой от бесконечного цикла."""

        runs = 0
        while self.tasks:
            runs += 1
            if runs > limit:
                raise AssertionError("ManualTaskRunner drain limit exceeded")
            self.run_next()


class LoadPackingService:
    """Fake backend обычной упаковки с накоплением коробок по 100 кодов."""

    def __init__(self, *, capacity: int) -> None:
        """Создает fake-сервис с заданной вместимостью коробки."""

        self.capacity = capacity
        self.current_box_id = 0
        self.items: list[str] = []
        self.closed_boxes: list[list[str]] = []

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую открытую коробку."""

        if self.current_box_id == 0:
            return None
        return self._detail_box()

    def open_box(
        self,
        device_id: str,
        count_in_packing: bool = True,
        order_id: str | None = None,
        order_line_id: str | None = None,
        code_value: str | None = None,
        sscc: str | None = None,
    ) -> OpenBoxResultDto:
        """Открывает новую fake-коробку."""

        self.current_box_id += 1
        self.items = []
        return OpenBoxResultDto(
            ok=True,
            created=True,
            has_active_boxes=False,
            box=self._box(),
        )

    def scan_to_box(self, box_id: int, code: str, scanner_id: str) -> ScanToBoxResultDto:
        """Добавляет код в fake-коробку."""

        if box_id != self.current_box_id:
            return ScanToBoxResultDto(
                ok=False,
                reason_code="package_is_not_open",
                error="Wrong box",
                box=self._box(),
            )
        if len(self.items) >= self.capacity:
            return ScanToBoxResultDto(
                ok=False,
                reason_code="box_capacity_reached",
                box=self._box(),
            )
        self.items.append(code)
        return ScanToBoxResultDto(
            ok=True,
            reason_code="code_added",
            box=self._box(),
            box_full_signal=len(self.items) >= self.capacity,
        )

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает текущую fake-коробку."""

        self.closed_boxes.append(list(self.items))
        result = CloseBoxResultDto(
            ok=True,
            reason_code="box_closed",
            box=self._box(is_closed=True),
        )
        self.items = []
        return result

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Возвращает успешный результат смены режима учета."""

        return BoxActionResultDto(ok=True, reason_code="updated", box=self._detail_box())

    def _box(self, *, is_closed: bool = False) -> BoxDto:
        """Создает summary текущей fake-коробки."""

        return BoxDto(
            box_id=self.current_box_id,
            order_name="LOAD-ORDER",
            sscc=f"SSCC-{self.current_box_id:04d}",
            capacity=self.capacity,
            filled=len(self.items),
            count_in_packing=True,
            allow_duplicate_scans=False,
            is_closed=is_closed,
            is_edit_mode=False,
        )

    def _detail_box(self) -> BoxDetailDto:
        """Создает detail текущей fake-коробки."""

        return BoxDetailDto(
            **self._box().model_dump(),
            items=[
                BoxItemDto(
                    id=index,
                    code_id=index,
                    scan_id=index,
                    gtin="04601234567890",
                    serial=f"SERIAL{index:06d}",
                    visible_code=code,
                )
                for index, code in enumerate(self.items, start=1)
            ],
        )


class LoadAutoPackingService:
    """Fake backend автоупаковки с накоплением большого потока кодов."""

    def __init__(self, *, capacity: int) -> None:
        """Создает fake-сервис."""

        self.capacity = capacity
        self.box_id = 1
        self.items: list[str] = []
        self.batch_calls = 0

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает детальную открытую коробку."""

        return BoxDetailDto(
            **self._box().model_dump(),
            items=[
                BoxItemDto(
                    id=index,
                    code_id=index,
                    scan_id=index,
                    gtin="04601234567890",
                    serial=f"SERIAL{index:06d}",
                    visible_code=code,
                )
                for index, code in enumerate(self.items, start=1)
            ],
        )

    def open_box(
        self,
        device_id: str,
        count_in_packing: bool = True,
        order_id: str | None = None,
        order_line_id: str | None = None,
        code_value: str | None = None,
        sscc: str | None = None,
    ) -> OpenBoxResultDto:
        """Открывает fake-коробку."""

        self.items = []
        return OpenBoxResultDto(ok=True, created=True, box=self._box())

    def scan_batch_to_box(
        self,
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Добавляет пачку в fake-коробку."""

        self.batch_calls += 1
        if len(self.items) + len(codes) > self.capacity:
            return ScanBatchToBoxResultDto(
                ok=False,
                reason_code="box_capacity_reached",
                box=self._box(),
            )
        self.items.extend(codes)
        return ScanBatchToBoxResultDto(
            ok=True,
            reason_code="batch_added",
            added=len(codes),
            box=self._box(),
            box_full_signal=len(self.items) >= self.capacity,
        )

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает fake-коробку."""

        return CloseBoxResultDto(ok=True, reason_code="box_closed", box=self._box(is_closed=True))

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Возвращает успешный результат смены режима учета."""

        return BoxActionResultDto(ok=True, reason_code="updated", box=self.current_box())

    def _box(self, *, is_closed: bool = False) -> BoxDto:
        """Создает summary fake-коробки."""

        return BoxDto(
            box_id=self.box_id,
            order_name="AUTO-LOAD-ORDER",
            sscc="SSCC-AUTO-0001",
            capacity=self.capacity,
            filled=len(self.items),
            count_in_packing=True,
            allow_duplicate_scans=False,
            is_closed=is_closed,
            is_edit_mode=False,
        )


class LoadAutoVerifier:
    """Verifier не должен вызываться при локальном пуле."""

    def __init__(self) -> None:
        """Создает счетчик вызовов."""

        self.calls = 0

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        save_scan: bool = True,
    ) -> VerifyExistsResponseDto:
        """Фиксирует ошибочный вызов fallback-проверки."""

        self.calls += 1
        raise AssertionError("HTTP verify must not be used with downloaded local pool")


class LoadOrderService:
    """Fake order backend с постраничным локальным пулом."""

    def __init__(self, *, codes: list[str]) -> None:
        """Создает сервис с заданным пулом кодов."""

        self.codes = codes
        self.pool_calls: list[tuple[str, int, int]] = []
        self.page = WorkOrderPageDto(
            data=[
                WorkOrderDto(
                    id="order-auto-load",
                    plant_id="plant-1",
                    supplier_id="supplier-1",
                    order_number="AUTO-LOAD-ORDER",
                    status="issued_to_supplier",
                    scan_required=True,
                    lines=[
                        OrderLineDto(
                            id="line-auto-load",
                            order_id="order-auto-load",
                            product_id="product-1",
                            quantity=len(codes),
                            required_code_quantity=len(codes),
                            package_capacity=len(codes),
                            status="active",
                            product=OrderProductDto(
                                id="product-1",
                                sku="LOAD-SKU",
                                name="Нагрузочный товар",
                            ),
                        )
                    ],
                )
            ]
        )

    def list_orders(
        self,
        status: str | None = None,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> WorkOrderPageDto:
        """Возвращает один заказ."""

        return self.page

    def download_local_pool(
        self,
        order_id: str,
        limit: int = 5000,
        offset: int = 0,
    ) -> LocalCodePoolPageDto:
        """Возвращает страницу локального пула."""

        self.pool_calls.append((order_id, limit, offset))
        page_codes = self.codes[offset : offset + limit]
        next_offset = offset + limit if offset + limit < len(self.codes) else None
        return LocalCodePoolPageDto(
            data=LocalCodePoolDto(
                order=self.page.data[0],
                codes=[
                    LocalPoolCodeDto(id=f"code-{index}", code=code, status="issued")
                    for index, code in enumerate(page_codes, start=offset + 1)
                ],
                total=len(self.codes),
                count=len(page_codes),
                limit=limit,
                offset=offset,
                next_offset=next_offset,
                has_more=next_offset is not None,
            )
        )


def _load_code(index: int) -> str:
    """Создает стабильный тестовый код DataMatrix-подобного вида."""

    return f"010460123456789021LOAD{index:012d}"


def test_manual_packing_packs_1000_fast_scans_into_10_boxes() -> None:
    """Проверяет поток 1000 быстрых сканов в коробки по 100 шт."""

    runner = ManualTaskRunner()
    service = LoadPackingService(capacity=100)
    controller = PackingController(
        packing_service=service,
        task_runner=runner,
        device_id="pc-load",
        scanner_id="desktop-com",
    )

    code_index = 1
    for _box_number in range(10):
        controller.open_box()
        runner.drain()
        for _ in range(100):
            controller.on_code_scanned(_load_code(code_index))
            code_index += 1
        runner.drain()
        assert controller.state.current_box is not None
        assert controller.state.current_box.filled == 100
        assert controller.state.error_message == ""
        controller.close_current_box()
        runner.drain()

    assert len(service.closed_boxes) == 10
    assert sum(len(box) for box in service.closed_boxes) == 1000
    assert all(len(box) == 100 for box in service.closed_boxes)
    assert service.closed_boxes[0][0] == _load_code(1)
    assert service.closed_boxes[-1][-1] == _load_code(1000)
    assert controller.state.current_box is None
    assert controller.state.error_message == ""


def test_auto_packing_processes_2000_fast_scans_from_local_pool(tmp_path: Path) -> None:
    """Проверяет автосканерный поток 2000 кодов без потери очереди и fallback HTTP."""

    codes = [_load_code(index) for index in range(1, 2001)]
    runner = ManualTaskRunner()
    service = LoadAutoPackingService(capacity=2000)
    verifier = LoadAutoVerifier()
    order_service = LoadOrderService(codes=codes)
    config = AppConfig(data_dir=tmp_path)
    store = SettingsStore.from_file(str(tmp_path / "settings.ini"))
    controller = AutoPackingController(
        packing_service=service,
        verify_service=verifier,
        box_edit_service=None,
        task_runner=runner,
        settings_store=store,
        settings_defaults=config,
        device_id="pc-load",
        order_service=order_service,
        scanner_id="desktop-com",
    )

    controller.refresh_orders()
    runner.drain()
    controller.open_box()
    runner.drain()
    controller.set_codes_per_item(1)

    for code in codes:
        controller.on_code_scanned(code)

    runner.drain()

    assert order_service.pool_calls == [("order-auto-load", 5000, 0)]
    assert verifier.calls == 0
    assert service.batch_calls == 2000
    assert service.items == codes
    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 2000
    assert len(controller.state.current_box.items) == 2000
    assert controller.state.pending_count == 0
    assert controller.state.is_busy is False
    assert controller.state.error_message == ""
