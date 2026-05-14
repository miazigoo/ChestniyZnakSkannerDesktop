"""Модель темы интерфейса."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """Описывает цвета и stylesheet Qt-темы."""

    name: str
    title: str
    stylesheet: str


LIGHT_THEME = Theme(
    name="light",
    title="Светлая",
    stylesheet="""
        QWidget { font-size: 14px; }
        QMainWindow { background: #f6f7f9; }
        QPushButton { padding: 8px 12px; }
        #blockingOverlay { background: rgba(246, 247, 249, 230); }
    """,
)

DARK_THEME = Theme(
    name="dark",
    title="Темная",
    stylesheet="""
        QWidget { background: #20242a; color: #f1f3f5; font-size: 14px; }
        QPushButton { background: #3a7afe; color: white; padding: 8px 12px; }
        QLineEdit, QTableWidget { background: #2b3038; color: #f1f3f5; }
        #blockingOverlay { background: rgba(32, 36, 42, 235); }
    """,
)

THEMES = {theme.name: theme for theme in (LIGHT_THEME, DARK_THEME)}
