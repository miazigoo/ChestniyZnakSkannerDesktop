"""Mock-тесты контроллера упаковки."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.packing import (
    BoxDetailDto,
    BoxDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.controllers.packing_controller import PackingController
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

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает fake текущую коробку."""

        return self.current_box_result

    def open_box(self, device_id: str, count_in_packing: bool = True) -> OpenBoxResultDto:
        """Возвращает fake результат открытия коробки."""

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
            print_ok=True,
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


def _controller_pair() -> tuple[PackingController, FakePackingService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakePackingService()
    sounds = FakeSoundService()
    controller = PackingController(
        packing_service=service,
        task_runner=ImmediateTaskRunner(),
        device_id="pc-1",
        scanner_id="desktop-com",
        sound_service=sounds,
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
    events = []
    controller.close_completed.connect(events.append)
    controller.open_box()
    controller.close_current_box()

    assert controller.state.current_box is None
    assert controller.state.status_message == "Коробка закрыта"
    assert sounds.events[-1] == SoundEvent.VICTORY
    assert events[-1].ok is True
    assert events[-1].is_full is True


def test_packing_controller_close_failed_keeps_current_box() -> None:
    """Проверяет, что ошибка закрытия оставляет коробку активной."""

    controller, service, sounds = _controller_pair()
    events = []
    service.close_result = CloseBoxResultDto(
        ok=False,
        reason_code="printer_unavailable",
        error="Принтер недоступен",
        box=_box(filled=5, capacity=20, is_closed=False),
        print_ok=False,
        print_error="Нет связи с принтером",
    )
    controller.close_completed.connect(events.append)

    controller.open_box()
    controller.close_current_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.filled == 5
    assert controller.state.status_message == "Коробка не закрыта"
    assert sounds.events[-1] == SoundEvent.ERROR
    assert events[-1].ok is False
    assert events[-1].error_message == "Принтер недоступен"


def test_packing_controller_refresh_current_box_with_items() -> None:
    """Проверяет загрузку текущей коробки со списком кодов."""

    controller, service, _sounds = _controller_pair()
    service.current_box_result = BoxDetailDto(
        **_box(filled=1).model_dump(),
        items=[
            {
                "id": 10,
                "code_id": 100,
                "gtin": "04601234567890",
                "serial": "SERIAL",
                "visible_code": "010460123456789021SERIAL",
            }
        ],
    )
    controller.refresh_current_box()

    assert controller.state.current_box is not None
    assert controller.state.current_box.items[0].serial == "SERIAL"
