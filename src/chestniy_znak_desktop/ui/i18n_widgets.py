"""Автообновление локализованных текстов Qt-виджетов."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QLabel,
    QLineEdit,
    QTabWidget,
    QWidget,
)

from chestniy_znak_desktop.i18n import translation_key_for_text, tr


def retranslate_widget_tree(root: QWidget) -> None:
    """Обновляет статические тексты виджета и его потомков по i18n-словарю."""

    widgets = [root, *root.findChildren(QWidget)]
    for widget in widgets:
        _retranslate_widget(widget)


def _retranslate_widget(widget: QWidget) -> None:
    """Обновляет один виджет, если его текущий текст есть в словаре."""

    if isinstance(widget, QLabel):
        _set_label_text(widget)
    if isinstance(widget, QAbstractButton):
        _set_button_text(widget)
    if isinstance(widget, QLineEdit):
        _set_placeholder(widget)
    if isinstance(widget, QComboBox):
        _set_combo_items(widget)
    if isinstance(widget, QTabWidget):
        _set_tab_titles(widget)


def _set_label_text(label: QLabel) -> None:
    """Переводит текст label."""

    key = translation_key_for_text(label.text())
    if key is not None:
        label.setText(tr(key))


def _set_button_text(button: QAbstractButton) -> None:
    """Переводит текст кнопки или checkbox."""

    key = translation_key_for_text(button.text())
    if key is not None:
        button.setText(tr(key))


def _set_placeholder(line_edit: QLineEdit) -> None:
    """Переводит placeholder поля ввода."""

    key = translation_key_for_text(line_edit.placeholderText())
    if key is not None:
        line_edit.setPlaceholderText(tr(key))


def _set_combo_items(combo: QComboBox) -> None:
    """Переводит статические элементы combo box."""

    for index in range(combo.count()):
        key = translation_key_for_text(combo.itemText(index))
        if key is not None:
            combo.setItemText(index, tr(key))


def _set_tab_titles(tabs: QTabWidget) -> None:
    """Переводит заголовки вкладок."""

    for index in range(tabs.count()):
        key = translation_key_for_text(tabs.tabText(index))
        if key is not None:
            tabs.setTabText(index, tr(key))
