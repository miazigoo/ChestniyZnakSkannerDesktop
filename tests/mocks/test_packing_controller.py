"""Mock-тесты контроллера упаковки."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.orders import (
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
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.api.models.printers import ClientPrinterDto, PackageLabelPrintResultDto
from chestniy_znak_desktop.controllers.packing_controller import CloseBoxUiEvent, PackingController
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


class FakeSoundService:
    """Fake sound service для проверки выбранных звуков."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


class FakePackingService:
    """Fake backend упаковки для проверки PackingController."""

    def __init__(self) -> None:
        """Создает fake-сервис с типовыми ответами."""

        self.current_box_result: BoxDetailDto | None = None
        self.last_scan: tuple[int, str, str] | None = None
        self.close_result: CloseBoxResultDto | None = None
        self.count_calls: list[tuple[int, bool]] = []
        self.open_calls: list[tuple[str, bool, str | None, str | None]] = []

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает fake текущую коробку."""

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
        """Возвращает fake результат открытия коробки."""

        self.open_calls.append((device_id, count_in_packing, order_id, order_line_id))
        return OpenBoxResultDto(
            ok=True,
            created=True,
            has_active_boxes=False,
            box=_box(count_in_packing=count_in_packing),
        )

    def scan_to_box(self, box_id: int, code: str, scanner_id: str) -> ScanToBoxResultDto:
        """Возвращает fake результат скана в коробку."""

        self.last_scan = (box_id, code, scanner_id)
        return ScanToBoxResultDto(
            ok=True,
            reason_code="code_added",
            box=_box(filled=1),
        )

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Возвращает fake результат закрытия коробки."""

        if self.close_result is not None:
            return self.close_result
        return CloseBoxResultDto(
            ok=True,
            reason_code="box_closed",
            box=_box(filled=20, is_closed=True),
        )

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Возвращает fake результат переключения учета коробки."""

        self.count_calls.append((box_id, count_in_packing))
        return BoxActionResultDto(
            ok=True,
            reason_code="count_in_packing_updated",
            box=_box(count_in_packing=count_in_packing),
        )


class FakeOrderService:
    """Fake сервис рабочих заказов для проверки выбора номенклатуры."""

    def __init__(self, page: WorkOrderPageDto) -> None:
        """Создает сервис с фиксированной страницей заказов."""

        self.page = page

    def list_orders(
        self,
        status: str | None = None,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> WorkOrderPageDto:
        """Возвращает заданную страницу заказов."""

        return self.page


class FakeLabelPrinter:
    """Fake сервис печати SSCC для проверки закрытия коробки."""

    def __init__(self, print_ok: bool = True) -> None:
        """Создает fake с заданным результатом печати."""

        self.print_ok = print_ok
        self.calls: list[tuple[int, str]] = []

    def print_box_label(self, box_id: int, device_id: str) -> PackageLabelPrintResultDto:
        """Возвращает fake результат печати."""

        self.calls.append((box_id, device_id))
        return PackageLabelPrintResultDto(
            ok=self.print_ok,
            reason_code="label_printed" if self.print_ok else "label_print_failed",
            print_status="",
            print_ok=self.print_ok,
            print_error="" if self.print_ok else "Нет связи с принтером",
            printer=ClientPrinterDto(
                id=1,
                name="Zebra",
                ip_address="192.168.1.10",
            ),
        )


def _box(
    *,
    filled: int = 0,
    capacity: int = 20,
    count_in_packing: bool = True,
    is_closed: bool = False,
) -> BoxDto:
    """Создает DTO коробки для тестов."""

    return BoxDto(
        box_id=1,
        order_name="26-0001",
        sscc="",
        capacity=capacity,
        filled=filled,
        count_in_packing=count_in_packing,
        allow_duplicate_scans=False,
        is_closed=is_closed,
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


def _controller_pair(
    order_service: FakeOrderService | None = None,
    label_printer: FakeLabelPrinter | None = None,
) -> tuple[PackingController, FakePackingService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakePackingService()
    sounds = FakeSoundService()
    controller = PackingController(
        packing_service=service,
        task_runner=ImmediateTaskRunner(),
        device_id="pc-1",
        order_service=order_service,
        scanner_id="desktop-com",
        sound_service=sounds,
        label_printer=label_printer,
    )
    return controller, service, sounds


def test_packing_controller_open_box_updates_state() -> None:
    """Проверяет открытие коробки и обновление state."""

    controller, _service, sounds = _controller_pair()
    controller.open_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.box_id == 1
    assert controller.state.status_message == "Коробка открыта"
    assert sounds.events == [SoundEvent.OK]


def test_packing_controller_uses_count_flag_when_opening_box() -> None:
    """Проверяет, что чекбокс учета влияет на открытие коробки."""

    controller, _service, _sounds = _controller_pair()
    controller.set_count_in_packing(False)

    controller.open_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.count_in_packing is False
    assert controller.state.count_in_packing is False


def test_packing_controller_updates_count_flag_for_open_box() -> None:
    """Проверяет, что чекбокс учета меняет уже открытую коробку через backend."""

    controller, service, _sounds = _controller_pair()
    controller.open_box()

    controller.set_count_in_packing(False)

    assert service.count_calls == [(1, False)]
    assert controller.state.current_box is not None
    assert controller.state.current_box.count_in_packing is False
    assert controller.state.count_in_packing is False
    assert controller.state.status_message == "Учет коробки обновлен"
    assert controller.state.result_message == "Без учета упаковки"


def test_packing_controller_blocks_box_for_no_scan_order() -> None:
    """Проверяет, что заказ без сканирования не открывает упаковочную коробку."""

    order_service = FakeOrderService(_work_order(scan_required=False))
    controller, service, sounds = _controller_pair(order_service)

    controller.refresh_orders()
    controller.open_box()

    assert controller.state.selected_order_scan_required is False
    assert service.open_calls == []
    assert controller.state.status_message == "Сканирование по заказу отключено"
    assert "web-кабинете поставщика" in controller.state.result_message
    assert sounds.events == [SoundEvent.WARNING]


def test_packing_controller_warns_when_scan_without_box() -> None:
    """Проверяет скан без открытой коробки."""

    controller, _service, sounds = _controller_pair()
    controller.on_code_scanned("CODE")

    assert controller.state.error_message == "Открытая коробка не найдена"
    assert sounds.events == [SoundEvent.WARNING]


def test_packing_controller_scan_to_box_updates_state() -> None:
    """Проверяет успешное добавление кода в коробку."""

    controller, service, sounds = _controller_pair()
    controller.open_box()
    controller.on_code_scanned("CODE")

    assert service.last_scan == (1, "CODE", "desktop-com")
    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 1
    assert controller.state.status_message == "Код добавлен"
    assert sounds.events[-1] == SoundEvent.OK


def test_packing_controller_close_box_clears_current_box() -> None:
    """Проверяет закрытие коробки."""

    controller, _service, sounds = _controller_pair()
    events: list[CloseBoxUiEvent] = []
    controller.close_completed.connect(events.append)
    controller.open_box()
    controller.close_current_box()

    assert controller.state.current_box is None
    assert controller.state.status_message == "Коробка закрыта"
    assert sounds.events[-1] == SoundEvent.VICTORY
    assert events[-1].ok is True
    assert events[-1].is_full is True


def test_packing_controller_prints_label_after_successful_close() -> None:
    """Проверяет печать SSCC после успешного закрытия коробки."""

    label_printer = FakeLabelPrinter(print_ok=True)
    controller, _service, sounds = _controller_pair(label_printer=label_printer)
    events: list[CloseBoxUiEvent] = []
    controller.close_completed.connect(events.append)

    controller.open_box()
    controller.close_current_box()

    assert label_printer.calls == [(1, "pc-1")]
    assert events[-1].print_ok is True
    assert events[-1].print_printer_name == "Zebra"
    assert sounds.events[-1] == SoundEvent.VICTORY


def test_packing_controller_warns_when_label_print_failed_after_close() -> None:
    """Проверяет явный статус, если коробка закрылась, но SSCC не напечатался."""

    label_printer = FakeLabelPrinter(print_ok=False)
    controller, _service, sounds = _controller_pair(label_printer=label_printer)
    events: list[CloseBoxUiEvent] = []
    controller.close_completed.connect(events.append)

    controller.open_box()
    controller.close_current_box()

    assert controller.state.current_box is None
    assert events[-1].ok is True
    assert events[-1].print_ok is False
    assert events[-1].print_error == "Нет связи с принтером"
    assert sounds.events[-1] == SoundEvent.WARNING


def test_packing_controller_close_failed_keeps_current_box() -> None:
    """Проверяет, что ошибка закрытия оставляет коробку активной."""

    controller, service, sounds = _controller_pair()
    events: list[CloseBoxUiEvent] = []
    service.close_result = CloseBoxResultDto(
        ok=False,
        reason_code="close_failed",
        error="Не удалось закрыть коробку",
        box=_box(filled=5, capacity=20, is_closed=False),
    )
    controller.close_completed.connect(events.append)

    controller.open_box()
    controller.close_current_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 5
    assert controller.state.status_message == "Коробка не закрыта"
    assert sounds.events[-1] == SoundEvent.ERROR
    assert events[-1].ok is False
    assert events[-1].error_message == "Не удалось закрыть коробку"


def test_packing_controller_refresh_current_box_with_items() -> None:
    """Проверяет загрузку текущей коробки со списком кодов."""

    controller, service, _sounds = _controller_pair()
    service.current_box_result = BoxDetailDto(
        **_box(filled=1).model_dump(),
        items=[
            BoxItemDto(
                id=10,
                code_id=100,
                gtin="04601234567890",
                serial="SERIAL",
                visible_code="010460123456789021SERIAL",
            )
        ],
    )
    controller.refresh_current_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.items[0].serial == "SERIAL"
