"""Тесты нормализации поиска коробки."""

from __future__ import annotations

from chestniy_znak_desktop.domain.box_lookup import build_box_lookup_candidates


def test_build_box_lookup_candidates_keeps_sscc_variants() -> None:
    """Проверяет варианты поиска из GS1-штрихкода SSCC."""

    assert build_box_lookup_candidates("(00)123456789012345678") == [
        "00123456789012345678",
        "123456789012345678",
    ]


def test_build_box_lookup_candidates_keeps_box_id() -> None:
    """Проверяет поиск по числовому ID коробки."""

    assert build_box_lookup_candidates(" 42 ") == ["42"]
