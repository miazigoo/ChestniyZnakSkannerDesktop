"""Сервис авторизации backend."""

from __future__ import annotations

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.models.auth import AccountDto, AuthCheckDto


class AuthService:
    """Выполняет вход, выход и проверку сессии."""

    def __init__(self, api_client: ApiClient) -> None:
        """Сохраняет API-клиент для запросов авторизации."""

        self._api_client = api_client

    def login_by_token(self, token: str) -> AccountDto:
        """Авторизует пользователя по токену из QR или сканера."""

        payload = self._api_client.post("accounts/login/token", json={"token": token})
        return AccountDto.model_validate(payload)

    def auth_check(self) -> AuthCheckDto:
        """Проверяет текущую cookie-сессию."""

        payload = self._api_client.get("auth-check")
        return AuthCheckDto.model_validate(payload)

    def logout(self) -> None:
        """Завершает сессию пользователя на backend."""

        self._api_client.post("accounts/logout")
        self._api_client.clear_cookies()
