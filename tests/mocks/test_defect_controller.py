"""Mock-тесты контроллера брака."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.verify import (
    DefectRemovedBoxDto,
    DefectResponseDto,
    RemoteCodeDto,
    VerifyResponseDto,
)
from chestniy_znak_desktop.controllers.defect_controller import DefectController
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


class FakeDefectService:
    """Fake backend брака."""

    def __init__(self) -> None:
        """Создает fake-сервис с последним вызовом."""

        self.last_call: tuple[str, str] | None = None
        self.error: Exception | None = None
        self.result = DefectResponseDto(
            ok=True,
            reason_code="defect_marked",
            verify=VerifyResponseDto(
                status="OK",
                message="Код найден",
                code=RemoteCodeDto(
                    id=1,
                    gtin="04601234567890",
                    serial="SERIAL",
                    visible_code="010460123456789021SERIAL",
                    order_name="26-0001",
                    device_name="Device",
                ),
            ),
            removed_from_box=DefectRemovedBoxDto(box_id=10, sscc="SSCC", filled=3),
        )

    def mark_defect(self, code: str, scanner_id: str) -> DefectResponseDto:
        """Возвращает результат отметки брака."""

        self.last_call = (code, scanner_id)
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


def _controller_pair() -> tuple[DefectController, FakeDefectService, FakeSoundService]:
    """Создает controller с fake-зависимостями."""

    service = FakeDefectService()
    sounds = FakeSoundService()
    controller = DefectController(
        defect_service=service,
        task_runner=ImmediateTaskRunner(),
        scanner_id="desktop-com-defect",
        sound_service=sounds,
    )
    return controller, service, sounds


def test_defect_controller_marks_scanned_code() -> None:
    """Проверяет отправку скана в сценарий брака."""

    controller, service, sounds = _controller_pair()

    controller.on_code_scanned("CODE")

    assert service.last_call == ("CODE", "desktop-com-defect")
    assert controller.state.status_message == "Код обработан"
    assert controller.state.result_message == "Код отправлен в брак"
    assert controller.state.order_name == "26-0001"
    assert controller.state.removed_box_message == "Удалено из коробки #10 | SSCC | остаток 3"
    assert sounds.events == [SoundEvent.WARNING]


def test_defect_controller_reports_rejected_scan() -> None:
    """Проверяет отображение отклоненного скана."""

    controller, service, sounds = _controller_pair()
    service.result = DefectResponseDto(
        ok=False,
        reason_code="scan_rejected",
        error="Некорректный код",
    )

    controller.on_code_scanned("BAD")

    assert controller.state.error_message == "Некорректный код"
    assert sounds.events == [SoundEvent.WARNING]


def test_defect_controller_reports_backend_error() -> None:
    """Проверяет ошибку backend-сценария брака."""

    controller, service, sounds = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.on_code_scanned("CODE")

    assert controller.state.status_message == "Ошибка отправки в брак"
    assert controller.state.error_message == "Backend недоступен"
    assert sounds.events == [SoundEvent.ERROR]
