"""Контроллер выбора принтера."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.printer import (
    ClientPrinterDto,
    ClientPrinterSelectionDto,
)
from chestniy_znak_desktop.runtime.task_runner import TaskRunner


class PrinterBackend(Protocol):
    """Контракт backend-сервиса выбора принтера."""

    def get_selection(self, device_id: str) -> ClientPrinterSelectionDto:
        """Возвращает список принтеров и текущий выбор устройства."""

    def set_selection(self, device_id: str, printer_id: int) -> ClientPrinterSelectionDto:
        """Сохраняет выбранный принтер для устройства."""


@dataclass(frozen=True, slots=True)
class PrinterOptionUi:
    """UI-модель доступного принтера."""

    id: int
    title: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class PrinterUiState:
    """Состояние UI выбора принтера."""

    printers: list[PrinterOptionUi] = field(default_factory=list)
    selected_printer_id: int | None = None
    is_busy: bool = False
    status_message: str = "Принтер не выбран"
    error_message: str = ""


class PrinterController(QObject):
    """Загружает доступные принтеры и сохраняет выбор устройства."""

    state_changed = Signal(PrinterUiState)

    def __init__(
        self,
        printer_service: PrinterBackend,
        task_runner: TaskRunner,
        device_id: str,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер выбора принтера."""

        super().__init__(parent)
        self._printer_service = printer_service
        self._task_runner = task_runner
        self._device_id = device_id
        self._state = PrinterUiState()

    @property
    def state(self) -> PrinterUiState:
        """Возвращает текущее состояние выбора принтера."""

        return self._state

    def refresh(self) -> None:
        """Загружает список принтеров и текущий выбор."""

        if self._state.is_busy:
            return
        self._set_state(
            PrinterUiState(
                printers=self._state.printers,
                selected_printer_id=self._state.selected_printer_id,
                is_busy=True,
                status_message="Загружаем принтеры...",
            )
        )
        self._task_runner.submit(
            lambda: self._printer_service.get_selection(self._device_id),
            self._on_selection_loaded,
            self._on_error,
        )

    def select_printer(self, printer_id: int) -> None:
        """Сохраняет выбранный принтер для текущего desktop-устройства."""

        if self._state.is_busy or printer_id <= 0:
            return
        self._set_state(
            PrinterUiState(
                printers=self._state.printers,
                selected_printer_id=printer_id,
                is_busy=True,
                status_message="Сохраняем выбранный принтер...",
            )
        )
        self._task_runner.submit(
            lambda: self._printer_service.set_selection(self._device_id, printer_id),
            self._on_selection_loaded,
            self._on_error,
        )

    def _on_selection_loaded(self, result: object) -> None:
        """Обрабатывает загруженный или сохраненный выбор принтера."""

        if not isinstance(result, ClientPrinterSelectionDto):
            raise TypeError("Ожидался результат ClientPrinterSelectionDto")
        self._set_state(
            PrinterUiState(
                printers=[self._printer_to_ui(printer) for printer in result.printers],
                selected_printer_id=result.selected_printer_id,
                status_message=self._status_message(result),
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Обрабатывает ошибку загрузки или сохранения принтера."""

        self._set_state(
            PrinterUiState(
                printers=self._state.printers,
                selected_printer_id=self._state.selected_printer_id,
                status_message="Ошибка настройки принтера",
                error_message=str(exc),
            )
        )

    def _set_state(self, state: PrinterUiState) -> None:
        """Сохраняет и публикует состояние выбора принтера."""

        self._state = state
        self.state_changed.emit(state)

    @staticmethod
    def _printer_to_ui(printer: ClientPrinterDto) -> PrinterOptionUi:
        """Преобразует DTO принтера в UI-модель."""

        section = f" | {printer.section}" if printer.section else ""
        active = "" if printer.is_active else " | неактивен"
        return PrinterOptionUi(
            id=printer.id,
            title=f"{printer.name} | {printer.ip_address}{section}{active}",
            is_active=printer.is_active,
        )

    @staticmethod
    def _status_message(selection: ClientPrinterSelectionDto) -> str:
        """Возвращает текст состояния выбранного принтера."""

        if selection.selected_printer is not None:
            return f"Выбран принтер: {selection.selected_printer.name}"
        if selection.selected_printer_id is not None:
            return f"Выбран принтер #{selection.selected_printer_id}"
        return "Принтер не выбран"
