"""Тесты извлечения токена авторизации."""

from __future__ import annotations

from chestniy_znak_desktop.domain.auth_token_extractor import extract_auth_token


def test_extract_auth_token_from_plain_text() -> None:
    """Проверяет plain-text токен."""

    assert extract_auth_token(" scanner-token ") == "scanner-token"


def test_extract_auth_token_from_json() -> None:
    """Проверяет токен в JSON-представлении."""

    assert extract_auth_token('{"token":"json-token"}') == "json-token"


def test_extract_auth_token_from_url_query() -> None:
    """Проверяет токен в query-параметре URL."""

    assert extract_auth_token("https://host/login?token=url-token") == "url-token"


def test_extract_auth_token_returns_none_for_blank_value() -> None:
    """Проверяет пустое значение сканера."""

    assert extract_auth_token("  ") is None
