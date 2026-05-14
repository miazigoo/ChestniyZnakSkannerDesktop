"""DTO принтеров Честного знака."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClientPrinterDto(BaseModel):
    """Принтер, доступный desktop-клиенту."""

    id: int
    name: str
    ip_address: str
    section: str = ""
    is_active: bool


class ClientPrinterSelectionDto(BaseModel):
    """Текущий выбор принтера для `device_id`."""

    ok: bool
    device_id: str
    selected_printer_id: int | None = None
    selected_printer: ClientPrinterDto | None = None
    printers: list[ClientPrinterDto] = Field(default_factory=list)
