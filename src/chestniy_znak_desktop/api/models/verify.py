"""DTO проверки DataMatrix-кодов."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RemoteCodeDto(BaseModel):
    """Краткая информация о найденном коде маркировки."""

    id: int
    gtin: str
    serial: str
    ai_parts: dict[str, str] = Field(default_factory=dict)
    visible_code: str
    status_1c: str = ""
    app_status: str = ""
    order_dnp_name: str = ""
    order_name: str = ""
    device_name: str = ""


class VerifyResponseDto(BaseModel):
    """Результат проверки DataMatrix-кода."""

    status: str
    message: str
    scan_id: int | None = None
    code: RemoteCodeDto | None = None
    warnings: list[str] = Field(default_factory=list)


class VerifyExistsResponseDto(BaseModel):
    """Упрощенный результат проверки существования кода в базе."""

    ok: bool
    exists: bool
    status: str
    message: str
    order_name: str | None = None
    device_name: str | None = None
    scan_id: int | None = None
    code: RemoteCodeDto | None = None
    warnings: list[str] = Field(default_factory=list)
