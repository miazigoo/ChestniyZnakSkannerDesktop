"""Mock-тесты контроллера выбора принтера."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.models.printer import (
    ClientPrinterDto,
    ClientPrinterSelectionDto,
)
from chestniy_znak_desktop.controllers.printer_controller import PrinterController


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


class FakePrinterService:
    """Fake backend выбора принтера."""

    def __init__(self) -> None:
        """Создает fake-сервис с последним вызовом."""

        self.last_call: tuple[str, str, int | None] | None = None
        self.error: Exception | None = None

    def get_selection(self, device_id: str) -> ClientPrinterSelectionDto:
        """Возвращает fake список принтеров."""

        self.last_call = ("get", device_id, None)
        if self.error is not None:
            raise self.error
        return _selection(selected_printer_id=None)

    def set_selection(self, device_id: str, printer_id: int) -> ClientPrinterSelectionDto:
        """Возвращает fake сохраненный выбор."""

        self.last_call = ("set", device_id, printer_id)
        if self.error is not None:
            raise self.error
        return _selection(selected_printer_id=printer_id)


def _selection(selected_printer_id: int | None) -> ClientPrinterSelectionDto:
    """Создает DTO выбора принтера."""

    printer = ClientPrinterDto(
        id=1,
        name="Zebra",
        ip_address="172.16.8.120",
        section="A",
        is_active=True,
    )
    return ClientPrinterSelectionDto(
        ok=True,
        device_id="pc-1",
        selected_printer_id=selected_printer_id,
        selected_printer=printer if selected_printer_id == printer.id else None,
        printers=[printer],
    )


def _controller_pair() -> tuple[PrinterController, FakePrinterService]:
    """Создает контроллер с fake-сервисом."""

    service = FakePrinterService()
    controller = PrinterController(
        printer_service=service,
        task_runner=ImmediateTaskRunner(),
        device_id="pc-1",
    )
    return controller, service


def test_printer_controller_refresh_loads_printers() -> None:
    """Проверяет загрузку списка принтеров."""

    controller, service = _controller_pair()

    controller.refresh()

    assert service.last_call == ("get", "pc-1", None)
    assert controller.state.printers[0].title == "Zebra | 172.16.8.120 | A"
    assert controller.state.status_message == "Принтер не выбран"


def test_printer_controller_selects_printer() -> None:
    """Проверяет сохранение выбранного принтера."""

    controller, service = _controller_pair()

    controller.select_printer(1)

    assert service.last_call == ("set", "pc-1", 1)
    assert controller.state.selected_printer_id == 1
    assert controller.state.status_message == "Выбран принтер: Zebra"


def test_printer_controller_reports_error() -> None:
    """Проверяет ошибку загрузки принтеров."""

    controller, service = _controller_pair()
    service.error = RuntimeError("Backend недоступен")

    controller.refresh()

    assert controller.state.status_message == "Ошибка настройки принтера"
    assert controller.state.error_message == "Backend недоступен"
