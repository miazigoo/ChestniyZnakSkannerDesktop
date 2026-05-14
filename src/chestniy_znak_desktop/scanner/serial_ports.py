"""Поиск доступных COM/SPP-портов."""

from __future__ import annotations

from pathlib import Path

from serial.tools import list_ports

from chestniy_znak_desktop.scanner.base import ScannerPort


def list_serial_ports() -> list[ScannerPort]:
    """Возвращает список доступных serial-портов системы."""

    ports_by_device: dict[str, ScannerPort] = {}
    for port in list_ports.comports():
        scanner_port = ScannerPort(
            device=str(port.device),
            description=str(port.description or port.device),
            hwid=str(port.hwid or ""),
        )
        ports_by_device[scanner_port.device] = scanner_port

    for device_path in _rfcomm_device_paths():
        device = str(device_path)
        ports_by_device.setdefault(
            device,
            ScannerPort(
                device=device,
                description="Bluetooth SPP rfcomm",
                hwid="RFCOMM",
            ),
        )

    return list(ports_by_device.values())


def _rfcomm_device_paths() -> list[Path]:
    """Возвращает Linux rfcomm-устройства для Bluetooth SPP-сканеров."""

    return sorted(Path("/dev").glob("rfcomm*"))
