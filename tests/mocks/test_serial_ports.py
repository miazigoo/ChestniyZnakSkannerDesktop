"""Mock-тесты поиска serial-портов."""

from __future__ import annotations

from types import SimpleNamespace

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

    ports = serial_ports.list_serial_ports()
    assert ports[0].device == "COM7"
    assert ports[0].title == "COM7 - Bluetooth SPP"
    assert ports[1].title == "/dev/ttyUSB0"
