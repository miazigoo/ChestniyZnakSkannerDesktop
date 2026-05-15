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


def test_build_box_lookup_candidates_accepts_gs1_symbology_prefix() -> None:
    """Проверяет поиск SSCC с HID/GS1-префиксом символогии."""

    assert build_box_lookup_candidates("]C1(00)123456789012345678") == [
        "00123456789012345678",
        "123456789012345678",
    ]


def test_build_box_lookup_candidates_removes_visible_gs_alias() -> None:
    """Проверяет очистку видимого GS-разделителя в скане коробки."""

    assert build_box_lookup_candidates("]C1(00)123456789012345678<GS>") == [
        "00123456789012345678",
        "123456789012345678",
    ]
