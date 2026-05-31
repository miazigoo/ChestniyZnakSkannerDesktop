"""Сервис выбора принтера и печати SSCC-этикеток коробок."""

from __future__ import annotations

from typing import Any

from chestniy_znak_desktop.api.models.printers import (
    ClientPrinterSelectionDto,
    PackageLabelPrintResultDto,
)
from chestniy_znak_desktop.api.services.api_client_protocol import ApiClientProtocol
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.services.print_transport import PrintTransport, RawTcpPrintTransport


class PrinterService:
    """Работает с принтерами поставщика и локальной печатью SSCC."""

    def __init__(
        self,
        api_client: ApiClientProtocol,
        print_transport: PrintTransport | None = None,
    ) -> None:
        """Сохраняет зависимости сервиса."""

        self._api_client = api_client
        self._print_transport = print_transport or RawTcpPrintTransport()

    def get_selection(self, device_id: str) -> ClientPrinterSelectionDto:
        """Возвращает список активных принтеров и текущий выбор рабочего места."""

        payload = self._api_client.get(
            "chestniy-znak/packing/printer/printers",
            params={"device_id": device_id},
        )
        return ClientPrinterSelectionDto.model_validate(_unwrap_data(payload))

    def select_printer(self, device_id: str, printer_id: int) -> ClientPrinterSelectionDto:
        """Сохраняет выбранный принтер для рабочего места."""

        payload = self._api_client.post(
            "chestniy-znak/packing/printer/printer-selection",
            json={"device_id": device_id, "printer_id": printer_id},
        )
        return ClientPrinterSelectionDto.model_validate(_unwrap_data(payload))

    def prepare_box_label(
        self,
        box_id: int,
        device_id: str,
        printer_id: int | None = None,
    ) -> PackageLabelPrintResultDto:
        """Запрашивает у backend задание печати SSCC для коробки."""

        request: dict[str, Any] = {"device_id": device_id}
        if printer_id is not None:
            request["printer_id"] = printer_id
        payload = self._api_client.post(
            f"chestniy-znak/packing/boxes/{box_id}/print-label",
            json=request,
        )
        return PackageLabelPrintResultDto.model_validate(_unwrap_data(payload))

    def report_box_label_print(
        self,
        box_id: int,
        device_id: str,
        *,
        printer_id: int | None,
        print_ok: bool,
        print_error: str,
    ) -> PackageLabelPrintResultDto:
        """Отправляет backend итог локальной печати SSCC."""

        request: dict[str, Any] = {
            "device_id": device_id,
            "print_ok": print_ok,
            "print_error": print_error,
        }
        if printer_id is not None:
            request["printer_id"] = printer_id
        payload = self._api_client.post(
            f"chestniy-znak/packing/boxes/{box_id}/print-result",
            json=request,
        )
        return PackageLabelPrintResultDto.model_validate(_unwrap_data(payload))

    def print_box_label(self, box_id: int, device_id: str) -> PackageLabelPrintResultDto:
        """Готовит, печатает и подтверждает SSCC-этикетку коробки."""

        selection = self._selection_with_single_printer_autoselect(device_id)
        prepared = self.prepare_box_label(
            box_id,
            device_id,
            printer_id=selection.selected_printer_id,
        )
        job = prepared.print_job
        if job is None:
            return prepared
        print_ok, print_error = self._print_transport.send(job)
        printer_id = job.printer.id if job.printer is not None else None
        try:
            return self.report_box_label_print(
                box_id,
                device_id,
                printer_id=printer_id,
                print_ok=print_ok,
                print_error=print_error,
            )
        except Exception:
            if print_ok:
                raise
            return PackageLabelPrintResultDto(
                ok=False,
                reason_code="label_print_failed",
                print_status="failed",
                print_ok=False,
                print_error_code="printer_job_failed",
                print_error=print_error or tr("printer.reportFailed"),
                printer=job.printer,
                print_job=job,
            )

    def _selection_with_single_printer_autoselect(
        self,
        device_id: str,
    ) -> ClientPrinterSelectionDto:
        """Автоматически выбирает единственный активный принтер для нового рабочего места."""

        selection = self.get_selection(device_id)
        if selection.selected_printer_id is None and len(selection.printers) == 1:
            return self.select_printer(device_id, selection.printers[0].id)
        return selection


def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload
