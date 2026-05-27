"""Сервис авторизации backend."""

from __future__ import annotations

from chestniy_znak_desktop.api.client import ApiClient
from chestniy_znak_desktop.api.models.auth import (
    AccountDto,
    AuthCheckDto,
    TsdBootstrapDto,
)


class AuthService:
    """Выполняет вход, выход и проверку сессии."""

    def __init__(self, api_client: ApiClient) -> None:
        """Сохраняет API-клиент для запросов авторизации."""

        self._api_client = api_client

    def login_by_token(self, token: str) -> AccountDto:
        """Авторизует пользователя по токену из QR или сканера."""

        if self._api_client.is_saas_api:
            payload = self._api_client.post(
                "public/accounts/login/token",
                json={
                    "token": token,
                    "device_uid": self._api_client.device_id,
                },
            )
            data = self._api_client.unwrap_data(payload)
            access_token = str(data.get("access_token") or "")
            refresh_token = str(data.get("refresh_token") or "")
            if not access_token or not refresh_token:
                raise ValueError("Backend не вернул app-токены")
            self._api_client.set_bearer_tokens(access_token, refresh_token)
            auth_check = self.auth_check()
            return AccountDto(
                id=auth_check.user_id,
                username=auth_check.user,
                plant_id=auth_check.plant_id,
                device_id=auth_check.device_id,
                supplier_id=auth_check.supplier_id,
                supplier_name=auth_check.supplier_name,
                plant_name=auth_check.plant_name,
                client_device_id=auth_check.client_device_id,
                subscription_status=auth_check.subscription_status,
            )
        payload = self._api_client.post("accounts/login/token", json={"token": token})
        return AccountDto.model_validate(payload)

    def auth_check(self) -> AuthCheckDto:
        """Проверяет текущую backend-сессию."""

        if self._api_client.is_saas_api:
            payload = self._api_client.get(
                "tsd/bootstrap",
                params={"client_device_id": self._api_client.device_id},
            )
            data = self._api_client.unwrap_data(payload)
            bootstrap = TsdBootstrapDto.model_validate(data)
            user = bootstrap.user
            context = bootstrap.context
            plant = bootstrap.plant
            supplier = bootstrap.supplier
            subscription = bootstrap.subscription
            username = str(
                (user.display_name if user else "")
                or (user.login if user else "")
                or (user.email if user else "")
                or "Оператор"
            )
            return AuthCheckDto(
                authenticated=bootstrap.authenticated,
                user=username,
                user_id=(user.id if user else "") or "",
                plant_id=(context.plant_id if context else "") or "",
                device_id=(context.device_id if context else "") or "",
                supplier_id=(context.supplier_id if context else "") or "",
                supplier_name=(supplier.name if supplier else "") or "",
                plant_name=(plant.name if plant else "") or "",
                client_device_id=(context.client_device_id if context else "") or "",
                subscription_status=(subscription.status if subscription else "") or "",
            )
        payload = self._api_client.get("auth-check")
        return AuthCheckDto.model_validate(payload)

    def logout(self) -> None:
        """Завершает сессию пользователя на backend."""

        if self._api_client.is_saas_api:
            self._api_client.clear_bearer_tokens()
            self._api_client.clear_cookies()
            return
        self._api_client.post("accounts/logout")
        self._api_client.clear_cookies()
