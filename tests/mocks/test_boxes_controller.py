"""Mock-тесты контроллера списка коробок."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.packing import BoxDto, BoxListDto
from chestniy_znak_desktop.controllers.boxes_controller import BoxesController


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
            items=[_box()],
            total=2,
            limit=limit,
            offset=offset,
            has_more=offset == 0,
        )


def _box() -> BoxDto:
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
        print_ok=True,
    )


def _controller_pair() -> tuple[BoxesController, FakeBoxesService]:
    """Создает контроллер списка коробок с fake-сервисом."""

    service = FakeBoxesService()
    controller = BoxesController(
        boxes_service=service,
        task_runner=ImmediateTaskRunner(),
        page_limit=1,
    )
    return controller, service


def test_boxes_controller_refresh_loads_rows() -> None:
    """Проверяет загрузку строк таблицы коробок."""

    controller, service = _controller_pair()

    controller.refresh()

    assert service.last_call == ("all", "", 1, 0)
    assert controller.state.rows[0].box_id == 10
    assert controller.state.rows[0].status == "Открыта"
    assert controller.state.rows[0].print_status == "Напечатано"
    assert controller.state.page_title == "1-1 / 2"


def test_boxes_controller_filter_resets_page() -> None:
    """Проверяет смену фильтра с загрузкой первой страницы."""

    controller, service = _controller_pair()

    controller.set_status_filter("closed")

    assert service.last_call == ("closed", "", 1, 0)
    assert controller.state.status_filter == "closed"


def test_boxes_controller_search_resets_page() -> None:
    """Проверяет поиск с загрузкой первой страницы."""

    controller, service = _controller_pair()

    controller.set_query(" 000123 ")

    assert service.last_call == ("all", "000123", 1, 0)
    assert controller.state.query == "000123"


def test_boxes_controller_loads_next_page() -> None:
    """Проверяет переход на следующую страницу."""

    controller, service = _controller_pair()
    controller.refresh()

    controller.next_page()

    assert service.last_call == ("all", "", 1, 1)
    assert controller.state.offset == 1


def test_boxes_controller_reports_error() -> None:
    """Проверяет отображение ошибки загрузки."""

    controller, service = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.refresh()

    assert controller.state.status_message == "Ошибка загрузки коробок"
    assert controller.state.error_message == "Backend недоступен"
