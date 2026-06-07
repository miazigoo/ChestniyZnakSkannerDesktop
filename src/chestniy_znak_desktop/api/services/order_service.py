"""Сервис рабочих заказов SaaS для упаковки."""

from __future__ import annotations

from chestniy_znak_desktop.api.errors import UnauthorizedError
from chestniy_znak_desktop.api.models.orders import LocalCodePoolPageDto, WorkOrderPageDto
from chestniy_znak_desktop.api.services.api_client_protocol import ApiClientProtocol
from chestniy_znak_desktop.services.order_local_pool_cache import OrderLocalPoolCache


class OrderService:
    """Получает заказы и строки номенклатуры для Desktop/TSD сценариев."""

    def __init__(
        self,
        api_client: ApiClientProtocol,
        local_pool_cache: OrderLocalPoolCache | None = None,
    ) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client
        self._local_pool_cache = local_pool_cache

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

    def download_local_pool(
        self,
        order_id: str,
        limit: int = 5000,
        offset: int = 0,
    ) -> LocalCodePoolPageDto:
        """Возвращает страницу кодов заказа для локального сканирования."""

        try:
            payload = self._api_client.get(
                f"orders/{order_id}/local-pool",
                params={"limit": limit, "offset": offset},
            )
        except UnauthorizedError:
            raise
        except Exception:
            if self._local_pool_cache is not None:
                cached = self._local_pool_cache.load_page(order_id, limit=limit, offset=offset)
                if cached is not None:
                    return cached
            raise
        page = LocalCodePoolPageDto.model_validate(payload)
        if self._local_pool_cache is not None:
            self._local_pool_cache.save_page(page)
        return page
