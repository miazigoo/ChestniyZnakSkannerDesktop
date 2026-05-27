"""DTO авторизации."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AccountDto(BaseModel):
    """Данные авторизованного пользователя."""

    id: int | str
    username: str
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    plant_id: str = ""
    device_id: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    plant_name: str = ""
    client_device_id: str = ""
    subscription_status: str = ""

    @property
    def display_name(self) -> str:
        """Возвращает отображаемое имя пользователя."""

        return " ".join([self.first_name, self.last_name]).strip() or self.username


class AuthCheckDto(BaseModel):
    """Ответ проверки текущей сессии."""

    authenticated: bool
    user: str
    user_id: int | str
    plant_id: str = ""
    device_id: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    plant_name: str = ""
    client_device_id: str = ""
    subscription_status: str = ""


class SaasUserDto(BaseModel):
    """Пользователь из SaaS bootstrap-контекста."""

    id: str | None = None
    login: str | None = None
    email: str | None = None
    display_name: str | None = None


class SaasOrganizationDto(BaseModel):
    """Организация из SaaS bootstrap-контекста."""

    id: str | None = None
    name: str | None = None
    legal_name: str | None = None


class SaasDeviceDto(BaseModel):
    """Зарегистрированное SaaS-устройство приложения."""

    id: str | None = None
    name: str | None = None
    device_uid: str | None = None
    status: str | None = None


class SaasContextDto(BaseModel):
    """Текущий app-контекст, привязанный к токену поставщика."""

    surface: str | None = None
    supplier_id: str | None = None
    plant_id: str | None = None
    device_id: str | None = None
    client_device_id: str | None = None
    role: str | None = None
    scopes: list[str] = Field(default_factory=list)


class SaasSubscriptionDto(BaseModel):
    """Краткая информация о подписке завода."""

    status: str | None = None
    plan_code: str | None = None
    expires_at: str | None = None
    grace_period_ends_at: str | None = None


class TsdBootstrapDto(BaseModel):
    """Единый bootstrap-ответ для desktop/ТСД после авторизации."""

    authenticated: bool = True
    user: SaasUserDto | None = None
    supplier: SaasOrganizationDto | None = None
    plant: SaasOrganizationDto | None = None
    device: SaasDeviceDto | None = None
    context: SaasContextDto | None = None
    subscription: SaasSubscriptionDto | None = None
