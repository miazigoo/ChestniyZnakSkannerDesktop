"""Общие UI-заготовки для страниц настроек."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIcon, VectorIconName

SETTINGS_COMBO_POPUP_QSS = """
    QAbstractItemView {
        color: #f8fbff;
        background: #202938;
        border: 1px solid rgba(129, 140, 168, 110);
        border-radius: 10px;
        padding: 6px;
        outline: 0;
        selection-color: #071212;
        selection-background-color: #66d2c7;
    }
    QAbstractItemView::item {
        min-height: 30px;
        padding: 7px 10px;
        border-radius: 8px;
    }
    QAbstractItemView::item:hover {
        color: #071212;
        background: #8fb8ff;
    }
    QAbstractItemView::item:selected {
        color: #071212;
        background: #66d2c7;
    }
"""


def apply_combo_popup_style(combo: QComboBox) -> None:
    """Применяет читаемый стиль popup-списка combo box."""

    combo.view().setObjectName("settingsComboPopup")
    combo.view().setStyleSheet(SETTINGS_COMBO_POPUP_QSS)


def create_page_header(
    *,
    title: str,
    subtitle: str,
    icon_name: VectorIconName,
    icon_color: str,
) -> QFrame:
    """Создает верхний hero-блок страницы настроек."""

    header = QFrame()
    header.setObjectName("settingsPageHeader")
    icon = VectorIcon(icon_name, icon_color)
    title_label = QLabel(title)
    title_label.setObjectName("settingsPageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("settingsPageSubtitle")
    subtitle_label.setWordWrap(True)

    text = QVBoxLayout()
    text.addWidget(title_label)
    text.addWidget(subtitle_label)

    layout = QHBoxLayout(header)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(16)
    layout.addWidget(icon)
    layout.addLayout(text, 1)
    return header


def create_card(
    *,
    title: str,
    subtitle: str = "",
    icon_name: VectorIconName | None = None,
    icon_color: str = "#66d2c7",
) -> tuple[QFrame, QVBoxLayout]:
    """Создает карточку настроек и возвращает ее основной layout."""

    card = QFrame()
    card.setObjectName("settingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(14)
    if icon_name is not None:
        header = QHBoxLayout()
        header.addWidget(VectorIcon(icon_name, icon_color))
        text = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("settingsCardTitle")
        text.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("settingsMutedText")
            subtitle_label.setWordWrap(True)
            text.addWidget(subtitle_label)
        header.addLayout(text, 1)
        layout.addLayout(header)
    else:
        title_label = QLabel(title)
        title_label.setObjectName("settingsCardTitle")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("settingsMutedText")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)
    return card, layout


def create_form_row(title: str, widget: QWidget) -> QFrame:
    """Создает строку формы с подписью и управляющим виджетом."""

    row = QFrame()
    row.setObjectName("settingsFormRow")
    title_label = QLabel(title)
    title_label.setObjectName("settingsFormLabel")
    title_label.setWordWrap(True)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(12)
    layout.addWidget(title_label, 1)
    layout.addWidget(widget, 2)
    return row


def create_back_button() -> QPushButton:
    """Создает стандартную кнопку возврата к группам настроек."""

    button = QPushButton("Назад к настройкам")
    button.setObjectName("settingsSecondaryButton")
    return button
