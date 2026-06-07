"""DTO рабочих заказов SaaS для упаковки."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OrderProductDto(BaseModel):
    """Номенклатура в строке заказа."""

    id: str
    sku: str
    name: str
    gtin: str | None = None
    unit: str = "pcs"


class OrderLineDto(BaseModel):
    """Строка заказа с привязкой к номенклатуре."""

    id: str
    order_id: str
    product_id: str
    quantity: int
    required_code_quantity: int
    package_capacity: int | None = None
    packaging_rule_id: str | None = None
    status: str
    product: OrderProductDto | None = None


class WorkOrderDto(BaseModel):
    """Рабочий заказ поставщика для маркировки."""

    id: str
    plant_id: str
    supplier_id: str
    order_number: str
    external_number: str | None = None
    status: str
    scan_required: bool = True
    planned_date: str | None = None
    lines: list[OrderLineDto] = Field(default_factory=list)


class WorkOrderPageDto(BaseModel):
    """Страница заказов из SaaS API."""

    data: list[WorkOrderDto] = Field(default_factory=list)
    meta: dict[str, int] = Field(default_factory=dict)


class LocalPoolCodeDto(BaseModel):
    """Код маркировки из локального пула заказа."""

    id: str
    code: str
    status: str
    order_line_id: str | None = None
    package_unit_id: str | None = None
    package_code: str | None = None
    package_status: str | None = None
    package_closed_at: str | None = None
    updated_at: str | None = None


class LocalCodePoolDto(BaseModel):
    """Страница локального пула кодов выбранного заказа."""

    order: WorkOrderDto
    codes: list[LocalPoolCodeDto] = Field(default_factory=list)
    total: int = 0
    count: int = 0
    limit: int = 5000
    offset: int = 0
    next_offset: int | None = None
    has_more: bool = False


class LocalCodePoolPageDto(BaseModel):
    """Ответ SaaS API со страницей локального пула заказа."""

    data: LocalCodePoolDto
