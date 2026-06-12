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


def test_parse_short_44_code_without_gs() -> None:
    """Проверяет короткий код ЧЗ без явного GS."""

    parsed = parse_marking_code("010460700123456721SERIAL1234567890123493ABCD")
    assert parsed.gtin == "04607001234567"
    assert parsed.serial == "SERIAL12345678901234"
    assert parsed.ai_parts == {"93": "ABCD"}
    assert parsed.visible_code == "010460700123456721SERIAL12345678901234<GS>93ABCD"
    assert parsed.gs_restored is True


def test_parse_long_crypto_tail_without_gs() -> None:
    """Проверяет длинный код ЧЗ без GS между serial, 91 и 92."""

    parsed = parse_marking_code("010460700123456721SERIAL1234567890123491KEY192" + "X" * 44)
    assert parsed.serial == "SERIAL12345678901234"
    assert parsed.ai_parts == {"91": "KEY1", "92": "X" * 44}
    assert parsed.visible_code == (
        "010460700123456721SERIAL12345678901234<GS>91KEY1<GS>92" + "X" * 44
    )
    assert parsed.gs_restored is True


def test_parse_short_serial_crypto_tail_without_gs() -> None:
    """Проверяет HID-код с коротким serial и потерянными GS перед 91/92."""

    parsed = parse_marking_code("010460123456789021A10000005591W81K925Y7N")

    assert parsed.gtin == "04601234567890"
    assert parsed.serial == "A100000055"
    assert parsed.ai_parts == {"91": "W81K", "92": "5Y7N"}
    assert parsed.visible_code == "010460123456789021A100000055<GS>91W81K<GS>925Y7N"
    assert parsed.gs_restored is True


def test_parse_hid_decimal_group_separator_before_crypto_ai() -> None:
    """Проверяет сканер, который отправляет GS как текст `0029` перед AI."""

    parsed = parse_marking_code(
        "010460123456789021A100000046002991FZKG0029926X2F0VZD16AR61Y2"
        "SIICCBRHKL3OI8RWK6A773NJG4VKYIZN5706GS7Y"
    )

    assert parsed.gtin == "04601234567890"
    assert parsed.serial == "A100000046"
    assert parsed.identity_key == "04601234567890|A100000046"
    assert parsed.ai_parts == {
        "91": "FZKG",
        "92": "6X2F0VZD16AR61Y2SIICCBRHKL3OI8RWK6A773NJG4VKYIZN5706GS7Y",
    }
    assert parsed.visible_code.startswith("010460123456789021A100000046<GS>91FZKG<GS>92")
    assert parsed.scanner_gs_native is True


def test_parse_longer_crypto_tail_without_gs() -> None:
    """Проверяет удлиненный криптохвост без привязки к общей длине кода."""

    parsed = parse_marking_code("010460700123456721SERIAL1234567890123491KEY192" + "Y" * 49)
    assert parsed.serial == "SERIAL12345678901234"
    assert parsed.ai_parts == {"91": "KEY1", "92": "Y" * 49}
    assert "<GS>91KEY1<GS>92" in parsed.visible_code
    assert parsed.gs_restored is True


def test_normalize_accepts_visible_gs_aliases() -> None:
    """Проверяет замену видимых алиасов GS на управляющий символ."""

    normalized, native_gs, _ = normalize_scanner_input(
        f" {GS}010460123456789021S{{GS}}91ABCD\\03592TAIL\r\n"
    )
    assert normalized == f"010460123456789021S{GS}91ABCD{GS}92TAIL"
    assert native_gs is True


def test_parse_rejects_bad_prefix() -> None:
    """Проверяет ошибку для кода без AI 01."""

    with pytest.raises(MarkingCodeParseError):
        parse_marking_code("990460123456789021SERIAL")
