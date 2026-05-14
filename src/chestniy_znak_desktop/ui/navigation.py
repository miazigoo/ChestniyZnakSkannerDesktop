"""Навигационные идентификаторы экранов."""

from __future__ import annotations

from enum import Enum


class ScreenName(str, Enum):
    """Имена экранов desktop-клиента."""

    LOGIN = "login"
    PACKING = "packing"
    MENU = "menu"
    BOXES = "boxes"
    BOX_DETAIL = "box_detail"
    DEFECT = "defect"
    SETTINGS = "settings"
