"""Страница быстрого выбора темы интерфейса."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    create_back_button,
    create_card,
    create_page_header,
)
from chestniy_znak_desktop.ui.themes.theme import Theme, available_themes, theme_by_name
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName

THEME_PREVIEW_COLORS: dict[str, tuple[str, str, str]] = {
    "light": ("#f4f6f8", "#ffffff", "#1f6feb"),
    "graphite": ("#17191d", "#20242a", "#e0b15e"),
    "pacific": ("#ecf7f8", "#ffffff", "#007c89"),
    "field": ("#f3f5ef", "#ffffff", "#28724f"),
    "contrast": ("#0b0c0f", "#15171c", "#ffd166"),
    "harbor": ("#101820", "#172331", "#5bd1c8"),
    "ember": ("#191817", "#232120", "#e06f3f"),
    "alpine": ("#eef4f2", "#ffffff", "#1d7f6e"),
    "midnight": ("#0d1117", "#141a22", "#7dd3fc"),
    "ruby": ("#f7f3f5", "#ffffff", "#a53860"),
}


class ThemeOptionCard(QFrame):
    """Кликабельная карточка темы с цветовым превью."""

    clicked = Signal(str)

    def __init__(self, theme: Theme) -> None:
        """Создает карточку для одной темы."""

        super().__init__()
        self._theme = theme
        self.setObjectName("settingsThemeItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)
        self.setMinimumHeight(104)

        title = QLabel(theme.title)
        title.setObjectName("settingsThemeTitle")
        meta = QLabel(theme.name)
        meta.setObjectName("settingsThemeMeta")
        self._state_label = QLabel(tr("settings.theme.available"))
        self._state_label.setObjectName("settingsThemeCheck")

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        text.addWidget(title)
        text.addWidget(meta)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addLayout(text, 1)
        head.addWidget(self._state_label, alignment=Qt.AlignmentFlag.AlignTop)

        swatches = QHBoxLayout()
        swatches.setContentsMargins(0, 0, 0, 0)
        swatches.setSpacing(8)
        for color in THEME_PREVIEW_COLORS.get(theme.name, ("#ffffff", "#d8dee8", "#56c7b8")):
            swatches.addWidget(self._create_swatch(color))
        swatches.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.addLayout(head)
        layout.addLayout(swatches)

    @property
    def theme_name(self) -> str:
        """Возвращает техническое имя темы."""

        return self._theme.name

    def set_selected(self, selected: bool) -> None:
        """Обновляет визуальное состояние выбранной темы."""

        self.setProperty("selected", selected)
        self._state_label.setText(
            tr("settings.theme.active") if selected else tr("settings.theme.available")
        )
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Публикует выбор темы по клику на карточку."""

        self.clicked.emit(self._theme.name)
        super().mousePressEvent(event)

    @staticmethod
    def _create_swatch(color: str) -> QFrame:
        """Создает цветовой маркер превью темы."""

        swatch = QFrame()
        swatch.setObjectName("settingsThemeSwatch")
        swatch.setFixedSize(46, 14)
        swatch.setStyleSheet(f"background: {color}; border-radius: 7px;")
        return swatch


class ThemeSettingsPage(QWidget):
    """Выбирает тему интерфейса кликом по карточке."""

    back_requested = Signal()
    theme_selected = Signal(str)

    def __init__(self) -> None:
        """Создает страницу карточек доступных тем."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._theme_items = [ThemeOptionCard(theme) for theme in available_themes()]
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._columns = 0
        self._back_button = create_back_button()
        self._back_button.clicked.connect(self.back_requested.emit)
        for item in self._theme_items:
            item.clicked.connect(self._select_theme)

        header = create_page_header(
            title=tr("settings.theme.title"),
            subtitle=tr("settings.theme.subtitle"),
            icon_name=VectorIconName.SETTINGS,
            icon_color="#8fb8ff",
        )
        card, card_layout = create_card(
            title=tr("settings.theme.cardTitle"),
            subtitle=tr("settings.theme.cardSubtitle"),
            icon_name=VectorIconName.SHIELD,
            icon_color="#66d2c7",
        )
        card_layout.addLayout(self._grid)
        actions = QHBoxLayout()
        actions.addWidget(self._back_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
        layout.addStretch(1)
        self._reflow_theme_items(3)

    def apply_state(self, state: SettingsUiState) -> None:
        """Отмечает активную тему из состояния настроек."""

        self._mark_selected(theme_by_name(state.theme_name).name)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Перестраивает сетку карточек под доступную ширину."""

        super().resizeEvent(event)
        width = event.size().width()
        if width < 560:
            columns = 1
        elif width < 920:
            columns = 2
        else:
            columns = 3
        self._reflow_theme_items(columns)

    def _select_theme(self, theme_name: str) -> None:
        """Выбирает тему локально и отправляет запрос применения."""

        normalized_name = theme_by_name(theme_name).name
        self._mark_selected(normalized_name)
        self.theme_selected.emit(normalized_name)

    def _mark_selected(self, theme_name: str) -> None:
        """Подсвечивает выбранную карточку темы."""

        for item in self._theme_items:
            item.set_selected(item.theme_name == theme_name)

    def _reflow_theme_items(self, columns: int) -> None:
        """Размещает карточки в сетке с нужным количеством колонок."""

        if columns == self._columns:
            return
        self._columns = columns
        for index, item in enumerate(self._theme_items):
            self._grid.removeWidget(item)
            row = index // columns
            column = index % columns
            self._grid.addWidget(item, row, column)
        for column in range(columns):
            self._grid.setColumnStretch(column, 1)
