"""Сервис упаковки кодов в коробки."""

from __future__ import annotations

from chestniy_znak_desktop.api.errors import ApiError
from chestniy_znak_desktop.api.models.packing import (
    BoxActionResultDto,
    BoxDetailDto,
    BoxListDto,
    CloseBoxResultDto,
    OpenBoxResultDto,
    ScanBatchToBoxResultDto,
    ScanToBoxResultDto,
)
from chestniy_znak_desktop.api.services.api_client_protocol import ApiClientProtocol


class PackingService:
    """Работает с backend-сценариями коробок Честного знака."""

    def __init__(self, api_client: ApiClientProtocol) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client

    def list_boxes(
        self,
        status: str = "all",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> BoxListDto:
        """Возвращает страницу коробок с фильтром и поиском."""

        payload = self._api_client.get(
            "chestniy-znak/packing/boxes",
            params={"status": status, "query": query, "limit": limit, "offset": offset},
        )
        return BoxListDto.model_validate(payload)

    def current_box(self) -> BoxDetailDto | None:
        """Возвращает текущую открытую коробку или `None`."""

        try:
            payload = self._api_client.get("chestniy-znak/packing/boxes/current")
        except ApiError as exc:
            if "Открытая коробка не найдена" in str(exc):
                return None
            raise
        return BoxDetailDto.model_validate(payload)

    def get_box(self, box_id: int) -> BoxDetailDto:
        """Возвращает детальную карточку коробки по ID."""

        payload = self._api_client.get(f"chestniy-znak/packing/boxes/{box_id}")
        result = BoxActionResultDto.model_validate(payload)
        return BoxDetailDto.model_validate(result.box.model_dump())

    def open_box(
        self,
        device_id: str,
        count_in_packing: bool = True,
        order_id: str | None = None,
        order_line_id: str | None = None,
        code_value: str | None = None,
        sscc: str | None = None,
    ) -> OpenBoxResultDto:
        """Открывает новую коробку или возвращает активную коробку пользователя."""

        request = {"device_id": device_id, "count_in_packing": count_in_packing}
        optional_fields = {
            "order_id": order_id,
            "order_line_id": order_line_id,
            "code_value": code_value,
            "sscc": sscc,
        }
        request.update({key: value for key, value in optional_fields.items() if value})
        payload = self._api_client.post(
            "chestniy-znak/packing/boxes/open",
            json=request,
        )
        return OpenBoxResultDto.model_validate(payload)

    def scan_to_box(self, box_id: int, code: str, scanner_id: str) -> ScanToBoxResultDto:
        """Добавляет отсканированный код в коробку."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/boxes/{box_id}/scan",
            json={"code": code, "scanner_id": scanner_id},
        )
        return ScanToBoxResultDto.model_validate(payload)

    def scan_batch_to_box(
        self,
        box_id: int,
        codes: list[str],
        scanner_id: str,
    ) -> ScanBatchToBoxResultDto:
        """Атомарно добавляет пачку отсканированных кодов в коробку."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/boxes/{box_id}/scan-batch",
            json={"codes": codes, "scanner_id": scanner_id},
        )
        return ScanBatchToBoxResultDto.model_validate(payload)

    def close_box(self, box_id: int, device_id: str) -> CloseBoxResultDto:
        """Закрывает коробку на backend."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/boxes/{box_id}/close",
            params={"device_id": device_id},
        )
        return CloseBoxResultDto.model_validate(payload)

    def set_count_in_packing(self, box_id: int, count_in_packing: bool) -> BoxActionResultDto:
        """Переключает учет коробки в упаковке заказа."""

        payload = self._api_client.patch(
            f"chestniy-znak/packing/boxes/{box_id}/count-in-packing",
            json={"count_in_packing": count_in_packing},
        )
        return BoxActionResultDto.model_validate(payload)
