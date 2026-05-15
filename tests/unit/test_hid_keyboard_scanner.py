"""Тесты HID keyboard wedge источника сканов."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget  # noqa: E402

from chestniy_znak_desktop.domain.scanner_normalizer import GS  # noqa: E402
from chestniy_znak_desktop.scanner.hid_keyboard_scanner import (  # noqa: E402
    HidKeyboardScanner,
)


def qapp() -> QApplication:
    """Возвращает существующий QApplication или создает новый."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return cast(QApplication, app)


def _key_event(text: str, key: Qt.Key = Qt.Key.Key_A) -> QKeyEvent:
    """Создает key press событие для HID scanner теста."""

    return QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        Qt.KeyboardModifier.NoModifier,
        text,
    )


def _modified_key_event(
    text: str,
    key: Qt.Key,
    modifier: Qt.KeyboardModifier,
) -> QKeyEvent:
    """Создает key press событие с модификатором."""

    return QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        modifier,
        text,
    )


def test_hid_keyboard_scanner_emits_code_on_enter() -> None:
    """Проверяет сбор HID-клавиш в один код до Enter."""

    app = qapp()
    target = QWidget()
    scanner = HidKeyboardScanner(app)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    for char in "LOGIN123":
        assert scanner.eventFilter(target, _key_event(char)) is True
    assert scanner.eventFilter(target, _key_event("", Qt.Key.Key_Return)) is True

    scanner.stop()
    assert received == ["LOGIN123"]


def test_hid_keyboard_scanner_keeps_gs_for_datamatrix() -> None:
    """Проверяет сохранение GS-разделителя DataMatrix из HID-ввода."""

    app = qapp()
    target = QWidget()
    scanner = HidKeyboardScanner(app)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    for char in "010460123456789021SERIAL":
        scanner.eventFilter(target, _key_event(char))
    scanner.eventFilter(
        target,
        _modified_key_event(
            "",
            Qt.Key.Key_BracketRight,
            Qt.KeyboardModifier.ControlModifier,
        ),
    )
    for char in "92TAIL":
        scanner.eventFilter(target, _key_event(char))
    scanner.eventFilter(target, _key_event("", Qt.Key.Key_Return))

    scanner.stop()
    assert received == [f"010460123456789021SERIAL{GS}92TAIL"]


def test_hid_keyboard_scanner_ignores_editable_widgets() -> None:
    """Проверяет, что ввод в настройках не превращается в скан."""

    app = qapp()
    edit = QLineEdit()
    scanner = HidKeyboardScanner(app)
    received: list[str] = []
    scanner.code_scanned.connect(received.append)
    scanner.start()

    assert scanner.eventFilter(edit, _key_event("A")) is False
    assert scanner.eventFilter(edit, _key_event("", Qt.Key.Key_Return)) is False

    scanner.stop()
    assert received == []
