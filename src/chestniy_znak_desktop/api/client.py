"""HTTP-клиент backend API."""

from __future__ import annotations

from collections.abc import Mapping
from http.cookiejar import MozillaCookieJar
from typing import Any

import httpx

from chestniy_znak_desktop.api.errors import (
    ApiError,
    PlantSubscriptionExpiredError,
    UnauthorizedError,
)
from chestniy_znak_desktop.api.session_store import (
    BearerSession,
    FileBearerTokenStore,
    FileCookieStore,
)
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.i18n import language_headers, normalize_language


class ApiClient:
    """Оборачивает `httpx.Client` и хранит cookies сессии."""

    def __init__(
        self,
        config: AppConfig,
        cookie_store: FileCookieStore | None = None,
        bearer_store: FileBearerTokenStore | None = None,
        language: str = "ru",
    ) -> None:
        """Создает HTTP-клиент для указанной конфигурации."""

        self._config = config
        self._language = normalize_language(language)
        self._cookie_store = cookie_store
        self._cookie_jar = cookie_store.load() if cookie_store else MozillaCookieJar()
        self._bearer_store = bearer_store
        self._bearer_session = bearer_store.load() if bearer_store else None
        self._client = httpx.Client(
            base_url=config.api_base_url,
            timeout=config.request_timeout_sec,
            follow_redirects=False,
            cookies=self._cookie_jar,
        )

    @property
    def device_id(self) -> str:
        """Возвращает локальный идентификатор desktop-устройства."""

        return self._config.device_id

    @property
    def is_saas_api(self) -> bool:
        """Возвращает `True`, если клиент настроен на Marking Platform API v1."""

        return "/api/v1" in str(self._client.base_url)

    @property
    def has_bearer_session(self) -> bool:
        """Возвращает `True`, если сохранена bearer-сессия SaaS."""

        return self._bearer_session is not None

    @property
    def language(self) -> str:
        """Возвращает язык API-ответов."""

        return self._language

    def set_language(self, language: str) -> None:
        """Обновляет язык API-ответов для новых запросов."""

        self._language = normalize_language(language)

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

    def set_bearer_tokens(self, access_token: str, refresh_token: str) -> None:
        """Сохраняет bearer-токены SaaS app-сессии."""

        self._bearer_session = BearerSession(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        self.save_bearer_tokens()

    def save_bearer_tokens(self) -> None:
        """Сохраняет bearer-токены на диск, если задано хранилище."""

        if self._bearer_store is not None and self._bearer_session is not None:
            self._bearer_store.save(self._bearer_session)

    def clear_bearer_tokens(self) -> None:
        """Очищает bearer-токены SaaS app-сессии."""

        self._bearer_session = None
        if self._bearer_store is not None:
            self._bearer_store.clear()

    def get(self, url: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Выполняет GET-запрос и возвращает JSON-словарь."""

        return self._request("GET", url, params=params)

    def get_bytes(self, url: str, params: Mapping[str, Any] | None = None) -> bytes:
        """Выполняет GET-запрос и возвращает бинарное тело ответа."""

        return self._request_response("GET", url, params=params).content

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

        response = self._request_response(method, url, **kwargs)
        payload = response.json() if response.content else {}
        if not isinstance(payload, dict):
            raise ApiError("Backend вернул неожиданный формат ответа")
        return payload

    def _request_response(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Отправляет HTTP-запрос и возвращает сырой ответ после проверки ошибок."""

        retry_auth = bool(kwargs.pop("_retry_auth", True))
        request_url = self._surface_url(url)
        kwargs = self._with_language_headers(kwargs)
        kwargs = self._with_csrf_header(method, kwargs)
        kwargs = self._with_bearer_header(request_url, kwargs)
        response = self._client.request(method, request_url, **kwargs)
        if (
            response.status_code == 401
            and retry_auth
            and self._bearer_session is not None
            and not self._is_public_url(request_url)
            and self._refresh_bearer_session()
        ):
            return self._request_response(method, request_url, _retry_auth=False, **kwargs)
        if response.status_code == 401:
            raise UnauthorizedError(self._extract_error_message(response))
        if response.status_code == 402 and self._extract_error_code(response) == (
            "plant_subscription_inactive"
        ):
            raise PlantSubscriptionExpiredError(self._extract_error_message(response))
        if response.is_error:
            raise ApiError(self._extract_error_message(response))
        self.save_cookies()
        return response

    def _refresh_bearer_session(self) -> bool:
        """Обновляет SaaS access token через refresh token."""

        if self._bearer_session is None:
            return False
        try:
            payload = self._request(
                "POST",
                "public/auth/refresh",
                json={"refresh_token": self._bearer_session.refresh_token},
                _retry_auth=False,
            )
        except ApiError:
            self.clear_bearer_tokens()
            return False
        data = self.unwrap_data(payload)
        access_token = str(data.get("access_token") or "")
        refresh_token = str(data.get("refresh_token") or "")
        if not access_token or not refresh_token:
            self.clear_bearer_tokens()
            return False
        self.set_bearer_tokens(access_token, refresh_token)
        return True

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

    def _with_bearer_header(self, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Добавляет Authorization bearer для SaaS app API."""

        if self._bearer_session is None or self._is_public_url(url):
            return kwargs
        headers = dict(kwargs.get("headers") or {})
        headers["Authorization"] = f"Bearer {self._bearer_session.access_token}"
        kwargs["headers"] = headers
        return kwargs

    def _with_language_headers(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Добавляет заголовки языка для локализованных backend-ответов."""

        headers = dict(kwargs.get("headers") or {})
        headers.update(language_headers(self._language))
        kwargs["headers"] = headers
        return kwargs

    def _surface_url(self, url: str) -> str:
        """Добавляет TSD surface-prefix для SaaS рабочих endpoint."""

        if not self.is_saas_api or self._is_public_url(url):
            return url
        clean_url = url.lstrip("/")
        if self._has_surface_prefix(clean_url) or "://" in clean_url:
            return url
        return f"tsd/{clean_url}"

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
    def _is_public_url(url: str) -> bool:
        """Возвращает `True` для публичных SaaS endpoint."""

        clean_url = url.lstrip("/")
        return clean_url.startswith("public/") or "/public/" in clean_url

    @staticmethod
    def _has_surface_prefix(clean_url: str) -> bool:
        """Возвращает `True`, если URL уже содержит surface-prefix API."""

        return clean_url.startswith(("plant/", "supplier/", "tsd/", "admin/", "integration/"))

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Достает человекочитаемое сообщение из ошибочного ответа."""

        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"
        if isinstance(payload, dict):
            nested_error = payload.get("error")
            if isinstance(nested_error, dict):
                return str(nested_error.get("message") or nested_error)
            return str(payload.get("message") or payload.get("detail") or payload)
        return str(payload)

    @staticmethod
    def _extract_error_code(response: httpx.Response) -> str:
        """Достает машинный код ошибки из ответа backend."""

        try:
            payload = response.json()
        except ValueError:
            return ""
        if not isinstance(payload, dict):
            return ""
        nested_error = payload.get("error")
        if isinstance(nested_error, dict):
            return str(nested_error.get("code") or "")
        return str(payload.get("code") or "")

    @staticmethod
    def unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
        """Возвращает `data` из envelope-ответа SaaS или исходный payload."""

        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return payload
