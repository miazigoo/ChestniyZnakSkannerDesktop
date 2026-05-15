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


def _custom_object_styles(palette: ThemePalette) -> str:
    """Генерирует QSS для objectName-виджетов рабочих экранов."""

    hero_background = (
        "qlineargradient("
        "x1: 0, y1: 0, x2: 1, y2: 1, "
        f"stop: 0 {palette.panel_alt}, "
        f"stop: 0.58 {palette.panel}, "
        f"stop: 1 {palette.accent_soft}"
        ")"
    )
    accent_background = (
        "qlineargradient("
        "x1: 0, y1: 0, x2: 1, y2: 0, "
        f"stop: 0 {palette.accent}, "
        f"stop: 1 {palette.button_bg}"
        ")"
    )
    return f"""
        #mainScreen,
        #packingScreen,
        #boxesScreen,
        #boxLookupScreen,
        #verifyScreen,
        #defectScreen,
        #diagnosticsScreen,
        #settingsScreen,
        #settingsPage,
        #settingsStack,
        #packingScreenScroll,
        #boxesScreenScroll,
        #boxLookupScreenScroll,
        #verifyScreenScroll,
        #defectScreenScroll,
        #settingsScreenScroll,
        #diagnosticsScreenScroll {{
            background: transparent;
            border: 0;
        }}

        #mainWorkspace,
        #userSessionPanel,
        #loginPanel,
        #packingCard,
        #packingScanCard,
        #packingActionsPanel,
        #packingTablePanel,
        #boxesToolbar,
        #boxesListPanel,
        #boxesDetailPanel,
        #boxesActionsPanel,
        #boxesItemsPanel,
        #lookupCard,
        #lookupResultCard,
        #lookupLogPanel,
        #verifyCard,
        #verifyResultCard,
        #verifyMetaPanel,
        #verifyLogPanel,
        #defectCard,
        #defectResultCard,
        #defectMetaPanel,
        #defectLogPanel,
        #diagnosticsPanel,
        #diagnosticsLogsPanel,
        #settingsCard {{
            background: {palette.panel};
            border: 1px solid {palette.border};
            border-radius: 18px;
        }}

        #mainSidebar {{
            background: {hero_background};
            border: 1px solid {palette.border};
            border-radius: 18px;
        }}

        #mainSidebarScroll,
        #mainSidebarContent {{
            background: transparent;
            border: 0;
        }}

        #packingHero,
        #boxesHero,
        #lookupHero,
        #verifyHero,
        #defectHero,
        #diagnosticsHero,
        #settingsPageHeader {{
            background: {hero_background};
            border: 1px solid {palette.border};
            border-radius: 18px;
        }}

        #mainBrand,
        #workspaceTitle,
        #loginHeroTitle,
        #loginPanelTitle,
        #packingHeroTitle,
        #boxesHeroTitle,
        #lookupHeroTitle,
        #verifyHeroTitle,
        #defectHeroTitle,
        #diagnosticsHeroTitle,
        #settingsPageTitle {{
            color: {palette.text};
            font-weight: 900;
            background: transparent;
        }}

        #workspaceTitle,
        #packingHeroTitle,
        #boxesHeroTitle,
        #lookupHeroTitle,
        #verifyHeroTitle,
        #defectHeroTitle,
        #diagnosticsHeroTitle,
        #settingsPageTitle {{
            font-size: 25px;
        }}

        #loginHeroTitle {{
            font-size: 46px;
        }}

        #loginHeroSubtitle {{
            color: {palette.accent};
            font-size: 22px;
            font-weight: 800;
            background: transparent;
        }}

        #mainSection,
        #workspaceSubtitle,
        #sessionMeta,
        #loginHeroDescription,
        #loginPanelHint,
        #loginStatusValue,
        #packingHeroSubtitle,
        #packingMutedText,
        #boxesHeroSubtitle,
        #boxesMutedText,
        #lookupHeroSubtitle,
        #lookupMutedText,
        #lookupLastCode,
        #verifyHeroSubtitle,
        #verifyMutedText,
        #verifyStatusText,
        #defectHeroSubtitle,
        #defectMutedText,
        #defectStatusText,
        #diagnosticsHeroSubtitle,
        #diagnosticsMutedText,
        #diagnosticsStatusText,
        #settingsPageSubtitle,
        #settingsMutedText,
        #settingsStatusText {{
            color: {palette.muted};
            background: transparent;
        }}

        #mainSection {{
            color: {palette.accent};
            font-weight: 800;
        }}

        #packingCardTitle,
        #boxesPanelTitle,
        #lookupCardTitle,
        #verifyCardTitle,
        #defectCardTitle,
        #diagnosticsPanelTitle,
        #settingsCardTitle,
        #sessionUser,
        #loginStatusTitle,
        #loginPrimaryStatus {{
            color: {palette.text};
            font-weight: 800;
            background: transparent;
        }}

        #workspaceAccent {{
            background: {accent_background};
            border-radius: 3px;
        }}

        #mainNavItem,
        #loginStatusRow,
        #settingsFormRow {{
            background: {palette.input_bg};
            border: 1px solid {palette.border};
            border-radius: 14px;
        }}

        #mainNavItem:hover,
        #settingsHubButton:hover {{
            border-color: {palette.accent};
            background: {palette.accent_soft};
        }}

        #mainNavItem[active="true"] {{
            background: {palette.selection_bg};
            border-color: {palette.button_bg};
        }}

        #mainNavTitle,
        #settingsFormLabel {{
            color: {palette.text};
            font-weight: 800;
            background: transparent;
        }}

        #mainNavItem[active="true"] #mainNavTitle {{
            color: {palette.selection_text};
        }}

        #mainNavItem[active="true"] #mainNavSubtitle {{
            color: {palette.selection_text};
        }}

        #mainNavSubtitle {{
            color: {palette.muted};
            font-size: 11px;
            background: transparent;
        }}

        #sessionLogout,
        #packingPrimaryButton,
        #boxesPrimaryButton,
        #lookupPrimaryButton,
        #diagnosticsPrimaryButton,
        #settingsPrimaryButton {{
            min-height: 38px;
            border: 0;
            border-radius: 12px;
            padding: 0 14px;
            color: {palette.button_text};
            background: {palette.button_bg};
            font-weight: 800;
        }}

        #packingSecondaryButton,
        #boxesSecondaryButton,
        #lookupSecondaryButton,
        #settingsSecondaryButton {{
            min-height: 38px;
            border: 0;
            border-radius: 12px;
            padding: 0 14px;
            color: {palette.text};
            background: {palette.panel_alt};
            font-weight: 800;
        }}

        #packingDangerButton,
        #boxesDangerButton,
        #diagnosticsDangerButton,
        #settingsDangerButton {{
            min-height: 38px;
            border: 0;
            border-radius: 12px;
            padding: 0 14px;
            color: {palette.selection_text};
            background: {palette.danger};
            font-weight: 800;
        }}

        #packingPrimaryButton:disabled,
        #packingSecondaryButton:disabled,
        #packingDangerButton:disabled,
        #boxesPrimaryButton:disabled,
        #boxesSecondaryButton:disabled,
        #boxesDangerButton:disabled,
        #lookupSecondaryButton:disabled,
        #diagnosticsPrimaryButton:disabled,
        #diagnosticsDangerButton:disabled,
        #settingsPrimaryButton:disabled,
        #settingsSecondaryButton:disabled,
        #settingsDangerButton:disabled {{
            color: {palette.muted};
            background: {palette.panel_alt};
        }}

        #sessionLogout {{
            min-height: 32px;
            border-radius: 10px;
        }}

        #packingBadge,
        #loginStatusBadge,
        #packingScannerStatus,
        #lookupScannerStatus,
        #verifyScannerStatus,
        #defectScannerStatus {{
            border-radius: 12px;
            padding: 9px 12px;
            color: {palette.button_text};
            background: {palette.button_bg};
            font-weight: 850;
        }}

        #packingBadge[tone="idle"] {{
            color: {palette.text};
            background: {palette.panel_alt};
        }}

        #packingBadge[tone="closed"],
        #verifyWarning,
        #defectWarning {{
            color: {palette.button_text};
            background: {palette.accent};
        }}

        #packingScannerStatus[tone="error"],
        #lookupScannerStatus[tone="error"],
        #verifyScannerStatus[tone="error"],
        #defectScannerStatus[tone="error"] {{
            color: {palette.selection_text};
            background: {palette.danger};
        }}

        #packingScanTitle,
        #boxesDetailTitle,
        #lookupFoundBox,
        #verifyResult,
        #defectResult {{
            color: {palette.text};
            border-radius: 16px;
            padding: 16px 18px;
            background: {palette.panel_alt};
            font-size: 20px;
            font-weight: 850;
        }}

        #lookupFoundBox[tone="found"],
        #verifyResult[tone="ok"] {{
            color: {palette.button_text};
            background: {palette.button_bg};
        }}

        #verifyResult[tone="error"],
        #defectResult[tone="error"] {{
            color: {palette.selection_text};
            background: {palette.danger};
        }}

        #packingResult,
        #boxesStatusText,
        #lookupStatusTitle,
        #diagnosticsStatusText {{
            color: {palette.muted};
            font-weight: 700;
            background: transparent;
        }}

        #loginError,
        #packingError,
        #boxesErrorText,
        #lookupError,
        #verifyError,
        #defectError,
        #diagnosticsErrorText,
        #settingsErrorText {{
            color: {palette.danger};
            border-radius: 12px;
            padding: 9px 11px;
            background: {palette.accent_soft};
            font-weight: 750;
        }}

        #packingMetaTitle,
        #boxesMetaTitle,
        #diagnosticsMetaTitle {{
            color: {palette.muted};
            font-size: 12px;
            font-weight: 700;
            background: transparent;
        }}

        #packingMetaValue,
        #boxesMetaValue,
        #verifyMetaValue,
        #defectMetaValue,
        #diagnosticsMetaValue {{
            color: {palette.text};
            border-radius: 14px;
            padding: 11px 13px;
            background: {palette.panel_alt};
            font-weight: 700;
        }}

        #packingProgressValue,
        #boxesProgressValue {{
            color: {palette.accent};
            font-size: 18px;
            font-weight: 850;
            background: transparent;
        }}

        #packingProgressBar,
        #boxesProgressBar {{
            min-height: 14px;
            max-height: 14px;
            border: 0;
            border-radius: 7px;
            background: {palette.panel_alt};
        }}

        #packingProgressBar::chunk,
        #boxesProgressBar::chunk {{
            border-radius: 7px;
            background: {palette.accent};
        }}

        #boxesPageLabel {{
            color: {palette.text};
            min-width: 96px;
            qproperty-alignment: AlignCenter;
            font-weight: 800;
            background: transparent;
        }}

        #boxesSearchInput,
        #boxesCombo,
        #settingsInput,
        #settingsCombo {{
            min-height: 38px;
            color: {palette.text};
            background: {palette.input_bg};
            border: 1px solid {palette.border};
            border-radius: 12px;
            padding: 0 12px;
            font-weight: 650;
        }}

        #packingCheckBox,
        #verifyDuplicateCheck,
        #settingsCheckBox {{
            color: {palette.text};
            font-weight: 700;
            background: transparent;
        }}

        #packingItemsTable,
        #boxesTable,
        #boxesItemsTable,
        #lookupLog,
        #verifyLog,
        #defectLog,
        #diagnosticsLog {{
            color: {palette.text};
            background: {palette.input_bg};
            alternate-background-color: {palette.panel_alt};
            border: 1px solid {palette.border};
            border-radius: 14px;
            selection-background-color: {palette.selection_bg};
            selection-color: {palette.selection_text};
        }}

        #lookupLog,
        #verifyLog,
        #defectLog,
        #diagnosticsLog {{
            font-family: monospace;
            font-size: 13px;
        }}

        #settingsHubButton {{
            min-height: 86px;
            border: 1px solid {palette.border};
            border-radius: 18px;
            padding: 18px 20px;
            color: {palette.text};
            background: {palette.panel};
            font-size: 17px;
            font-weight: 850;
            text-align: left;
        }}

        #settingsThemeItem {{
            background: {palette.input_bg};
            border: 1px solid {palette.border};
            border-radius: 16px;
        }}

        #settingsThemeItem:hover {{
            background: {palette.accent_soft};
            border-color: {palette.accent};
        }}

        #settingsThemeItem[selected="true"] {{
            background: {palette.selection_bg};
            border-color: {palette.button_bg};
        }}

        #settingsThemeTitle {{
            color: {palette.text};
            font-size: 16px;
            font-weight: 850;
            background: transparent;
        }}

        #settingsThemeMeta {{
            color: {palette.muted};
            font-size: 12px;
            font-weight: 700;
            background: transparent;
        }}

        #settingsThemeCheck {{
            color: {palette.muted};
            border-radius: 10px;
            padding: 6px 9px;
            background: {palette.panel_alt};
            font-size: 12px;
            font-weight: 800;
        }}

        #settingsThemeItem[selected="true"] #settingsThemeCheck {{
            color: {palette.button_text};
            background: {palette.button_bg};
        }}

        #settingsThemeSwatch {{
            border: 1px solid {palette.border};
        }}

        #closeBoxDialog,
        #closeBoxConfirmDialog,
        #closeBoxProgressDialog {{
            background: {palette.panel};
        }}

        #closeBoxDialogImage {{
            background: {palette.panel_alt};
            border: 1px solid {palette.border};
            border-radius: 16px;
            padding: 8px;
        }}

        #closeBoxDialogTitle {{
            color: {palette.text};
            font-size: 22px;
            font-weight: 900;
            background: transparent;
        }}

        #closeBoxDialogMessage {{
            color: {palette.text};
            font-size: 15px;
            font-weight: 750;
            background: transparent;
        }}

        #closeBoxDialogDetails {{
            color: {palette.muted};
            border-radius: 14px;
            padding: 12px 14px;
            background: {palette.panel_alt};
            font-weight: 650;
        }}

        #closeBoxDialogButton {{
            min-width: 112px;
            min-height: 38px;
            border: 0;
            border-radius: 12px;
            padding: 0 16px;
            color: {palette.button_text};
            background: {palette.button_bg};
            font-weight: 850;
        }}

        #closeBoxDialogSecondaryButton {{
            min-width: 112px;
            min-height: 38px;
            border: 1px solid {palette.border};
            border-radius: 12px;
            padding: 0 16px;
            color: {palette.text};
            background: {palette.panel_alt};
            font-weight: 850;
        }}

        #closeBoxProgressBar {{
            min-height: 14px;
            max-height: 14px;
            border-radius: 7px;
            background: {palette.panel_alt};
            border: 1px solid {palette.border};
        }}

        #closeBoxProgressBar::chunk {{
            border-radius: 7px;
            background: {palette.button_bg};
        }}

        #settingsSlider {{
            min-height: 34px;
            background: transparent;
        }}

        #settingsInlinePicker,
        #boxesSideColumn {{
            background: transparent;
            border: 0;
        }}

        #settingsComboPopup {{
            color: {palette.text};
            background: {palette.panel};
            border: 1px solid {palette.border};
            border-radius: 10px;
            padding: 6px;
            outline: 0;
            selection-color: {palette.selection_text};
            selection-background-color: {palette.selection_bg};
        }}

        #settingsComboPopup::item {{
            min-height: 30px;
            padding: 7px 10px;
            border-radius: 8px;
        }}

        #settingsComboPopup::item:hover,
        #settingsComboPopup::item:selected {{
            color: {palette.button_text};
            background: {palette.button_bg};
        }}
    """


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

        {_custom_object_styles(palette)}

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
