"""Распознавание служебных QR-команд сканера."""

from __future__ import annotations

from enum import Enum


class ScannerCommand(str, Enum):
    """Служебные команды, доступные из любого рабочего экрана."""

    OPEN_NEW_BOX = "OpenNewBox"
    CLOSE_BOX = "CloseBox"
    CONFIRM_OK = "ConfirmOK"


COMMAND_ALIASES = {
    "opennewbox": ScannerCommand.OPEN_NEW_BOX,
    "closebox": ScannerCommand.CLOSE_BOX,
    "confirmok": ScannerCommand.CONFIRM_OK,
}


def parse_scanner_command(raw_code: str) -> ScannerCommand | None:
    """Возвращает служебную команду из текста скана или `None`."""

    normalized = raw_code.strip().replace("\r", "").replace("\n", "").casefold()
    return COMMAND_ALIASES.get(normalized)
