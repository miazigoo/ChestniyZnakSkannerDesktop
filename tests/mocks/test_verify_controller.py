"""Mock-тесты контроллера проверки кодов."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.verify import (
    RemoteCodeDto,
    VerifyBoxDto,
    VerifyExistsResponseDto,
)
from chestniy_znak_desktop.controllers.verify_controller import (
    VERIFY_LOG_LIMIT,
    VerifyController,
)
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


class FakeVerifyService:
    """Fake backend проверки кодов."""

    def __init__(self) -> None:
        """Создает fake-сервис с последним вызовом."""

        self.last_call: tuple[str, str, bool] | None = None
        self.error: Exception | None = None
        self.result = VerifyExistsResponseDto(
            ok=True,
            exists=True,
            status="OK",
            message="Код найден",
            order_name="26-0001",
            device_name="Device",
            code=RemoteCodeDto(
                id=1,
                gtin="04601234567890",
                serial="SERIAL",
                visible_code="010460123456789021SERIAL",
                order_name="26-0001",
                device_name="Device",
            ),
            box=VerifyBoxDto(
                box_id=101,
                sscc="SSCC-101",
                is_closed=True,
            ),
        )

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
    ) -> VerifyExistsResponseDto:
        """Возвращает результат проверки кода."""

        self.last_call = (code, scanner_id, allow_duplicate)
        if self.error is not None:
            raise self.error
        return self.result


class FakeSoundService:
    """Fake sound service для проверки звуков."""

    def __init__(self) -> None:
        """Создает список проигранных событий."""

        self.events: list[SoundEvent] = []

    def play(self, event: SoundEvent) -> None:
        """Запоминает событие звука."""

        self.events.append(event)


def _controller_pair() -> tuple[VerifyController, FakeVerifyService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakeVerifyService()
    sounds = FakeSoundService()
    controller = VerifyController(
        verify_service=service,
        task_runner=ImmediateTaskRunner(),
        scanner_id="desktop-com-verify",
        sound_service=sounds,
    )
    return controller, service, sounds


def test_verify_controller_checks_scanned_code() -> None:
    """Проверяет отправку скана в сценарий проверки."""

    controller, service, sounds = _controller_pair()

    controller.on_code_scanned("CODE")

    assert service.last_call == ("CODE", "desktop-com-verify", True)
    assert controller.state.status_message == "Код обработан"
    assert controller.state.result_message == "Код найден"
    assert controller.state.order_name == "26-0001"
    assert controller.state.device_name == "Device"
    assert controller.state.box_id == 101
    assert controller.state.box_sscc == "SSCC-101"
    assert controller.state.box_status == "закрыта"
    assert "SSCC-101" in controller.state.box_hint
    assert controller.state.exists is True
    assert sounds.events == [SoundEvent.OK]


def test_verify_controller_can_check_duplicates() -> None:
    """Проверяет режим учета дублей при проверке."""

    controller, service, _sounds = _controller_pair()

    controller.set_check_duplicates(True)
    controller.on_code_scanned("CODE")

    assert controller.state.check_duplicates is True
    assert service.last_call == ("CODE", "desktop-com-verify", False)


def test_verify_controller_keeps_only_recent_log_entries() -> None:
    """Проверяет ограничение журнала последних проверок."""

    controller, _service, _sounds = _controller_pair()

    for index in range(VERIFY_LOG_LIMIT + 5):
        controller.on_code_scanned(f"CODE-{index}")

    assert len(controller.state.log) == VERIFY_LOG_LIMIT
    assert controller.state.log[0].startswith("010460123456789021SERIAL")


def test_verify_controller_reports_missing_code() -> None:
    """Проверяет отображение отсутствующего кода."""

    controller, service, sounds = _controller_pair()
    service.result = VerifyExistsResponseDto(
        ok=False,
        exists=False,
        status="NOT_FOUND",
        message="Код не найден",
        order_name="",
        device_name="",
    )

    controller.on_code_scanned("BAD")

    assert controller.state.error_message == "Код не найден"
    assert controller.state.exists is False
    assert controller.state.box_id is None
    assert controller.state.box_status == "не упакован"
    assert sounds.events == [SoundEvent.ERROR]


def test_verify_controller_reports_backend_error() -> None:
    """Проверяет ошибку backend-сценария проверки."""

    controller, service, sounds = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.on_code_scanned("CODE")

    assert controller.state.status_message == "Ошибка проверки кода"
    assert controller.state.error_message == "Backend недоступен"
    assert sounds.events == [SoundEvent.ERROR]
