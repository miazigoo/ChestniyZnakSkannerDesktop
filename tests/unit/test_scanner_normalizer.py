"""Тесты нормализации и разбора DataMatrix."""

from __future__ import annotations

import pytest

from chestniy_znak_desktop.domain.scanner_normalizer import (
    GS,
    MarkingCodeParseError,
    normalize_scanner_input,
    parse_marking_code,
)


def test_parse_code_with_native_gs() -> None:
    """Проверяет разбор кода с настоящим ASCII GS."""

    parsed = parse_marking_code(f"010460123456789021SERIAL0001{GS}910001{GS}92TAIL")
    assert parsed.gtin == "04601234567890"
    assert parsed.serial == "SERIAL0001"
    assert parsed.ai_parts == {"91": "0001", "92": "TAIL"}
    assert parsed.scanner_gs_native is True


def test_parse_bracketed_ai_input() -> None:
    """Проверяет поддержку человекочитаемых AI в скобках."""

    parsed = parse_marking_code("(01)04601234567890(21)SERIAL0001(91)0001(92)TAIL")
    assert parsed.visible_code == "010460123456789021SERIAL0001<GS>910001<GS>92TAIL"


def test_parse_restores_missing_gs_after_long_serial() -> None:
    """Проверяет эвристику восстановления GS после длинного serial."""

    parsed = parse_marking_code("010460123456789021SERIAL00000000000019920001")
    assert parsed.gs_restored is True
    assert parsed.ai_parts == {"92": "0001"}


def test_normalize_accepts_visible_gs_aliases() -> None:
    """Проверяет замену видимых алиасов GS на управляющий символ."""

    normalized, native_gs, _ = normalize_scanner_input("010460123456789021S<GS>92TAIL\r\n")
    assert normalized == f"010460123456789021S{GS}92TAIL"
    assert native_gs is True


def test_parse_rejects_bad_prefix() -> None:
    """Проверяет ошибку для кода без AI 01."""

    with pytest.raises(MarkingCodeParseError):
        parse_marking_code("990460123456789021SERIAL")
