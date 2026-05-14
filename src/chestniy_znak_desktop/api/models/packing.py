"""DTO упаковки и коробок Честного знака."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoxDto(BaseModel):
    """Краткая карточка коробки ЧЗ."""

    box_id: int
    order_id: int | None = None
    order_name: str | None = None
    sscc: str | None = None
    capacity: int
    filled: int
    count_in_packing: bool = True
    allow_duplicate_scans: bool
    is_closed: bool
    is_edit_mode: bool
    active_user_name: str = ""
    created_by_name: str = ""
    print_ok: bool = False
    print_error: str = ""


class BoxItemDto(BaseModel):
    """Один код маркировки внутри коробки."""

    id: int
    code_id: int
    scan_id: int | None = None
    gtin: str
    serial: str
    visible_code: str


class BoxDetailDto(BoxDto):
    """Полная карточка коробки со списком кодов."""

    items: list[BoxItemDto] = Field(default_factory=list)


class BoxListDto(BaseModel):
    """Страница списка коробок."""

    items: list[BoxDto] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False


class OpenBoxResultDto(BaseModel):
    """Результат открытия коробки."""

    ok: bool
    created: bool
    has_active_boxes: bool = False
    boxes: list[BoxDto] = Field(default_factory=list)
    box: BoxDto


class ScanToBoxResultDto(BaseModel):
    """Результат добавления кода в коробку."""

    ok: bool
    reason_code: str
    error: str | None = None
    duplicate: bool | None = None
    box: BoxDto
    box_full_signal: bool | None = None


class CloseBoxResultDto(BaseModel):
    """Результат закрытия коробки и печати этикетки."""

    ok: bool
    reason_code: str
    error: str | None = None
    box: BoxDto
    print_ok: bool | None = None
    print_error: str | None = None


class BoxActionResultDto(BaseModel):
    """Общий результат операции над коробкой."""

    ok: bool
    reason_code: str
    error: str | None = None
    box: BoxDetailDto | BoxDto
    boxes: list[BoxDto] = Field(default_factory=list)
    removed: int | None = None
