"""Mock-тесты контроллера редактирования коробки."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.packing import BoxActionResultDto, BoxDto
from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditController
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


class FakeBoxEditService:
    """Fake backend редактирования коробки."""

    def __init__(self) -> None:
        """Создает fake-сервис с последним вызовом."""

        self.last_call: tuple[str, int, int | str | None] | None = None
        self.error: Exception | None = None
        self.ok = True
        self.reason_code = "edit_opened"
        self.removed: int | None = None

    def open_edit(self, box_id: int, reason: str = "") -> BoxActionResultDto:
        """Имитирует открытие редактирования."""

        self.last_call = ("open", box_id, reason)
        return self._result()

    def close_edit(self, box_id: int) -> BoxActionResultDto:
        """Имитирует закрытие редактирования."""

        self.last_call = ("close", box_id, None)
        return self._result()

    def remove_item(self, box_id: int, item_id: int) -> BoxActionResultDto:
        """Имитирует удаление кода."""

        self.last_call = ("remove", box_id, item_id)
        return self._result()

    def clear_box(self, box_id: int) -> BoxActionResultDto:
        """Имитирует очистку коробки."""

        self.last_call = ("clear", box_id, None)
        return self._result()

    def delete_empty_box(self, box_id: int) -> BoxActionResultDto:
        """Имитирует удаление пустой коробки."""

        self.last_call = ("delete", box_id, None)
        return self._result()

    def _result(self) -> BoxActionResultDto:
        """Возвращает fake результат действия."""

        if self.error is not None:
            raise self.error
        return BoxActionResultDto(
            ok=self.ok,
            reason_code=self.reason_code,
            error="" if self.ok else "Ошибка редактирования",
            box=_box(),
            removed=self.removed,
        )


class FakeSoundService:
    """Fake sound service для проверки выбранных звуков."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


def _box() -> BoxDto:
    """Создает DTO коробки для тестов."""

    return BoxDto(
        box_id=10,
        order_name="26-0001",
        sscc="000123",
        capacity=20,
        filled=0,
        count_in_packing=True,
        allow_duplicate_scans=False,
        is_closed=False,
        is_edit_mode=True,
    )


def _controller_pair() -> tuple[BoxEditController, FakeBoxEditService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakeBoxEditService()
    sounds = FakeSoundService()
    controller = BoxEditController(
        edit_service=service,
        task_runner=ImmediateTaskRunner(),
        sound_service=sounds,
    )
    return controller, service, sounds


def test_box_edit_controller_opens_edit_and_emits_change() -> None:
    """Проверяет открытие редактирования и запрос обновления детали."""

    controller, service, sounds = _controller_pair()
    changed: list[int] = []
    controller.box_changed.connect(changed.append)

    controller.open_edit(10, reason="fix")

    assert service.last_call == ("open", 10, "fix")
    assert controller.state.status_message == "Редактирование открыто"
    assert changed == [10]
    assert sounds.events == [SoundEvent.OK]


def test_box_edit_controller_removes_item() -> None:
    """Проверяет удаление выбранного кода."""

    controller, service, _sounds = _controller_pair()
    service.reason_code = "item_removed"

    controller.remove_item(10, 55)

    assert service.last_call == ("remove", 10, 55)
    assert controller.state.status_message == "Код удален из коробки"


def test_box_edit_controller_emits_deleted_for_empty_box() -> None:
    """Проверяет событие удаления пустой коробки."""

    controller, service, _sounds = _controller_pair()
    service.reason_code = "empty_box_deleted"
    service.removed = 1
    deleted: list[int] = []
    controller.box_deleted.connect(deleted.append)

    controller.delete_empty_box(10)

    assert service.last_call == ("delete", 10, None)
    assert deleted == [10]


def test_box_edit_controller_reports_backend_error() -> None:
    """Проверяет ошибку backend-сценария редактирования."""

    controller, service, sounds = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.clear_box(10)

    assert controller.state.status_message == "Ошибка редактирования коробки"
    assert controller.state.error_message == "Backend недоступен"
    assert sounds.events == [SoundEvent.ERROR]
