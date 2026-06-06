"""Тесты извлечения токена авторизации."""

from __future__ import annotations

from chestniy_znak_desktop.domain.auth_token_extractor import extract_auth_token


def test_extract_auth_token_from_plain_text() -> None:
    """Проверяет plain-text токен."""

    assert extract_auth_token(" LKIC-HDDS-NK4K ") == "LKIC-HDDS-NK4K"


def test_extract_auth_token_formats_compact_plain_text() -> None:
    """Проверяет токен без дефисов."""

    assert extract_auth_token("lkichddsnk4k") == "LKIC-HDDS-NK4K"


def test_extract_auth_token_from_json() -> None:
    """Проверяет токен в JSON-представлении."""

    assert extract_auth_token('{"token":"LKIC-HDDS-NK4K"}') == "LKIC-HDDS-NK4K"


def test_extract_auth_token_from_activation_code_json() -> None:
    """Проверяет QR payload из кабинета поставщика."""

    assert extract_auth_token('{"activation_code":"LKICHDDSNK4K"}') == "LKIC-HDDS-NK4K"


def test_extract_auth_token_from_url_query() -> None:
    """Проверяет токен в query-параметре URL."""

    assert extract_auth_token("https://host/login?token=LKIC-HDDS-NK4K") == "LKIC-HDDS-NK4K"


def test_extract_auth_token_returns_none_for_blank_value() -> None:
    """Проверяет пустое значение сканера."""

    assert extract_auth_token("  ") is None


def test_extract_auth_token_returns_none_for_short_hid_noise() -> None:
    """Проверяет, что одиночные клавиши HID не уходят как app-token."""

    assert extract_auth_token("L") is None
    assert extract_auth_token("LKIC") is None
