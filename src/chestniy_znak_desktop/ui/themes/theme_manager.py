"""Менеджер применения Qt-тем."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.ui.themes.theme import LIGHT_THEME, THEMES, Theme


class ThemeManager(QObject):
    """Выбирает и применяет stylesheet текущей темы."""

    theme_changed = Signal(str)

    def __init__(self, initial_theme_name: str = "light") -> None:
        """Создает менеджер с начальной темой."""

        super().__init__()
        self._theme = self.get_theme(initial_theme_name)

    @property
    def current_theme(self) -> Theme:
        """Возвращает текущую тему."""

        return self._theme

    def get_theme(self, theme_name: str) -> Theme:
        """Возвращает тему по имени или светлую тему по умолчанию."""

        return THEMES.get(theme_name, LIGHT_THEME)

    def set_theme(self, theme_name: str, app: QApplication | None = None) -> Theme:
        """Меняет текущую тему и при необходимости применяет ее к приложению."""

        self._theme = self.get_theme(theme_name)
        if app is not None:
            self.apply(app)
        self.theme_changed.emit(self._theme.name)
        return self._theme

    def apply(self, app: QApplication) -> None:
        """Применяет stylesheet текущей темы к QApplication."""

        app.setStyleSheet(self._theme.stylesheet)
