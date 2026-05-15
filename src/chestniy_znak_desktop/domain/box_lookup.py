"""Нормализация скана коробки для поиска."""

from __future__ import annotations


def build_box_lookup_candidates(raw_code: str) -> list[str]:
    """Возвращает варианты поиска коробки по SSCC или ID."""

    compact = (
        raw_code.strip()
        .replace("<GS>", "")
        .replace("[GS]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("\u001d", "")
        .replace(" ", "")
    )
    if compact.startswith("]C1"):
        compact = compact[3:]
    values: dict[str, None] = {}
    if compact:
        values[compact] = None

    digits_only = "".join(char for char in compact if char.isdigit())
    if digits_only:
        values[digits_only] = None
        if len(digits_only) == 20 and digits_only.startswith("00"):
            values[digits_only[2:]] = None

    return list(values.keys())
