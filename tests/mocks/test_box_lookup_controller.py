"""Mock-тесты контроллера поиска коробки."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.packing import BoxDto, BoxListDto
from chestniy_znak_desktop.controllers.box_lookup_controller import BoxLookupController
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
        """Создает fake-сервис поиска."""

        self.calls: list[str] = []
        self.error: Exception | None = None
        self.box = BoxDto(
            box_id=42,
            order_name="26-0001",
            sscc="123456789012345678",
            capacity=20,
            filled=7,
            allow_duplicate_scans=False,
            is_closed=False,
            is_edit_mode=False,
        )

    def list_boxes(
        self,
        status: str = "all",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> BoxListDto:
        """Возвращает страницу коробок для поиска."""

        self.calls.append(query)
        if self.error is not None:
            raise self.error
        if query in {str(self.box.box_id), self.box.sscc}:
            return BoxListDto(items=[self.box], total=1, limit=limit, offset=offset)
        return BoxListDto(items=[], total=0, limit=limit, offset=offset)


class FakeSoundService:
    """Fake sound service для проверки звуков."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


def _controller_pair() -> tuple[BoxLookupController, FakeBoxesService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakeBoxesService()
    sounds = FakeSoundService()
    controller = BoxLookupController(
        boxes_service=service,
        task_runner=ImmediateTaskRunner(),
        sound_service=sounds,
    )
    return controller, service, sounds


def test_box_lookup_controller_finds_box_by_sscc() -> None:
    """Проверяет поиск коробки по SSCC из GS1-скана."""

    controller, service, sounds = _controller_pair()
    found: list[int] = []
    controller.box_found.connect(found.append)

    controller.on_code_scanned("(00)123456789012345678")

    assert service.calls == ["00123456789012345678", "123456789012345678"]
    assert controller.state.found_box_id == 42
    assert controller.state.error_message == ""
    assert found == [42]
    assert sounds.events == [SoundEvent.OK]


def test_box_lookup_controller_reports_not_found() -> None:
    """Проверяет состояние, когда коробка не найдена."""

    controller, _service, sounds = _controller_pair()

    controller.on_code_scanned("000")

    assert controller.state.error_message == "Коробка не найдена"
    assert controller.state.found_box_id is None
    assert sounds.events == [SoundEvent.ERROR]


def test_box_lookup_controller_reports_backend_error() -> None:
    """Проверяет ошибку backend-сценария поиска."""

    controller, service, sounds = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.on_code_scanned("42")

    assert controller.state.status_message == "Ошибка поиска коробки"
    assert controller.state.error_message == "Backend недоступен"
    assert sounds.events == [SoundEvent.ERROR]
