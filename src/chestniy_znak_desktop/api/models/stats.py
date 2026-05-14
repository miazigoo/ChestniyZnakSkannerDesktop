"""DTO статистики Честного знака."""

from __future__ import annotations

from pydantic import BaseModel


class CatalogStatsDto(BaseModel):
    """Счетчики справочника кодов и сканов."""

    codes_count: int
    scans_count: int
