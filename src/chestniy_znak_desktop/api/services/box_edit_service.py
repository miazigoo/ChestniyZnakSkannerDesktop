"""Сервис редактирования коробок Честного знака."""

from __future__ import annotations

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.models.packing import BoxActionResultDto


class BoxEditService:
    """Работает с backend-режимом редактирования коробки."""

    def __init__(self, api_client: ApiClient) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client

    def open_edit(self, box_id: int, reason: str = "") -> BoxActionResultDto:
        """Открывает коробку в режиме редактирования."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/box-edit/{box_id}/open",
            json={"reason": reason},
        )
        return BoxActionResultDto.model_validate(payload)

    def close_edit(self, box_id: int) -> BoxActionResultDto:
        """Закрывает режим редактирования коробки."""

        payload = self._api_client.post(f"chestniy-znak/packing/box-edit/{box_id}/close")
        return BoxActionResultDto.model_validate(payload)

    def remove_item(self, box_id: int, item_id: int) -> BoxActionResultDto:
        """Удаляет один код из коробки по ID строки."""

        payload = self._api_client.post(
            f"chestniy-znak/packing/box-edit/{box_id}/items/remove",
            json={"item_id": item_id},
        )
        return BoxActionResultDto.model_validate(payload)

    def clear_box(self, box_id: int) -> BoxActionResultDto:
        """Очищает коробку от всех кодов."""

        payload = self._api_client.post(f"chestniy-znak/packing/box-edit/{box_id}/clear")
        return BoxActionResultDto.model_validate(payload)

    def delete_empty_box(self, box_id: int) -> BoxActionResultDto:
        """Удаляет пустую коробку."""

        payload = self._api_client.delete(f"chestniy-znak/packing/box-edit/{box_id}/empty")
        return BoxActionResultDto.model_validate(payload)
