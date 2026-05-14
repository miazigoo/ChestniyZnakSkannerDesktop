"""Тесты менеджера тем."""

from __future__ import annotations

from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager


def test_theme_manager_falls_back_to_light_theme() -> None:
    """Проверяет fallback на светлую тему для неизвестного имени."""

    manager = ThemeManager("unknown")
    assert manager.current_theme.name == "light"


def test_theme_manager_switches_theme_without_app() -> None:
    """Проверяет переключение темы без QApplication."""

    manager = ThemeManager("light")
    selected = manager.set_theme("dark")
    assert selected.name == "dark"
    assert manager.current_theme.title == "Темная"
