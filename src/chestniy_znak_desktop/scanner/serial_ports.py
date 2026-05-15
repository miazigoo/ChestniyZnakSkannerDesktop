"""Поиск доступных COM/SPP-портов."""

from __future__ import annotations

from pathlib import Path

from serial.tools import list_ports

from chestniy_znak_desktop.scanner.base import ScannerPort


def list_serial_ports() -> list[ScannerPort]:
    """Возвращает список доступных serial-портов системы."""

    ports_by_device: dict[str, ScannerPort] = {}
    for port in list_ports.comports():
        device = str(port.device)
        description = str(port.description or port.device)
        hwid = str(port.hwid or "")
        is_phantom_ttys = _is_phantom_linux_ttys(
            device=device,
            description=str(port.description or ""),
            hwid=hwid,
        )
        scanner_port = ScannerPort(
            device=device,
            description="Linux system serial port" if is_phantom_ttys else description,
            hwid=hwid,
            auto_selectable=not is_phantom_ttys,
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

    return sorted(ports_by_device.values(), key=_port_priority)


def _rfcomm_device_paths() -> list[Path]:
    """Возвращает Linux rfcomm-устройства для Bluetooth SPP-сканеров."""

    return sorted(Path("/dev").glob("rfcomm*"))


def _is_phantom_linux_ttys(*, device: str, description: str, hwid: str) -> bool:
    """Проверяет фантомные Linux ttyS-порты, которые не являются сканерами."""

    return (
        device.startswith("/dev/ttyS")
        and description.strip().lower() in {"", "n/a"}
        and hwid.strip().lower() in {"", "n/a"}
    )


def _port_priority(port: ScannerPort) -> int:
    """Возвращает приоритет автозапуска для найденного serial-порта."""

    if port.device.startswith("/dev/rfcomm"):
        return 0
    if not port.auto_selectable:
        return 9
    return 1
