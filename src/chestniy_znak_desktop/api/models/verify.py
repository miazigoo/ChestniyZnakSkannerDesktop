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


class DefectRemovedBoxDto(BaseModel):
    """Коробка, из которой код был удален при отметке брака."""

    box_id: int
    sscc: str | None = None
    filled: int = 0


class DefectResponseDto(BaseModel):
    """Результат отметки кода как брака."""

    ok: bool
    reason_code: str
    error: str | None = None
    verify: VerifyResponseDto | None = None
    removed_from_box: DefectRemovedBoxDto | None = None
