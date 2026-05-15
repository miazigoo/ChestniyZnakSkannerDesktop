"""Mock-тесты поиска serial-портов."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from chestniy_znak_desktop.scanner import serial_ports


def test_list_serial_ports_maps_pyserial_ports(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Проверяет преобразование pyserial port info в модель приложения."""

    monkeypatch.setattr(
        serial_ports.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(device="COM7", description="Bluetooth SPP", hwid="BTHENUM"),
            SimpleNamespace(device="/dev/ttyUSB0", description="", hwid="USB"),
        ],
    )
    monkeypatch.setattr(serial_ports, "_rfcomm_device_paths", lambda: [])

    ports = serial_ports.list_serial_ports()
    assert ports[0].device == "COM7"
    assert ports[0].title == "COM7 - Bluetooth SPP"
    assert ports[1].title == "/dev/ttyUSB0"


def test_list_serial_ports_adds_linux_rfcomm(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Проверяет добавление Linux rfcomm-порта для SPP-сканера."""

    monkeypatch.setattr(serial_ports.list_ports, "comports", lambda: [])
    monkeypatch.setattr(
        serial_ports,
        "_rfcomm_device_paths",
        lambda: [Path("/dev/rfcomm0")],
    )

    ports = serial_ports.list_serial_ports()

    assert ports[0].device == "/dev/rfcomm0"
    assert ports[0].title == "/dev/rfcomm0 - Bluetooth SPP rfcomm"


def test_list_serial_ports_deduplicates_rfcomm(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Проверяет отсутствие дубля, если pyserial уже нашел rfcomm."""

    monkeypatch.setattr(
        serial_ports.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(
                device="/dev/rfcomm0",
                description="pyserial rfcomm",
                hwid="BTH",
            ),
        ],
    )
    monkeypatch.setattr(
        serial_ports,
        "_rfcomm_device_paths",
        lambda: [Path("/dev/rfcomm0")],
    )

    ports = serial_ports.list_serial_ports()

    assert len(ports) == 1
    assert ports[0].title == "/dev/rfcomm0 - pyserial rfcomm"


def test_list_serial_ports_prefers_rfcomm_for_autostart(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет приоритет rfcomm, чтобы логин сканером работал локально."""

    monkeypatch.setattr(
        serial_ports.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(device="/dev/ttyS0", description="n/a", hwid="n/a"),
            SimpleNamespace(device="/dev/rfcomm0", description="n/a", hwid="n/a"),
        ],
    )
    monkeypatch.setattr(serial_ports, "_rfcomm_device_paths", lambda: [])

    ports = serial_ports.list_serial_ports()

    assert [port.device for port in ports] == ["/dev/rfcomm0", "/dev/ttyS0"]
    assert ports[0].auto_selectable is True
    assert ports[1].auto_selectable is False


def test_list_serial_ports_marks_phantom_linux_ttys_manual(  # type: ignore[no-untyped-def]
    monkeypatch,
) -> None:
    """Проверяет ручной режим фантомных ttyS, которые дают I/O error."""

    monkeypatch.setattr(
        serial_ports.list_ports,
        "comports",
        lambda: [
            SimpleNamespace(device="/dev/ttyS3", description="n/a", hwid="n/a"),
            SimpleNamespace(
                device="/dev/ttyUSB0",
                description="USB Serial",
                hwid="USB",
            ),
        ],
    )
    monkeypatch.setattr(serial_ports, "_rfcomm_device_paths", lambda: [])

    ports = serial_ports.list_serial_ports()

    assert [port.device for port in ports] == ["/dev/ttyUSB0", "/dev/ttyS3"]
    assert ports[0].auto_selectable is True
    assert ports[1].auto_selectable is False
