"""Поиск доступных COM/SPP-портов."""

from __future__ import annotations

from serial.tools import list_ports

from chestniy_znak_desktop.scanner.base import ScannerPort


def list_serial_ports() -> list[ScannerPort]:
    """Возвращает список доступных serial-портов системы."""

    ports = []
    for port in list_ports.comports():
        ports.append(
            ScannerPort(
                device=str(port.device),
                description=str(port.description or port.device),
                hwid=str(port.hwid or ""),
            )
        )
    return ports
