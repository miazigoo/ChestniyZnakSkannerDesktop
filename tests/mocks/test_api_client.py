"""Mock-тесты HTTP-клиента backend."""

from __future__ import annotations

import httpx
import pytest

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.errors import ApiError, UnauthorizedError
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

        seen_headers.update(kwargs.get("headers") or {})  # type: ignore[arg-type]
        request = httpx.Request(method, f"http://test/{url}")
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(httpx.Client, "request", fake_request)
    client = ApiClient(AppConfig(api_base_url="http://test/api/v2/"))
    client._client.cookies.set("csrftoken", "csrf-123")  # noqa: SLF001

    assert client.post("chestniy-znak/packing/boxes/open") == {"ok": True}
    assert seen_headers["X-CSRFToken"] == "csrf-123"
