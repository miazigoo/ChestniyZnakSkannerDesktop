"""Нагрузочные smoke-тесты таблиц упаковки Desktop UI."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from chestniy_znak_desktop.controllers.auto_packing_controller import (  # noqa: E402
    AutoPackingUiState,
)
from chestniy_znak_desktop.controllers.packing_controller import (  # noqa: E402
    PackingBoxUi,
    PackingItemUi,
    PackingUiState,
)
from chestniy_znak_desktop.ui.screens.auto_packing_screen import AutoPackingScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen  # noqa: E402


def qapp() -> QApplication:
    """Возвращает QApplication для offscreen UI-теста."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return cast(QApplication, app)


def _items(count: int) -> list[PackingItemUi]:
    """Создает список UI-кодов для нагрузочной таблицы."""

    return [
        PackingItemUi(
            id=index,
            code_id=index,
            gtin="04601234567890",
            serial=f"SERIAL{index:06d}",
            visible_code=f"010460123456789021LOAD{index:012d}",
        )
        for index in range(1, count + 1)
    ]


def test_packing_screen_handles_1000_box_items_without_repaint_churn() -> None:
    """Проверяет таблицу обычной упаковки на 1000 строк и повторное состояние."""

    qapp()
    screen = PackingScreen()
    state = PackingUiState(
        current_box=PackingBoxUi(
            box_id=1,
            order_name="LOAD-ORDER",
            sscc="SSCC-LOAD-0001",
            filled=1000,
            capacity=1000,
            count_in_packing=True,
            is_closed=False,
            items=_items(1000),
        )
    )

    screen.apply_state(state)
    first_signature = screen._items_table_signature  # noqa: SLF001
    screen.apply_state(state)

    assert screen._items_table.rowCount() == 1000  # noqa: SLF001
    assert screen._items_table_signature == first_signature  # noqa: SLF001


def test_auto_packing_screen_handles_2000_box_items_after_refresh() -> None:
    """Проверяет таблицу текущей коробки автосканера на 2000 строк."""

    qapp()
    screen = AutoPackingScreen()
    state = AutoPackingUiState(
        current_box=PackingBoxUi(
            box_id=2,
            order_name="AUTO-LOAD-ORDER",
            sscc="SSCC-AUTO-0001",
            filled=2000,
            capacity=2000,
            count_in_packing=True,
            is_closed=False,
            items=_items(2000),
        )
    )

    screen.apply_state(state)
    first_signature = screen._box_items_table_signature  # noqa: SLF001
    screen.apply_state(state)

    assert screen._box_items_table.rowCount() == 2000  # noqa: SLF001
    assert screen._box_items_table_signature == first_signature  # noqa: SLF001
