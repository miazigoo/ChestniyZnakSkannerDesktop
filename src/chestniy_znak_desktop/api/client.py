"""HTTP-клиент backend API."""

from __future__ import annotations

from collections.abc import Mapping
from http.cookiejar import MozillaCookieJar
from typing import Any

import httpx

from chestniy_znak_desktop.api.errors import ApiError, UnauthorizedError
from chestniy_znak_desktop.api.session_store import FileCookieStore
from chestniy_znak_desktop.app.config import AppConfig


class ApiClient:
    """Оборачивает `httpx.Client` и хранит cookies сессии."""

    def __init__(self, config: AppConfig, cookie_store: FileCookieStore | None = None) -> None:
        """Создает HTTP-клиент для указанной конфигурации."""

        self._cookie_store = cookie_store
        self._cookie_jar = cookie_store.load() if cookie_store else MozillaCookieJar()
        self._client = httpx.Client(
            base_url=config.api_base_url,
            timeout=config.request_timeout_sec,
            follow_redirects=False,
            cookies=self._cookie_jar,
        )

    def close(self) -> None:
        """Закрывает сетевые ресурсы клиента."""

        self.save_cookies()
        self._client.close()

    def save_cookies(self) -> None:
        """Сохраняет cookies текущей сессии, если задано хранилище."""

        if self._cookie_store is not None:
            self._cookie_store.save(self._cookie_jar)

    def clear_cookies(self) -> None:
        """Очищает cookies в памяти и на диске."""

        self._client.cookies.clear()
        self._cookie_jar.clear()
        if self._cookie_store is not None:
            self._cookie_store.clear()

    def get(self, url: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Выполняет GET-запрос и возвращает JSON-словарь."""

        return self._request("GET", url, params=params)

    def post(
        self,
        url: str,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Выполняет POST-запрос и возвращает JSON-словарь."""

        return self._request("POST", url, json=json, params=params)

    def patch(self, url: str, json: Mapping[str, Any]) -> dict[str, Any]:
        """Выполняет PATCH-запрос и возвращает JSON-словарь."""

        return self._request("PATCH", url, json=json)

    def delete(self, url: str) -> dict[str, Any]:
        """Выполняет DELETE-запрос и возвращает JSON-словарь."""

        return self._request("DELETE", url)

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """Отправляет HTTP-запрос и обрабатывает типовые ошибки backend."""

        kwargs = self._with_csrf_header(method, kwargs)
        response = self._client.request(method, url, **kwargs)
        if response.status_code == 401:
            raise UnauthorizedError(self._extract_error_message(response))
        if response.is_error:
            raise ApiError(self._extract_error_message(response))
        self.save_cookies()
        payload = response.json() if response.content else {}
        if not isinstance(payload, dict):
            raise ApiError("Backend вернул неожиданный формат ответа")
        return payload

    def _with_csrf_header(self, method: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Добавляет CSRF-заголовок для небезопасных HTTP-методов."""

        if method.upper() not in {"POST", "PATCH", "PUT", "DELETE"}:
            return kwargs
        csrf_token = self._csrf_token()
        if not csrf_token:
            return kwargs
        headers = dict(kwargs.get("headers") or {})
        headers.setdefault("X-CSRFToken", csrf_token)
        kwargs["headers"] = headers
        return kwargs

    def _csrf_token(self) -> str:
        """Возвращает CSRF-токен из cookies текущей сессии."""

        token = self._client.cookies.get("csrftoken")
        if token:
            return token
        for cookie in self._cookie_jar:
            if cookie.name == "csrftoken" and cookie.value is not None:
                return cookie.value
        return ""

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Достает человекочитаемое сообщение из ошибочного ответа."""

        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"
        if isinstance(payload, dict):
            return str(payload.get("message") or payload.get("detail") or payload)
        return str(payload)
