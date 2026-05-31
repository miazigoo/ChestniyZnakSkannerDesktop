"""Контроллер выбора SSCC-принтера рабочего места."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol, TypeVar

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.models.printers import ClientPrinterSelectionDto
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.task_runner import TaskRunner

TPrinterResult = TypeVar("TPrinterResult")


class PrinterBackend(Protocol):
    """Контракт backend-сервиса принтеров."""

    def get_selection(self, device_id: str) -> ClientPrinterSelectionDto:
        """Возвращает доступные принтеры и текущий выбор."""

    def select_printer(self, device_id: str, printer_id: int) -> ClientPrinterSelectionDto:
        """Сохраняет выбранный принтер."""


@dataclass(frozen=True, slots=True)
class PrinterOptionUi:
    """UI-модель принтера."""

    id: int
    label: str


@dataclass(frozen=True, slots=True)
class PrinterUiState:
    """Состояние выбора принтера."""

    is_busy: bool = False
    options: list[PrinterOptionUi] = field(default_factory=list)
    selected_printer_id: int | None = None
    status_message: str = field(default_factory=lambda: tr("printer.notLoaded"))
    error_message: str = ""


class PrinterController(QObject):
    """Загружает и сохраняет выбор принтера для текущего рабочего места."""

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
        """Возвращает текущее состояние."""

        return self._state

    def refresh_selection(self) -> None:
        """Загружает активные принтеры поставщика."""

        if self._state.is_busy:
            return
        self._set_state(replace(self._state, is_busy=True, error_message=""))
        self._task_runner.submit(
            lambda: self._printer_service.get_selection(self._device_id),
            self._on_selection_loaded,
            self._on_error,
        )

    def select_printer(self, printer_id: int) -> None:
        """Сохраняет принтер, выбранный оператором."""

        if self._state.is_busy or printer_id <= 0:
            return
        self._set_state(
            replace(
                self._state,
                is_busy=True,
                selected_printer_id=printer_id,
                error_message="",
                status_message=tr("printer.savingSelection"),
            )
        )
        self._task_runner.submit(
            lambda: self._printer_service.select_printer(self._device_id, printer_id),
            self._on_selection_saved,
            self._on_error,
        )

    def _on_selection_loaded(self, result: object) -> None:
        """Обрабатывает загрузку списка принтеров."""

        selection = self._expect(result, ClientPrinterSelectionDto)
        self._apply_selection(selection, status_message=self._selection_status(selection))

    def _on_selection_saved(self, result: object) -> None:
        """Обрабатывает сохранение выбора принтера."""

        selection = self._expect(result, ClientPrinterSelectionDto)
        self._apply_selection(selection, status_message=tr("printer.selectionSaved"))

    def _apply_selection(
        self,
        selection: ClientPrinterSelectionDto,
        *,
        status_message: str,
    ) -> None:
        """Публикует список принтеров в UI."""

        self._set_state(
            PrinterUiState(
                is_busy=False,
                options=[
                    PrinterOptionUi(id=printer.id, label=printer.label)
                    for printer in selection.printers
                ],
                selected_printer_id=selection.selected_printer_id,
                status_message=status_message,
                error_message="",
            )
        )

    def _on_error(self, exc: Exception) -> None:
        """Показывает ошибку работы с принтерами."""

        self._set_state(
            replace(
                self._state,
                is_busy=False,
                status_message=tr("printer.operationError"),
                error_message=str(exc),
            )
        )

    @staticmethod
    def _selection_status(selection: ClientPrinterSelectionDto) -> str:
        """Возвращает понятный статус выбора принтера."""

        if not selection.printers:
            return tr("printer.empty")
        if selection.selected_printer is not None:
            return tr("printer.selected", printer=selection.selected_printer.name)
        if len(selection.printers) == 1:
            return tr("printer.singleAvailable")
        return tr("printer.selectRequired")

    def _set_state(self, state: PrinterUiState) -> None:
        """Сохраняет и публикует состояние."""

        self._state = state
        self.state_changed.emit(state)

    @staticmethod
    def _expect(result: object, expected_type: type[TPrinterResult]) -> TPrinterResult:
        """Проверяет тип результата фоновой задачи."""

        if not isinstance(result, expected_type):
            raise TypeError(f"Ожидался результат {expected_type.__name__}")
        return result
