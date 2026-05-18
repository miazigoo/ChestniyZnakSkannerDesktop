"""Проверки входной строки сканера перед отправкой в рабочие сценарии."""

from __future__ import annotations


def contains_cyrillic(text: str) -> bool:
    """Проверяет, содержит ли скан символы кириллицы из-за неверной раскладки."""

    return any(
        "\u0400" <= char <= "\u04ff"
        or "\u0500" <= char <= "\u052f"
        or "\u2de0" <= char <= "\u2dff"
        or "\ua640" <= char <= "\ua69f"
        for char in text
    )
