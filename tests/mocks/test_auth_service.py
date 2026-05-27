"""Mock-тесты сервиса авторизации."""

from __future__ import annotations

from typing import Any

from chestniy_znak_desktop.api.services.auth_service import AuthService


class FakeSaasApiClient:
    """Fake ApiClient для SaaS-ветки AuthService."""

    is_saas_api = True
    device_id = "desktop-1"

    def __init__(self) -> None:
        """Создает fake-клиент с журналом вызовов."""

        self.posts: list[tuple[str, dict[str, Any] | None]] = []
        self.saved_tokens: tuple[str, str] | None = None

    def post(self, url: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Возвращает успешный login envelope."""

        self.posts.append((url, json))
        return {
            "data": {
                "access_token": "access-1",
                "refresh_token": "refresh-1",
            }
        }

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает SaaS /tsd/bootstrap envelope."""

        assert url == "tsd/bootstrap"
        assert params == {"client_device_id": "desktop-1"}
        return {
            "data": {
                "authenticated": True,
                "user": {
                    "id": "user-1",
                    "display_name": "Оператор SaaS",
                },
                "supplier": {
                    "id": "supplier-1",
                    "name": "Поставщик",
                },
                "plant": {
                    "id": "plant-1",
                    "name": "Завод",
                },
                "context": {
                    "supplier_id": "supplier-1",
                    "plant_id": "plant-1",
                    "device_id": "device-1",
                    "client_device_id": "desktop-1",
                },
                "subscription": {
                    "status": "active",
                },
            }
        }

    def unwrap_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Повторяет поведение ApiClient.unwrap_data."""

        data = payload.get("data")
        return data if isinstance(data, dict) else payload

    def set_bearer_tokens(self, access_token: str, refresh_token: str) -> None:
        """Запоминает токены."""

        self.saved_tokens = (access_token, refresh_token)


def test_auth_service_saas_login_uses_device_and_returns_context() -> None:
    """Проверяет вход app-токеном с device_uid и контекстом завода."""

    client = FakeSaasApiClient()
    account = AuthService(client).login_by_token("login-token")  # type: ignore[arg-type]

    assert client.posts == [
        (
            "public/accounts/login/token",
            {"token": "login-token", "device_uid": "desktop-1"},
        )
    ]
    assert client.saved_tokens == ("access-1", "refresh-1")
    assert account.username == "Оператор SaaS"
    assert account.plant_id == "plant-1"
    assert account.device_id == "device-1"
    assert account.supplier_id == "supplier-1"
    assert account.supplier_name == "Поставщик"
    assert account.plant_name == "Завод"
    assert account.client_device_id == "desktop-1"
    assert account.subscription_status == "active"
