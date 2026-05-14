"""Сервис выбора и повторной печати принтера."""

from __future__ import annotations

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.models.packing import CloseBoxResultDto
from chestniy_znak_desktop.api.models.printer import ClientPrinterSelectionDto


class PrinterService:
    """Работает с принтерами ЧЗ, выбранными для текущего desktop-устройства."""

    def __init__(self, api_client: ApiClient) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client

    def get_selection(self, device_id: str) -> ClientPrinterSelectionDto:
        """Получает список принтеров и текущий выбор устройства."""

        payload = self._api_client.get(
            "chestniy-znak/packing/printer/printers",
            params={"device_id": device_id},
        )
        return ClientPrinterSelectionDto.model_validate(payload)

    def set_selection(self, device_id: str, printer_id: int) -> ClientPrinterSelectionDto:
        """Сохраняет выбранный принтер для устройства."""

        payload = self._api_client.post(
            "chestniy-znak/packing/printer/printer-selection",
            json={"device_id": device_id, "printer_id": printer_id},
        )
        return ClientPrinterSelectionDto.model_validate(payload)

    def print_box_label(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Запускает повторную печать этикетки коробки."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/printer/boxes/{box_id}/print",
            params={"device_id": device_id},
        )
        return CloseBoxResultDto.model_validate(payload)
