"""Mock-тесты HTTP-клиента backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import httpx
import pytest

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.errors import (
    ApiError,
    PlantSubscriptionExpiredError,
    UnauthorizedError,
)
from chestniy_znak_desktop.app.config import AppConfig


def test_api_client_get_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет успешный GET без настоящего сетевого запроса."""

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Возвращает тестовый ответ вместо сетевого вызова."""

        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"))
    assert client.get("health") == {"ok": True}


def test_api_client_raises_on_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет преобразование 401 в доменную ошибку авторизации."""

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Возвращает 401 вместо сетевого вызова."""

        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(401, json={"detail": "Нет сессии"}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"))
    with pytest.raises(UnauthorizedError, match="Нет сессии"):
        client.get("auth-check")


def test_api_client_treats_forbidden_as_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет, что 403 не разлогинивает приложение как истекшая сессия."""

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Возвращает 403 вместо сетевого вызова."""

        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(403, json={"detail": "CSRF check Failed"}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"))
    with pytest.raises(ApiError, match="CSRF check Failed"):
        client.post("chestniy-znak/packing/boxes/open")


def test_api_client_adds_csrf_header_for_post(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет отправку CSRF-заголовка для POST-запросов."""

    seen_headers: dict[str, str] = {}

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Запоминает заголовки запроса."""

        seen_headers.update(cast(Mapping[str, str], kwargs.get("headers") or {}))
        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"))
    client._client.cookies.set("csrftoken", "csrf-123")  # noqa: SLF001

    assert client.post("chestniy-znak/packing/boxes/open") == {"ok": True}
    assert seen_headers["X-CSRFToken"] == "csrf-123"


def test_api_client_adds_language_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет отправку выбранного языка в backend."""

    seen_headers: dict[str, str] = {}

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Запоминает заголовки запроса."""

        seen_headers.update(cast(Mapping[str, str], kwargs.get("headers") or {}))
        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"), language="zh-CN")

    assert client.get("health") == {"ok": True}
    assert seen_headers["X-App-Language"] == "zh"
    assert seen_headers["X-Language"] == "zh"
    assert seen_headers["Accept-Language"].startswith("zh-CN")


def test_api_client_adds_bearer_header_for_saas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет отправку SaaS access token в Authorization."""

    seen_headers: dict[str, str] = {}
    seen_urls: list[str] = []

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Запоминает заголовки запроса."""

        seen_headers.update(cast(Mapping[str, str], kwargs.get("headers") or {}))
        seen_urls.append(url)
        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"data": {"ok": True}}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v1/"))
    client.set_bearer_tokens("access-1", "refresh-1")

    assert client.get("tsd/me") == {"data": {"ok": True}}
    assert seen_headers["Authorization"] == "Bearer access-1"
    assert seen_urls == ["tsd/me"]


def test_api_client_adds_tsd_surface_prefix_for_saas_work_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет совместимость старых рабочих URL с SaaS TSD surface."""

    seen_urls: list[str] = []

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Запоминает URL запроса."""

        seen_urls.append(url)
        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v1/"))
    client.set_bearer_tokens("access-1", "refresh-1")

    assert client.get("chestniy-znak/packing/boxes") == {"ok": True}
    assert seen_urls == ["tsd/chestniy-znak/packing/boxes"]


def test_api_client_raises_subscription_expired_for_saas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет понятную ошибку при истекшей подписке завода."""

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Возвращает SaaS envelope с ошибкой подписки."""

        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(
            402,
            json={
                "error": {
                    "code": "plant_subscription_inactive",
                    "message": "Подписка завода закончилась",
                }
            },
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v1/"))

    with pytest.raises(PlantSubscriptionExpiredError, match="Подписка завода закончилась"):
        client.get("tsd/me")


def test_api_client_refreshes_saas_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет refresh access token и повтор исходного запроса."""

    calls: list[tuple[str, str, str]] = []

    def fake_request(self: httpx.Client, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Имитирует 401, refresh и успешный повтор."""

        headers = cast(Mapping[str, str], kwargs.get("headers") or {})
        auth_header = headers.get("Authorization", "")
        calls.append((method, url, auth_header))
        request = httpx.Request(method, f"http://test/{url}")
        if url == "tsd/me" and len(calls) == 1:
            return httpx.Response(401, json={"detail": "token expired"}, request=request)
        if url == "public/auth/refresh":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "access_token": "access-new",
                        "refresh_token": "refresh-new",
                    }
                },
                request=request,
            )
        return httpx.Response(200, json={"data": {"ok": True}}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v1/"))
    client.set_bearer_tokens("access-old", "refresh-old")

    assert client.get("tsd/me") == {"data": {"ok": True}}
    assert calls == [
        ("GET", "tsd/me", "Bearer access-old"),
        ("POST", "public/auth/refresh", ""),
        ("GET", "tsd/me", "Bearer access-new"),
    ]
