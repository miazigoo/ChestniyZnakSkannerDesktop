"""DTO принтеров и заданий печати SSCC."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from chestniy_znak_desktop.api.models.packing import BoxDto


class ClientPrinterDto(BaseModel):
    """Принтер поставщика, доступный рабочему месту."""

    id: int
    name: str
    ip_address: str
    port: int = 9100
    section: str = ""
    driver: str = "zpl"
    is_active: bool = True

    @property
    def label(self) -> str:
        """Возвращает короткую подпись для выбора в UI."""

        section = f" · {self.section}" if self.section else ""
        return f"{self.name} · {self.ip_address}:{self.port}{section}"


class ClientPrinterSelectionDto(BaseModel):
    """Текущий выбор принтера для рабочего места."""

    ok: bool = True
    device_id: str = ""
    selected_printer_id: int | None = None
    selected_printer: ClientPrinterDto | None = None
    printers: list[ClientPrinterDto] = Field(default_factory=list)


class PrintJobDto(BaseModel):
    """Задание печати, подготовленное backend."""

    format: str = ""
    driver: str = ""
    encoding: str = "utf-8"
    transport: str = ""
    payload: str = ""
    printer: ClientPrinterDto | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PackageLabelPrintResultDto(BaseModel):
    """Результат подготовки или выполнения печати SSCC-этикетки."""

    ok: bool | None = None
    reason_code: str = ""
    print_status: str = ""
    print_ok: bool = False
    print_error_code: str = ""
    print_error: str = ""
    printer: ClientPrinterDto | None = None
    print_job: PrintJobDto | None = None
    box: BoxDto | None = None
    package: dict[str, Any] | None = None
