"""Тесты защитных проверок входной строки сканера."""

from __future__ import annotations

from chestniy_znak_desktop.domain.scanner_input_guard import contains_cyrillic


def test_contains_cyrillic_detects_wrong_keyboard_layout_scan() -> None:
    """Проверяет обнаружение скана, пришедшего в русской раскладке."""

    assert contains_cyrillic("юхэЖ123фыва") is True


def test_contains_cyrillic_allows_regular_datamatrix() -> None:
    """Проверяет, что обычный DataMatrix не блокируется."""

    assert contains_cyrillic("010464615169726121SERIAL123") is False
