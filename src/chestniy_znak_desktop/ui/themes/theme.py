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

        QComboBox QAbstractItemView {{
            background: {palette.panel};
            color: {palette.text};
            border: 1px solid {palette.border};
            selection-background-color: {palette.selection_bg};
            selection-color: {palette.selection_text};
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

        QToolTip {{
            background: {palette.panel};
            color: {palette.text};
            border: 1px solid {palette.border};
            border-radius: 6px;
            padding: 6px 8px;
        }}

        QMenu {{
            background: {palette.panel};
            color: {palette.text};
            border: 1px solid {palette.border};
            padding: 6px;
        }}

        QMenu::item {{
            padding: 7px 16px;
            border-radius: 6px;
        }}

        QMenu::item:selected {{
            background: {palette.selection_bg};
            color: {palette.selection_text};
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

        QProgressBar {{
            min-height: 10px;
            border: 0;
            border-radius: 5px;
            background: {palette.panel_alt};
            color: {palette.text};
        }}

        QProgressBar::chunk {{
            border-radius: 5px;
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

        QScrollBar::handle:vertical:hover {{
            background: {palette.accent};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background: {palette.panel};
            height: 12px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background: {palette.border};
            border-radius: 6px;
            min-width: 32px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {palette.accent};
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        QStackedWidget {{
            background: {palette.window};
            border: 0;
        }}

        QSplitter::handle {{
            background: {palette.border};
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

HARBOR_THEME = Theme(
    name="harbor",
    title="Harbor Steel",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#101820",
            panel="#172331",
            panel_alt="#223244",
            text="#f4f8fb",
            muted="#a9bac8",
            border="#3b5165",
            input_bg="#0b1219",
            button_bg="#5bd1c8",
            button_text="#071617",
            button_hover="#78e5dc",
            accent="#f0b24f",
            accent_soft="#42321c",
            danger="#ff7166",
            selection_bg="#2f6671",
            selection_text="#ffffff",
            overlay_rgba="rgba(16, 24, 32, 238)",
        )
    ),
)

EMBER_THEME = Theme(
    name="ember",
    title="Ember Signal",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#191817",
            panel="#232120",
            panel_alt="#312d29",
            text="#fbf6ef",
            muted="#c7bdb0",
            border="#4b4038",
            input_bg="#11100f",
            button_bg="#e06f3f",
            button_text="#180b06",
            button_hover="#f18653",
            accent="#64d2c2",
            accent_soft="#173f3a",
            danger="#ff6b6b",
            selection_bg="#614d33",
            selection_text="#fff8ec",
            overlay_rgba="rgba(25, 24, 23, 238)",
        )
    ),
)

ALPINE_THEME = Theme(
    name="alpine",
    title="Alpine Frost",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#eef4f2",
            panel="#ffffff",
            panel_alt="#dfe9e5",
            text="#14211d",
            muted="#52645e",
            border="#bfcec8",
            input_bg="#fbfffd",
            button_bg="#1d7f6e",
            button_text="#ffffff",
            button_hover="#176859",
            accent="#356bb3",
            accent_soft="#dce8f8",
            danger="#b42318",
            selection_bg="#c7e8de",
            selection_text="#10241f",
            overlay_rgba="rgba(238, 244, 242, 232)",
        )
    ),
)

MIDNIGHT_THEME = Theme(
    name="midnight",
    title="Midnight Console",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#0d1117",
            panel="#141a22",
            panel_alt="#202938",
            text="#f1f5f9",
            muted="#a9b6c7",
            border="#344256",
            input_bg="#070b10",
            button_bg="#7dd3fc",
            button_text="#07131c",
            button_hover="#a7e3ff",
            accent="#facc15",
            accent_soft="#3e3410",
            danger="#fb7185",
            selection_bg="#264766",
            selection_text="#ffffff",
            overlay_rgba="rgba(13, 17, 23, 240)",
        )
    ),
)

RUBY_THEME = Theme(
    name="ruby",
    title="Ruby Trace",
    stylesheet=_stylesheet(
        ThemePalette(
            window="#f7f3f5",
            panel="#ffffff",
            panel_alt="#ece3e7",
            text="#25171d",
            muted="#6c5962",
            border="#d2c0c8",
            input_bg="#fffafd",
            button_bg="#a53860",
            button_text="#ffffff",
            button_hover="#842d4d",
            accent="#0f8b8d",
            accent_soft="#d8f0ef",
            danger="#b42318",
            selection_bg="#efd3dd",
            selection_text="#27131c",
            overlay_rgba="rgba(247, 243, 245, 232)",
        )
    ),
)

THEME_LIST = (
    LIGHT_THEME,
    GRAPHITE_THEME,
    PACIFIC_THEME,
    FIELD_THEME,
    CONTRAST_THEME,
    HARBOR_THEME,
    EMBER_THEME,
    ALPINE_THEME,
    MIDNIGHT_THEME,
    RUBY_THEME,
)
THEMES = {theme.name: theme for theme in THEME_LIST}
THEME_ALIASES = {
    "dark": "graphite",
    "default": "light",
}


def available_themes() -> tuple[Theme, ...]:
    """Возвращает доступные темы в порядке отображения."""

    return THEME_LIST


def theme_by_name(theme_name: str) -> Theme:
    """Возвращает тему по имени с учетом старых alias-значений."""

    normalized_name = THEME_ALIASES.get(theme_name, theme_name)
    return THEMES.get(normalized_name, LIGHT_THEME)
