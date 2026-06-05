"""Tests for Windows HID process worker helpers."""

from __future__ import annotations

from chestniy_znak_desktop.domain.scanner_normalizer import GS
from chestniy_znak_desktop.scanner import hid_process_worker


class _FakeUser32:
    """Minimal Win32 API fake for key translation."""

    def __init__(
        self,
        shift_pressed: bool = False,
        caps_enabled: bool = False,
        pressed_keys: set[int] | None = None,
    ) -> None:
        """Create fake API call recorder."""

        self._shift_pressed = shift_pressed
        self._caps_enabled = caps_enabled
        self._pressed_keys = pressed_keys or set()

    def GetKeyState(self, vk_code: int) -> int:  # noqa: N802
        """Return fake modifier/toggle state."""

        if vk_code == hid_process_worker.VK_SHIFT and self._shift_pressed:
            return 0x8000
        if vk_code in self._pressed_keys:
            return 0x8000
        if vk_code == hid_process_worker.VK_CAPITAL and self._caps_enabled:
            return 0x0001
        return 0


def test_windows_hid_requires_scan_suffix_by_default() -> None:
    """Checks that Windows HID does not emit scans by idle timeout."""

    assert hid_process_worker.DEFAULT_HID_IDLE_FLUSH_MS == 0


def test_translate_key_uses_us_ascii_letters_independent_from_layout() -> None:
    """Protects Windows HID scanner from current OS keyboard layout."""

    user32 = _FakeUser32()

    text = hid_process_worker._translate_key(user32, 0x41, 0x1E)  # noqa: SLF001

    assert text == "a"


def test_translate_key_uses_shift_for_uppercase_letters() -> None:
    """Checks HID shift state for letters."""

    user32 = _FakeUser32(shift_pressed=True)

    assert hid_process_worker._translate_key(user32, 0x41, 0x1E) == "A"  # noqa: SLF001


def test_translate_key_ignores_caps_lock_for_scanner_letters() -> None:
    """Protects scanner letters from the user's Caps Lock state."""

    user32 = _FakeUser32(caps_enabled=True)

    assert (
        hid_process_worker._translate_key(  # noqa: SLF001
            user32,
            0x41,
            0x1E,
            shift_pressed=False,
        )
        == "a"
    )
    assert (
        hid_process_worker._translate_key(  # noqa: SLF001
            user32,
            0x41,
            0x1E,
            shift_pressed=True,
        )
        == "A"
    )


def test_translate_key_uses_shift_for_digits_and_oem_punctuation() -> None:
    """Checks common DataMatrix keyboard wedge punctuation."""

    user32 = _FakeUser32(shift_pressed=True)

    assert hid_process_worker._translate_key(user32, 0x31, 0x02) == "!"  # noqa: SLF001
    assert hid_process_worker._translate_key(user32, hid_process_worker.VK_OEM_2, 0) == "?"


def test_translate_key_prefers_virtual_key_by_default() -> None:
    """Checks real Windows HID decoding against misleading physical scan codes."""

    user32 = _FakeUser32()

    assert hid_process_worker._translate_key(user32, 0x41, 0x10) == "a"  # noqa: SLF001
    assert (
        hid_process_worker._translate_key(  # noqa: SLF001
            user32,
            0x41,
            0x34,
            shift_pressed=True,
        )
        == "A"
    )


def test_translate_key_can_force_physical_scan_code() -> None:
    """Keeps the scan-code decoder available for candidate comparison."""

    user32 = _FakeUser32()

    assert (
        hid_process_worker._translate_key(  # noqa: SLF001
            user32,
            0x41,
            0x10,
            prefer_scan_code=True,
        )
        == "q"
    )
    assert (
        hid_process_worker._translate_key(  # noqa: SLF001
            user32,
            0x41,
            0x34,
            shift_pressed=True,
            prefer_scan_code=True,
        )
        == ">"
    )


def test_select_hid_decode_prefers_virtual_key_on_equal_score() -> None:
    """Checks that real Windows vkCode wins when both candidates look valid."""

    scan_code = f"0104630626190739215SCAN-CODE-SERIAL{GS}93AAAA"
    vk_code = f"0104630626190739215VK-CODE-SERIAL{GS}93BBBB"

    selected, mode = hid_process_worker._select_hid_decode(scan_code, vk_code)  # noqa: SLF001

    assert selected == vk_code
    assert mode == "vk"


def test_malformed_gs1_like_hid_code_allows_recoverable_prefixes() -> None:
    """Checks that recoverable HID starts are repaired downstream, not dropped."""

    assert not hid_process_worker._is_malformed_gs1_like_hid_code(  # noqa: SLF001
        f"0104630626190739215SERIAL{GS}93ABCD",
    )
    assert hid_process_worker._is_malformed_gs1_like_hid_code(  # noqa: SLF001
        f"010463030626173739215BROKEN{GS}93ABCD",
    )
    assert not hid_process_worker._is_malformed_gs1_like_hid_code(  # noqa: SLF001
        f"04630626190739215SERIAL{GS}93ABCD",
    )
    assert not hid_process_worker._is_malformed_gs1_like_hid_code(  # noqa: SLF001
        f"630626190739215SERIAL{GS}93ABCD",
    )
    assert not hid_process_worker._is_malformed_gs1_like_hid_code("SSCC-OR-OTHER-CODE")


def test_any_modifier_pressed_checks_left_and_right_modifier_keys() -> None:
    """Checks Wine HID fallback against split left/right modifier state."""

    user32 = _FakeUser32(pressed_keys={hid_process_worker.VK_LSHIFT})

    assert hid_process_worker._any_modifier_pressed(  # noqa: SLF001
        user32,
        hid_process_worker.SHIFT_KEYS,
    )


def test_split_completed_gs1_buffer_keeps_active_next_code() -> None:
    """Checks fast emission of glued scans before idle flush."""

    code1 = f"0104646151697261215WsaP?q-'MzgeTtRBYt{GS}93ABCD"
    code2_prefix = "010463062619073921"
    buffer = list(code1 + code2_prefix)

    completed = hid_process_worker._split_completed_gs1_buffer(buffer)  # noqa: SLF001

    assert completed == [code1]
    assert "".join(buffer) == code2_prefix


def test_split_completed_gs1_buffer_does_not_cut_serial_like_prefix() -> None:
    """Checks that regex-like text inside serial does not split a code."""

    code = "0104646151697261215SERIAL011234567890123421TAIL"
    buffer = list(code)

    completed = hid_process_worker._split_completed_gs1_buffer(buffer)  # noqa: SLF001

    assert completed == []
    assert "".join(buffer) == code


def test_split_completed_gs1_buffer_waits_for_next_code_prefix() -> None:
    """Checks that one active scan is not emitted prematurely."""

    code = f"0104646151697261215WsaP?q-'MzgeTtRBYt{GS}93ABCD"
    buffer = list(code)

    completed = hid_process_worker._split_completed_gs1_buffer(buffer)  # noqa: SLF001

    assert completed == []
    assert "".join(buffer) == code


def test_windows_gs_key_accepts_f8_and_ctrl_right_brace() -> None:
    """Checks scanner-specific GS separator key variants on Windows."""

    assert hid_process_worker.is_windows_gs_key(
        hid_process_worker.VK_F8,
        control_pressed=False,
    )
    assert hid_process_worker.is_windows_gs_key(
        hid_process_worker.VK_OEM_6,
        control_pressed=True,
    )
    assert not hid_process_worker.is_windows_gs_key(
        hid_process_worker.VK_OEM_6,
        control_pressed=False,
    )


def test_windows_terminator_key_accepts_ctrl_ascii_suffixes() -> None:
    """Checks CR/LF/TAB suffixes encoded as Ctrl+M/J/I."""

    assert hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_RETURN,
        control_pressed=False,
    )
    assert hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_TAB,
        control_pressed=False,
    )
    assert hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_M,
        control_pressed=True,
    )
    assert hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_J,
        control_pressed=True,
    )
    assert hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_I,
        control_pressed=True,
    )
    assert not hid_process_worker.is_windows_terminator_key(
        hid_process_worker.VK_M,
        control_pressed=False,
    )
