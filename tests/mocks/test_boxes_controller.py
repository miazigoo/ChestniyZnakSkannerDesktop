"""Mock-тесты контроллера списка коробок."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.packing import (
    BoxDetailDto,
    BoxDto,
    BoxListDto,
    CloseBoxResultDto,
)
from chestniy_znak_desktop.controllers.boxes_controller import BoxesController
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


class FakeBoxesService:
    """Fake backend списка коробок."""

    def __init__(self) -> None:
        """Создает fake-сервис со счетчиком последнего вызова."""

        self.last_call: tuple[str, str, int, int] | None = None
        self.error: Exception | None = None
        self.items = [_box()]

    def list_boxes(
        self,
        status: str = "all",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> BoxListDto:
        """Возвращает страницу коробок или выбрасывает ошибку."""

        self.last_call = (status, query, limit, offset)
        if self.error is not None:
            raise self.error
        return BoxListDto(
            items=self.items,
            total=2,
            limit=limit,
            offset=offset,
            has_more=offset == 0,
        )

    def get_box(self, box_id: int) -> BoxDetailDto:
        """Возвращает детальную fake-коробку."""

        if self.error is not None:
            raise self.error
        return BoxDetailDto(
            **_box().model_dump(),
            items=[
                {
                    "id": box_id,
                    "code_id": 100,
                    "gtin": "04601234567890",
                    "serial": "SERIAL",
                    "visible_code": "010460123456789021SERIAL",
                }
            ],
        )


class FakePrinterService:
    """Fake backend повторной печати этикеток."""

    def __init__(self) -> None:
        """Создает fake-сервис со счетчиком вызова."""

        self.last_call: tuple[int, str] | None = None
        self.error: Exception | None = None
        self.result_ok = True
        self.print_ok = True

    def print_box_label(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Возвращает fake результат печати."""

        self.last_call = (box_id, device_id)
        if self.error is not None:
            raise self.error
        return CloseBoxResultDto(
            ok=self.result_ok,
            reason_code="printed",
            box=_box(print_ok=self.print_ok),
            print_ok=self.print_ok,
            print_error="" if self.print_ok else "Принтер недоступен",
        )


class FakeSoundService:
    """Fake sound service для проверки звуков действий."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


def _box(print_ok: bool = True) -> BoxDto:
    """Создает DTO коробки для тестов."""

    return BoxDto(
        box_id=10,
        order_name="26-0001",
        sscc="000123",
        capacity=20,
        filled=5,
        count_in_packing=True,
        allow_duplicate_scans=False,
        is_closed=False,
        is_edit_mode=False,
        active_user_name="Operator",
        print_ok=print_ok,
    )


def _controller_pair() -> tuple[
    BoxesController,
    FakeBoxesService,
    FakePrinterService,
    FakeSoundService,
]:
    """Создает контроллер списка коробок с fake-сервисом."""

    service = FakeBoxesService()
    printer = FakePrinterService()
    sounds = FakeSoundService()
    controller = BoxesController(
        boxes_service=service,
        printer_service=printer,
        task_runner=ImmediateTaskRunner(),
        device_id="pc-1",
        page_limit=1,
        sound_service=sounds,
    )
    return controller, service, printer, sounds


def test_boxes_controller_refresh_loads_rows() -> None:
    """Проверяет загрузку строк таблицы коробок."""

    controller, service, _printer, _sounds = _controller_pair()

    controller.refresh()

    assert service.last_call == ("all", "", 1, 0)
    assert controller.state.rows[0].box_id == 10
    assert controller.state.rows[0].status == "Открыта"
    assert controller.state.rows[0].print_status == "Напечатано"
    assert controller.state.page_title == "1-1 / 2"


def test_boxes_controller_filter_resets_page() -> None:
    """Проверяет смену фильтра с загрузкой первой страницы."""

    controller, service, _printer, _sounds = _controller_pair()

    controller.set_status_filter("closed")

    assert service.last_call == ("closed", "", 1, 0)
    assert controller.state.status_filter == "closed"


def test_boxes_controller_search_resets_page() -> None:
    """Проверяет поиск с загрузкой первой страницы."""

    controller, service, _printer, _sounds = _controller_pair()

    controller.set_query(" 000123 ")

    assert service.last_call == ("all", "000123", 1, 0)
    assert controller.state.query == "000123"


def test_boxes_controller_loads_next_page() -> None:
    """Проверяет переход на следующую страницу."""

    controller, service, _printer, _sounds = _controller_pair()
    controller.refresh()

    controller.next_page()

    assert service.last_call == ("all", "", 1, 1)
    assert controller.state.offset == 1


def test_boxes_controller_reports_error() -> None:
    """Проверяет отображение ошибки загрузки."""

    controller, service, _printer, _sounds = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.refresh()

    assert controller.state.status_message == "Ошибка загрузки коробок"
    assert controller.state.error_message == "Backend недоступен"


def test_boxes_controller_loads_box_detail() -> None:
    """Проверяет загрузку детальной карточки выбранной коробки."""

    controller, _service, _printer, _sounds = _controller_pair()

    controller.load_detail(10)

    assert controller.state.detail is not None
    assert controller.state.detail.box_id == 10
    assert controller.state.detail.items[0].serial == "SERIAL"
    assert controller.state.detail_status_message == "Коробка #10 загружена"


def test_boxes_controller_reports_detail_error() -> None:
    """Проверяет ошибку загрузки детальной карточки."""

    controller, service, _printer, _sounds = _controller_pair()
    controller.load_detail(10)
    service.error = RuntimeError("Коробка не найдена")

    controller.load_detail(10)

    assert controller.state.detail is None
    assert controller.state.detail_status_message == "Ошибка загрузки коробки"
    assert controller.state.detail_error_message == "Коробка не найдена"


def test_boxes_controller_clear_detail_resets_selected_box() -> None:
    """Проверяет явный сброс выбранной коробки."""

    controller, _service, _printer, _sounds = _controller_pair()
    controller.load_detail(10)

    controller.clear_detail("Коробка удалена")

    assert controller.state.selected_box_id is None
    assert controller.state.detail is None
    assert controller.state.detail_status_message == "Коробка удалена"


def test_boxes_controller_clear_loaded_data_keeps_filters() -> None:
    """Проверяет очистку загруженных данных без сброса фильтров."""

    controller, service, _printer, _sounds = _controller_pair()
    controller.set_query("000123")
    controller.load_detail(10)

    controller.clear_loaded_data()

    assert service.last_call == ("all", "000123", 1, 0)
    assert controller.state.query == "000123"
    assert controller.state.rows == []
    assert controller.state.detail is None
    assert controller.state.status_message == "Список будет загружен при входе в экран"


def test_boxes_controller_refresh_clears_missing_selected_box() -> None:
    """Проверяет сброс карточки, если выбранной коробки нет в списке."""

    controller, service, _printer, _sounds = _controller_pair()
    controller.load_detail(10)
    service.items = []

    controller.refresh()

    assert controller.state.selected_box_id is None
    assert controller.state.detail is None
    assert controller.state.detail_status_message == "Выберите коробку для просмотра состава"


def test_boxes_controller_prints_selected_label() -> None:
    """Проверяет повторную печать этикетки выбранной коробки."""

    controller, _service, printer, sounds = _controller_pair()
    controller.load_detail(10)

    controller.print_selected_label(10)

    assert printer.last_call == (10, "pc-1")
    assert controller.state.detail_status_message == "Этикетка отправлена на печать"
    assert controller.state.detail is not None
    assert controller.state.detail.print_status == "Напечатано"
    assert sounds.events[-1] == SoundEvent.OK


def test_boxes_controller_reports_print_error() -> None:
    """Проверяет ошибку повторной печати этикетки."""

    controller, _service, printer, sounds = _controller_pair()
    printer.error = RuntimeError("Принтер недоступен")

    controller.print_selected_label(10)

    assert controller.state.detail_status_message == "Ошибка печати"
    assert controller.state.detail_error_message == "Принтер недоступен"
    assert sounds.events[-1] == SoundEvent.ERROR
