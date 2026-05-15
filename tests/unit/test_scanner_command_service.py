"""Тесты распознавания служебных команд сканера."""

from __future__ import annotations

from chestniy_znak_desktop.services.scanner_command_service import (
    ScannerCommand,
    parse_scanner_command,
)
from chestniy_znak_desktop.ui.app_window import AppWindow


class FakeCommandWindow:
    """Минимальный объект для проверки маршрутизации служебного скана."""

    def __init__(self) -> None:
        """Создает списки вызовов fake-окна."""

        self.commands: list[ScannerCommand] = []
        self.auth_tokens: list[str] = []

    def _handle_scanner_command(self, command: ScannerCommand) -> bool:
        """Запоминает служебную команду как обработанную."""

        self.commands.append(command)
        return True


def test_parse_scanner_command_accepts_known_tokens() -> None:
    """Проверяет распознавание служебных QR-токенов."""

    assert parse_scanner_command("OpenNewBox") == ScannerCommand.OPEN_NEW_BOX
    assert parse_scanner_command("CloseBox") == ScannerCommand.CLOSE_BOX
    assert parse_scanner_command("ConfirmOK") == ScannerCommand.CONFIRM_OK


def test_parse_scanner_command_normalizes_scanner_line_endings() -> None:
    """Проверяет устойчивость к регистру и переводам строк сканера."""

    assert parse_scanner_command(" opennewbox\r\n") == ScannerCommand.OPEN_NEW_BOX


def test_parse_scanner_command_ignores_regular_codes() -> None:
    """Проверяет, что обычные коды маркировки не считаются командами."""

    assert parse_scanner_command("010460123456789021SERIAL") is None


def test_service_command_is_intercepted_before_regular_routing() -> None:
    """Проверяет, что служебный токен не уходит в auth или scan-обработчики."""

    window = FakeCommandWindow()

    AppWindow._handle_scanned_code(window, "OpenNewBox")  # type: ignore[arg-type]

    assert window.commands == [ScannerCommand.OPEN_NEW_BOX]
    assert window.auth_tokens == []
