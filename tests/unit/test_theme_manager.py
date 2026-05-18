"""Тесты менеджера тем."""

from __future__ import annotations

from chestniy_znak_desktop.ui.themes.theme import THEMES, available_themes, theme_by_name
from chestniy_znak_desktop.ui.themes.theme_manager import ThemeManager


def test_theme_manager_falls_back_to_light_theme() -> None:
    """Проверяет fallback на светлую тему для неизвестного имени."""

    manager = ThemeManager("unknown")
    assert manager.current_theme.name == "light"


def test_theme_manager_switches_theme_without_app() -> None:
    """Проверяет переключение темы без QApplication."""

    manager = ThemeManager("light")
    selected = manager.set_theme("graphite")
    assert selected.name == "graphite"
    assert manager.current_theme.title == "Graphite Pro"


def test_available_themes_are_registered() -> None:
    """Проверяет регистрацию всех тем."""

    names = [theme.name for theme in available_themes()]

    assert names == [
        "light",
        "graphite",
        "pacific",
        "field",
        "contrast",
        "harbor",
        "ember",
        "alpine",
        "midnight",
        "ruby",
    ]
    assert set(names) == set(THEMES)
    assert all("QPushButton" in theme.stylesheet for theme in available_themes())
    assert all("QProgressBar" in theme.stylesheet for theme in available_themes())
    assert all("QTabWidget" in theme.stylesheet for theme in available_themes())
    assert all("QTabBar::tab:selected" in theme.stylesheet for theme in available_themes())
    assert all("#packingHero" in theme.stylesheet for theme in available_themes())
    assert all("#settingsComboPopup" in theme.stylesheet for theme in available_themes())


def test_dark_alias_maps_to_graphite() -> None:
    """Проверяет совместимость со старым значением темной темы."""

    assert theme_by_name("dark").name == "graphite"


def test_theme_titles_are_unique() -> None:
    """Проверяет, что в списке нет дублей названий тем."""

    titles = [theme.title for theme in available_themes()]

    assert len(titles) == 10
    assert len(titles) == len(set(titles))
