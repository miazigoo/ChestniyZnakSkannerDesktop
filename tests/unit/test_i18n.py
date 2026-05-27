"""Тесты полноты desktop-локализации."""

from __future__ import annotations

from chestniy_znak_desktop.i18n import (
    SUPPORTED_LANGUAGES,
    _MESSAGES,
    accept_language,
    language_headers,
    normalize_language,
)


def test_i18n_dictionaries_have_same_keys() -> None:
    """Проверяет, что RU/EN/ZH словари не расходятся по ключам."""

    base_keys = set(_MESSAGES["ru"])
    for language in SUPPORTED_LANGUAGES:
        keys = set(_MESSAGES[language])
        assert keys == base_keys, (
            language,
            sorted(base_keys - keys),
            sorted(keys - base_keys),
        )


def test_i18n_language_normalization_and_headers() -> None:
    """Проверяет нормализацию языка и API-заголовки локализации."""

    assert normalize_language("ru-RU") == "ru"
    assert normalize_language("en_US") == "en"
    assert normalize_language("zh-CN") == "zh"
    assert normalize_language("de-DE") == "ru"
    assert accept_language("zh") == "zh-CN,zh;q=0.9,en;q=0.6"
    assert language_headers("en") == {
        "X-App-Language": "en",
        "X-Language": "en",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.6",
    }
