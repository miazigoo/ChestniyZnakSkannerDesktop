"""Минимальный контракт HTTP-клиента для сервисного слоя."""

from __future__ import annotations

from typing import Any, Protocol


class ApiClientProtocol(Protocol):
    """Описывает методы API-клиента, которые нужны прикладным сервисам."""

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Выполняет GET-запрос."""

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Выполняет POST-запрос."""

    def patch(self, url: str, json: dict[str, Any]) -> dict[str, Any]:
        """Выполняет PATCH-запрос."""

    def delete(self, url: str) -> dict[str, Any]:
        """Выполняет DELETE-запрос."""


class BinaryApiClientProtocol(ApiClientProtocol, Protocol):
    """Контракт API-клиента для endpoints, возвращающих файлы."""

    def get_bytes(self, url: str, params: dict[str, Any] | None = None) -> bytes:
        """Выполняет GET-запрос и возвращает бинарное тело."""
