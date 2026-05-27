"""Сервис рабочих заказов SaaS для упаковки."""

from __future__ import annotations

from chestniy_znak_desktop.api.models.orders import WorkOrderPageDto
from chestniy_znak_desktop.api.services.api_client_protocol import ApiClientProtocol


class OrderService:
    """Получает заказы и строки номенклатуры для Desktop/TSD сценариев."""

    def __init__(self, api_client: ApiClientProtocol) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client

    def list_orders(
        self,
        status: str | None = None,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> WorkOrderPageDto:
        """Возвращает рабочие заказы, доступные текущему app-токену."""

        params: dict[str, object] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        if search.strip():
            params["search"] = search.strip()
        payload = self._api_client.get("orders", params=params)
        return WorkOrderPageDto.model_validate(payload)
