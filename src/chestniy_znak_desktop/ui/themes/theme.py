"""Модель и каталог тем интерфейса."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """Описывает цвета и stylesheet Qt-темы."""

    name: str
    title: str
    stylesheet: str


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Палитра для генерации Qt stylesheet."""

    window: str
    panel: str
    panel_alt: str
    text: str
    muted: str
    border: str
    input_bg: str
    button_bg: str
    button_text: str
    button_hover: str
    accent: str
    accent_soft: str
    danger: str
    selection_bg: str
    selection_text: str
    overlay_rgba: str


def _stylesheet(palette: ThemePalette) -> str:
    """Генерирует общий QSS для виджетов приложения."""

    return f"""
        * {{
            font-family: "Inter", "Segoe UI", "Arial";
            font-size: 14px;
            outline: 0;
        }}

        QMainWindow, QWidget {{
            background: {palette.window};
            color: {palette.text};
        }}

        QLabel {{
            background: transparent;
            color: {palette.text};
            padding: 1px;
        }}

        QLineEdit, QTextEdit, QComboBox, QSpinBox {{
            background: {palette.input_bg};
            color: {palette.text};
            border: 1px solid {palette.border};
            border-radius: 8px;
            padding: 8px 10px;
            selection-background-color: {palette.selection_bg};
            selection-color: {palette.selection_text};
        }}

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 1px solid {palette.accent};
        }}

        QComboBox::drop-down {{
            border: 0;
            width: 28px;
        }}

        QPushButton {{
            background: {palette.button_bg};
            color: {palette.button_text};
            border: 1px solid {palette.button_bg};
            border-radius: 8px;
            padding: 9px 14px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background: {palette.button_hover};
            border-color: {palette.button_hover};
        }}

        QPushButton:pressed {{
            background: {palette.accent};
            border-color: {palette.accent};
        }}

        QPushButton:disabled {{
            background: {palette.panel_alt};
            color: {palette.muted};
            border-color: {palette.border};
        }}

        QCheckBox {{
            spacing: 8px;
            background: transparent;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 5px;
            border: 1px solid {palette.border};
            background: {palette.input_bg};
        }}

        QCheckBox::indicator:checked {{
            background: {palette.accent};
            border-color: {palette.accent};
        }}

        QSlider::groove:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: {palette.panel_alt};
        }}

        QSlider::handle:horizontal {{
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
            background: {palette.accent};
        }}

        QTableWidget {{
            background: {palette.panel};
            alternate-background-color: {palette.panel_alt};
            color: {palette.text};
            border: 1px solid {palette.border};
            border-radius: 8px;
            gridline-color: {palette.border};
            selection-background-color: {palette.selection_bg};
            selection-color: {palette.selection_text};
        }}

        QHeaderView::section {{
            background: {palette.panel_alt};
            color: {palette.muted};
            border: 0;
            border-right: 1px solid {palette.border};
            border-bottom: 1px solid {palette.border};
            padding: 8px;
            font-weight: 700;
        }}

        QScrollBar:vertical {{
            background: {palette.panel};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {palette.border};
            border-radius: 6px;
            min-height: 32px;
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QStackedWidget {{
            background: {palette.window};
            border: 0;
        }}

        QMessageBox {{
            background: {palette.panel};
        }}

        #blockingOverlay {{
            background: {palette.overlay_rgba};
        }}
    """


LIGHT_THEME = Theme(
    name="light",
    title="Studio Light",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#f4f6f8",
            panel="#ffffff",
            panel_alt="#e9eef3",
            text="#17202a",
            muted="#526170",
            border="#c9d3dd",
            input_bg="#ffffff",
            button_bg="#1f6feb",
            button_text="#ffffff",
            button_hover="#1557bd",
            accent="#0f8b8d",
            accent_soft="#d8f0ef",
            danger="#c2410c",
            selection_bg="#bfe8e5",
            selection_text="#0f2528",
            overlay_rgba="rgba(244, 246, 248, 232)",
        )
    ),
)

GRAPHITE_THEME = Theme(
    name="graphite",
    title="Graphite Pro",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#17191d",
            panel="#20242a",
            panel_alt="#2b3038",
            text="#f2f5f7",
            muted="#aeb8c2",
            border="#3f4854",
            input_bg="#111418",
            button_bg="#e0b15e",
            button_text="#19160f",
            button_hover="#f0c878",
            accent="#56c7b8",
            accent_soft="#183d3a",
            danger="#ff7a70",
            selection_bg="#315a67",
            selection_text="#ffffff",
            overlay_rgba="rgba(23, 25, 29, 238)",
        )
    ),
)

PACIFIC_THEME = Theme(
    name="pacific",
    title="Pacific Control",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#ecf7f8",
            panel="#ffffff",
            panel_alt="#d7ecef",
            text="#112b32",
            muted="#47656d",
            border="#a9c9cf",
            input_bg="#fbffff",
            button_bg="#007c89",
            button_text="#ffffff",
            button_hover="#00636d",
            accent="#d97706",
            accent_soft="#fde9c2",
            danger="#b42318",
            selection_bg="#b8e3e7",
            selection_text="#06262b",
            overlay_rgba="rgba(236, 247, 248, 232)",
        )
    ),
)

FIELD_THEME = Theme(
    name="field",
    title="Field Ops",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#f3f5ef",
            panel="#ffffff",
            panel_alt="#e2ead8",
            text="#182316",
            muted="#55624f",
            border="#c3d0b8",
            input_bg="#fbfff7",
            button_bg="#28724f",
            button_text="#ffffff",
            button_hover="#1f5d40",
            accent="#b86b00",
            accent_soft="#f5dfba",
            danger="#b3261e",
            selection_bg="#cae7c9",
            selection_text="#102211",
            overlay_rgba="rgba(243, 245, 239, 232)",
        )
    ),
)

CONTRAST_THEME = Theme(
    name="contrast",
    title="High Contrast",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#0b0c0f",
            panel="#15171c",
            panel_alt="#23262d",
            text="#ffffff",
            muted="#c4c9d4",
            border="#555d6b",
            input_bg="#050608",
            button_bg="#ffd166",
            button_text="#111111",
            button_hover="#ffe08f",
            accent="#2dd4bf",
            accent_soft="#123f3b",
            danger="#ff5c5c",
            selection_bg="#ffe08f",
            selection_text="#111111",
            overlay_rgba="rgba(11, 12, 15, 240)",
        )
    ),
)

THEME_LIST = (
    LIGHT_THEME,
    GRAPHITE_THEME,
    PACIFIC_THEME,
    FIELD_THEME,
    CONTRAST_THEME,
)
THEMES = {theme.name: theme for theme in THEME_LIST}
THEME_ALIASES = {"dark": "graphite"}


def available_themes() -> tuple[Theme, ...]:
    """Возвращает доступные темы в порядке отображения."""

    return THEME_LIST


def theme_by_name(theme_name: str) -> Theme:
    """Возвращает тему по имени с учетом старых alias-значений."""

    normalized_name = THEME_ALIASES.get(theme_name, theme_name)
    return THEMES.get(normalized_name, LIGHT_THEME)
