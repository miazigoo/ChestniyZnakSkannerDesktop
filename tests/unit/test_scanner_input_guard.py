"""Тесты защитных проверок входной строки сканера."""

from __future__ import annotations

from chestniy_znak_desktop.domain.scanner_input_guard import (
    contains_cyrillic,
    repair_cyrillic_keyboard_layout,
)


def test_contains_cyrillic_detects_wrong_keyboard_layout_scan() -> None:
    """Проверяет обнаружение скана, пришедшего в русской раскладке."""

    assert contains_cyrillic("юхэЖ123фыва") is True


def test_contains_cyrillic_allows_regular_datamatrix() -> None:
    """Проверяет, что обычный DataMatrix не блокируется."""

    assert contains_cyrillic("010464615169726121SERIAL123") is False


def test_repair_cyrillic_keyboard_layout_restores_hid_scan_tail() -> None:
    """Проверяет восстановление HID-скана, пришедшего в русской раскладке."""

    repaired, changed = repair_cyrillic_keyboard_layout("010460123456789021ЧЬ03")

    assert changed is True
    assert repaired == "010460123456789021XM03"
    assert contains_cyrillic(repaired) is False


def test_repair_cyrillic_keyboard_layout_keeps_regular_datamatrix() -> None:
    """Проверяет, что нормальный скан не меняется."""

    repaired, changed = repair_cyrillic_keyboard_layout("010460123456789021XM03")

    assert changed is False
    assert repaired == "010460123456789021XM03"
