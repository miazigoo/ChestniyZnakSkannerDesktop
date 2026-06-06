"""Tests for raw evdev scanner helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from chestniy_znak_desktop.domain.scanner_normalizer import GS
from chestniy_znak_desktop.scanner.evdev_keyboard_scanner import (
    EVDEV_SLEEP_GAP_RESTART_SEC,
    MultiEvdevKeyboardScanner,
    default_evdev_scanner_paths,
    is_evdev_gs_key,
    is_evdev_terminator_key,
    split_completed_gs1_buffer,
    translate_evdev_key,
)


def test_translate_evdev_key_uses_shifted_us_ascii() -> None:
    """Checks punctuation and case required by GS1 crypto tails."""

    assert translate_evdev_key(8, shift_pressed=True) == "&"
    assert translate_evdev_key(13, shift_pressed=True) == "+"
    assert translate_evdev_key(53, shift_pressed=True) == "?"
    assert translate_evdev_key(16, shift_pressed=True) == "Q"
    assert translate_evdev_key(16, shift_pressed=False) == "q"


def test_evdev_gs_key_accepts_f8_and_ctrl_right_brace() -> None:
    """Checks scanner-specific GS separator key variants."""

    assert is_evdev_gs_key(66, ctrl_down=False) is True
    assert is_evdev_gs_key(27, ctrl_down=True) is True
    assert is_evdev_gs_key(27, ctrl_down=False) is False


def test_evdev_terminator_key_accepts_ctrl_ascii_suffixes() -> None:
    """Checks CR/LF/TAB suffixes encoded as Ctrl+M/J/I."""

    assert is_evdev_terminator_key(28, ctrl_down=False) is True
    assert is_evdev_terminator_key(15, ctrl_down=False) is True
    assert is_evdev_terminator_key(50, ctrl_down=True) is True
    assert is_evdev_terminator_key(36, ctrl_down=True) is True
    assert is_evdev_terminator_key(23, ctrl_down=True) is True
    assert is_evdev_terminator_key(50, ctrl_down=False) is False


def test_split_completed_gs1_buffer_keeps_active_next_code() -> None:
    """Checks fast emission of glued GS1 scans."""

    code1 = f"0104646151697261215WsaP?q-'MzgeTtRBYt{GS}93ABCD"
    code2_prefix = "010463062619073921"
    buffer = list(code1 + code2_prefix)

    completed = split_completed_gs1_buffer(buffer)

    assert completed == [code1]
    assert "".join(buffer) == code2_prefix


def test_split_completed_gs1_buffer_does_not_cut_serial_like_prefix() -> None:
    """Checks that regex-like text inside serial does not split a code."""

    code = "0104646151697261215SERIAL011234567890123421TAIL"
    buffer = list(code)

    completed = split_completed_gs1_buffer(buffer)

    assert completed == []
    assert "".join(buffer) == code


def test_default_evdev_scanner_paths_discovers_generic_scanners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks generic HID scanner discovery without obvious regular keyboards."""

    existing = {
        "/dev/input/by-id/usb-Newtologic_4010E_XXXXXX-event-kbd",
        "/dev/input/by-id/usb-0581_011a-event-kbd",
        "/dev/input/by-id/usb-SCANNER_SCANNER_1E6D4D5C0000-event-kbd",
        "/dev/input/by-id/usb-zlww_USB_Keyboard_BS43-event-kbd",
        "/dev/input/by-id/usb-Unknown_2D_Scanner-event-kbd",
        "/dev/input/by-id/usb-Compx_2.4G_Receiver-event-kbd",
        "/dev/input/by-id/usb-Micro-Star_INT_L_CO._LTD_MSI_GK30_Gaming_Keyboard-event-kbd",
        "/dev/input/by-id/usb-Symbol_Technologies__Inc__2008_Symbol_Bar_Code_Scanner-event-kbd",
        "/dev/input/by-id/usb-HS6209_A4tech_2.4G_Wireless_Device-event-kbd",
        "/dev/input/by-id/usb-Logitech_USB_Keyboard-event-kbd",
        "/dev/input/by-id/usb-MOSART_Semi._2.4G_Keyboard_Mouse-event-kbd",
        "/dev/input/by-id/bluetooth-2D_Barcode_Scanner-event-kbd",
    }

    def fake_glob(pattern: str) -> list[str]:
        return {
            "/dev/input/by-id/usb-Newtologic_*event-kbd": [
                "/dev/input/by-id/usb-Newtologic_4010E_XXXXXX-event-kbd",
            ],
            "/dev/input/by-id/usb-0581_*event-kbd": [
                "/dev/input/by-id/usb-0581_011a-event-kbd",
            ],
            "/dev/input/by-id/usb-SCANNER_*event-kbd": [
                "/dev/input/by-id/usb-SCANNER_SCANNER_1E6D4D5C0000-event-kbd",
            ],
            "/dev/input/by-id/usb-zlww_USB_Keyboard_*event-kbd": [
                "/dev/input/by-id/usb-zlww_USB_Keyboard_BS43-event-kbd",
            ],
            "/dev/input/by-id/*event-kbd": sorted(existing),
        }.get(pattern, [])

    def fake_exists(path: Path) -> bool:
        return str(path) in existing

    monkeypatch.setattr(
        "chestniy_znak_desktop.scanner.evdev_keyboard_scanner.glob.glob",
        fake_glob,
    )
    monkeypatch.setattr(
        "chestniy_znak_desktop.scanner.evdev_keyboard_scanner.Path.exists",
        fake_exists,
    )

    assert default_evdev_scanner_paths() == [
        "/dev/input/by-id/usb-Newtologic_4010E_XXXXXX-event-kbd",
        "/dev/input/by-id/usb-0581_011a-event-kbd",
        "/dev/input/by-id/usb-zlww_USB_Keyboard_BS43-event-kbd",
        "/dev/input/by-id/usb-SCANNER_SCANNER_1E6D4D5C0000-event-kbd",
        "/dev/input/by-id/bluetooth-2D_Barcode_Scanner-event-kbd",
        "/dev/input/by-id/usb-Symbol_Technologies__Inc__2008_Symbol_Bar_Code_Scanner-event-kbd",
        "/dev/input/by-id/usb-Unknown_2D_Scanner-event-kbd",
    ]


def test_multi_evdev_scanner_reports_missing_devices() -> None:
    """Checks multi-scanner source reports no configured devices."""

    scanner = MultiEvdevKeyboardScanner(device_paths=[])
    errors: list[str] = []
    scanner.error_occurred.connect(errors.append)

    scanner.start()

    assert scanner.is_running is False
    assert errors == ["USB HID evdev scanner device not found"]


def test_multi_evdev_health_restarts_after_sleep_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks HID readers are recreated after the workstation wakes from sleep."""

    scanner = MultiEvdevKeyboardScanner(device_paths=["/dev/input/by-id/scan-event-kbd"])
    restarts: list[bool] = []
    scanner._is_running = True  # noqa: SLF001
    scanner._last_health_wall_time = 1_000.0  # noqa: SLF001
    monkeypatch.setattr(
        "chestniy_znak_desktop.scanner.evdev_keyboard_scanner.time.time",
        lambda: 1_000.0 + EVDEV_SLEEP_GAP_RESTART_SEC,
    )
    monkeypatch.setattr(scanner, "_schedule_restart", lambda: restarts.append(True))

    scanner._check_device_health()  # noqa: SLF001

    assert restarts == [True]


def test_multi_evdev_health_restarts_when_by_id_target_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checks HID readers are recreated when a scanner reappears as another eventX."""

    path = "/dev/input/by-id/scan-event-kbd"
    scanner = MultiEvdevKeyboardScanner(device_paths=[path])
    restarts: list[bool] = []
    scanner._is_running = True  # noqa: SLF001
    scanner._last_health_wall_time = 1_000.0  # noqa: SLF001
    scanner._device_snapshot = {path: "/dev/input/event10"}  # noqa: SLF001
    monkeypatch.setattr(
        "chestniy_znak_desktop.scanner.evdev_keyboard_scanner.time.time",
        lambda: 1_010.0,
    )
    monkeypatch.setattr(
        "chestniy_znak_desktop.scanner.evdev_keyboard_scanner._device_snapshot",
        lambda paths: {paths[0]: "/dev/input/event11"},
    )
    monkeypatch.setattr(scanner, "_schedule_restart", lambda: restarts.append(True))

    scanner._check_device_health()  # noqa: SLF001

    assert restarts == [True]
