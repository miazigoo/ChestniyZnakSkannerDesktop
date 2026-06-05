"""Windows Raw Input keyboard scanner source."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QWidget

from chestniy_znak_desktop.domain.scanner_normalizer import (
    GS,
    restore_missing_gs1_marking_prefix,
    visible,
)
from chestniy_znak_desktop.scanner.hid_process_worker import (
    CONTROL_KEYS,
    CONTROL_SCAN_CODES,
    SHIFT_KEYS,
    SHIFT_SCAN_CODES,
    STALE_HID_BUFFER_DROP_SEC,
    WM_KEYDOWN,
    WM_KEYUP,
    WM_SYSKEYDOWN,
    WM_SYSKEYUP,
    _is_malformed_gs1_like_hid_code,
    _select_hid_decode,
    _translate_key,
    is_windows_gs_key,
    is_windows_terminator_key,
)
from chestniy_znak_desktop.scanner.windows_hid_scanner import WindowsHidScanner

logger = logging.getLogger(__name__)

QueueMessage = tuple[str, str]
RID_INPUT = 0x10000003
RIM_TYPEKEYBOARD = 1
RIDEV_INPUTSINK = 0x00000100
RIDI_DEVICENAME = 0x20000007
WM_INPUT = 0x00FF


def _is_windows_platform() -> bool:
    """Return True when running on Windows."""

    return sys.platform == "win32"


class RawInputDevice(ctypes.Structure):
    """Win32 RAWINPUTDEVICE."""

    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RawInputHeader(ctypes.Structure):
    """Win32 RAWINPUTHEADER."""

    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RawKeyboard(ctypes.Structure):
    """Win32 RAWKEYBOARD."""

    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class RawInputUnion(ctypes.Union):
    """Keyboard-only RAWINPUT union subset."""

    _fields_ = [("keyboard", RawKeyboard)]


class RawInput(ctypes.Structure):
    """Win32 RAWINPUT."""

    _fields_ = [("header", RawInputHeader), ("data", RawInputUnion)]


class Msg(ctypes.Structure):
    """Win32 MSG."""

    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


@dataclass(slots=True)
class RawInputDeviceState:
    """Accumulated scanner state for one Raw Input device."""

    scan_code_buffer: list[str] = field(default_factory=list)
    vk_code_buffer: list[str] = field(default_factory=list)
    shift_keys_down: set[int] = field(default_factory=set)
    control_keys_down: set[int] = field(default_factory=set)
    last_key_at: float = 0.0
    key_events: int = 0
    shift_events: int = 0
    control_events: int = 0

    @property
    def has_buffer(self) -> bool:
        return bool(self.scan_code_buffer or self.vk_code_buffer)

    @property
    def buffer_len(self) -> int:
        return max(len(self.scan_code_buffer), len(self.vk_code_buffer))

    def reset_buffer(self) -> tuple[str, str, int, int, int, int]:
        scan_code = "".join(self.scan_code_buffer)
        vk_code = "".join(self.vk_code_buffer)
        buffer_len = self.buffer_len
        key_events = self.key_events
        shift_events = self.shift_events
        control_events = self.control_events
        self.scan_code_buffer.clear()
        self.vk_code_buffer.clear()
        self.key_events = 0
        self.shift_events = 0
        self.control_events = 0
        return scan_code, vk_code, buffer_len, key_events, shift_events, control_events


class WindowsRawInputScanner(QObject, QAbstractNativeEventFilter):
    """Captures Windows keyboard-wedge scanners through Raw Input WM_INPUT."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        idle_flush_ms: int = 300,
        dedupe_window_ms: int = 750,
        poll_interval_ms: int = 100,
        fallback_scanner: WindowsHidScanner | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create Raw Input scanner source."""

        QObject.__init__(self, parent)
        self._idle_flush_sec = idle_flush_ms / 1000
        self._dedupe_window_sec = dedupe_window_ms / 1000
        self._root_widget: QWidget | None = None
        self._is_running = False
        self._devices: dict[int, RawInputDeviceState] = {}
        self._device_names: dict[int, str] = {}
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0
        self._user32: Any | None = None
        self._raw_input_active = False
        self._fallback_scanner = fallback_scanner
        if self._fallback_scanner is None and _is_windows_platform():
            self._fallback_scanner = WindowsHidScanner()
        if self._fallback_scanner is not None:
            self._fallback_scanner.code_scanned.connect(self._emit_fallback_code)
            self._fallback_scanner.error_occurred.connect(self._on_fallback_error)
        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self._flush_or_drop_stale_buffers)

    @property
    def is_running(self) -> bool:
        """Return True while Raw Input capture is installed."""

        return self._is_running

    def bind_root(self, widget: QWidget) -> None:
        """Bind Raw Input to the top-level window handle."""

        self._root_widget = widget

    def start(self) -> None:
        """Register Raw Input keyboard capture."""

        if self._is_running:
            return
        if not _is_windows_platform():
            self._is_running = True
            self.started.emit()
            return
        if self._root_widget is None:
            logger.warning("Windows Raw Input root window is not bound; starting HID fallback")
            self._start_fallback()
            self._is_running = True
            self.started.emit()
            return
        app = QApplication.instance()
        if app is None:
            logger.warning("Windows Raw Input requires QApplication; starting HID fallback")
            self._start_fallback()
            self._is_running = True
            self.started.emit()
            return
        windll = getattr(ctypes, "windll")
        user32 = windll.user32
        self._configure_winapi(user32)
        hwnd = int(self._root_widget.winId())
        device = RawInputDevice(
            usUsagePage=0x01,
            usUsage=0x06,
            dwFlags=RIDEV_INPUTSINK,
            hwndTarget=hwnd,
        )
        ok = user32.RegisterRawInputDevices(
            ctypes.byref(device),
            1,
            ctypes.sizeof(RawInputDevice),
        )
        if not ok:
            error_code = windll.kernel32.GetLastError()
            logger.warning(
                "Windows Raw Input registration failed; starting HID fallback: WinError %s",
                error_code,
            )
            self._start_fallback()
            self._is_running = True
            self.started.emit()
            return
        self._user32 = user32
        app.installNativeEventFilter(self)
        self._timer.start()
        self._raw_input_active = True
        self._start_fallback()
        self._is_running = True
        logger.info("Windows Raw Input scanner active hwnd=0x%X", hwnd)
        self.started.emit()

    def stop(self) -> None:
        """Stop Raw Input capture."""

        if not self._is_running:
            return
        app = QApplication.instance()
        if app is not None and self._raw_input_active:
            app.removeNativeEventFilter(self)
        self._timer.stop()
        self._stop_fallback()
        self._devices.clear()
        self._device_names.clear()
        self._raw_input_active = False
        self._is_running = False
        self.stopped.emit()

    def nativeEventFilter(
        self,
        event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> tuple[bool, int]:
        """Handle WM_INPUT messages delivered by Qt."""

        _ = event_type
        if not self._is_running or self._user32 is None:
            return False, 0
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(Msg)).contents
        except (TypeError, ValueError):
            return False, 0
        if msg.message != WM_INPUT:
            return False, 0
        self._handle_raw_input(int(msg.lParam))
        return False, 0

    def _handle_raw_input(self, hraw_input: int) -> None:
        user32 = self._user32
        if user32 is None:
            return
        size = wintypes.UINT(0)
        result = user32.GetRawInputData(
            hraw_input,
            RID_INPUT,
            None,
            ctypes.byref(size),
            ctypes.sizeof(RawInputHeader),
        )
        if result == wintypes.UINT(-1).value or size.value <= 0:
            return
        buffer = ctypes.create_string_buffer(size.value)
        result = user32.GetRawInputData(
            hraw_input,
            RID_INPUT,
            buffer,
            ctypes.byref(size),
            ctypes.sizeof(RawInputHeader),
        )
        if result == wintypes.UINT(-1).value:
            return
        raw_input = ctypes.cast(buffer, ctypes.POINTER(RawInput)).contents
        if raw_input.header.dwType != RIM_TYPEKEYBOARD:
            return
        keyboard = raw_input.data.keyboard
        device_id = int(raw_input.header.hDevice or 0)
        state = self._devices.setdefault(device_id, RawInputDeviceState())
        self._remember_device_name(device_id, raw_input.header.hDevice)
        self._handle_key(
            device_id=device_id,
            state=state,
            vk_code=int(keyboard.VKey),
            scan_code=int(keyboard.MakeCode),
            message=int(keyboard.Message),
        )

    def _handle_key(
        self,
        *,
        device_id: int,
        state: RawInputDeviceState,
        vk_code: int,
        scan_code: int,
        message: int,
    ) -> None:
        is_key_down = message in {WM_KEYDOWN, WM_SYSKEYDOWN}
        if message not in {WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP}:
            return
        if vk_code in SHIFT_KEYS or scan_code in SHIFT_SCAN_CODES:
            if is_key_down:
                state.shift_keys_down.add(scan_code or vk_code)
            else:
                state.shift_keys_down.clear()
            state.shift_events += 1
            return
        if vk_code in CONTROL_KEYS or scan_code in CONTROL_SCAN_CODES:
            if is_key_down:
                state.control_keys_down.add(scan_code or vk_code)
            else:
                state.control_keys_down.clear()
            state.control_events += 1
            return
        if not is_key_down:
            return
        state.last_key_at = time.monotonic()
        state.key_events += 1
        control_pressed = bool(state.control_keys_down)
        if is_windows_terminator_key(vk_code, control_pressed=control_pressed):
            logger.info(
                "Windows Raw Input scan suffix device=%s vk=0x%02X scan=0x%02X buffer_len=%s",
                self._device_label(device_id),
                vk_code,
                scan_code,
                state.buffer_len,
            )
            self._flush_device(device_id, state)
            return
        if is_windows_gs_key(vk_code, control_pressed=control_pressed):
            state.scan_code_buffer.append(GS)
            state.vk_code_buffer.append(GS)
            return
        shift_pressed = bool(state.shift_keys_down)
        scan_text = _translate_key(
            self._user32,
            vk_code,
            scan_code,
            shift_pressed=shift_pressed,
            prefer_scan_code=True,
        )
        vk_text = _translate_key(
            self._user32,
            vk_code,
            scan_code,
            shift_pressed=shift_pressed,
            prefer_scan_code=False,
        )
        if len(scan_text) == 1 and scan_text.isprintable():
            state.scan_code_buffer.append(scan_text)
        if len(vk_text) == 1 and vk_text.isprintable():
            state.vk_code_buffer.append(vk_text)

    def _flush_or_drop_stale_buffers(self) -> None:
        now = time.monotonic()
        for device_id, state in list(self._devices.items()):
            if not state.has_buffer:
                continue
            idle_for = now - state.last_key_at
            if self._idle_flush_sec > 0 and idle_for >= self._idle_flush_sec:
                self._flush_device(device_id, state)
            elif idle_for >= STALE_HID_BUFFER_DROP_SEC:
                self._drop_device_buffer(device_id, state)

    def _flush_device(self, device_id: int, state: RawInputDeviceState) -> None:
        if not state.has_buffer:
            return
        scan_code, vk_code, buffer_len, key_events, shift_events, control_events = (
            state.reset_buffer()
        )
        code, selected_mode = _select_hid_decode(scan_code, vk_code)
        logger.info(
            "Windows Raw Input scan assembled device=%s selected=%s buffer_len=%s "
            "key_events=%s shift_events=%s control_events=%s",
            self._device_label(device_id),
            selected_mode,
            buffer_len,
            key_events,
            shift_events,
            control_events,
        )
        if scan_code.strip() and vk_code.strip() and scan_code.strip() != vk_code.strip():
            logger.warning(
                "Windows Raw Input decoded scan/vk differently; device=%s selected=%s "
                "scan=%r vk=%r",
                self._device_label(device_id),
                selected_mode,
                visible(scan_code),
                visible(vk_code),
            )
        self._emit_code(device_id, code, source="raw")

    def _drop_device_buffer(self, device_id: int, state: RawInputDeviceState) -> None:
        scan_code, vk_code, *_ = state.reset_buffer()
        logger.warning(
            "Windows Raw Input dropped buffered scan because suffix did not arrive: "
            "device=%s scan=%r vk=%r",
            self._device_label(device_id),
            visible(scan_code),
            visible(vk_code),
        )

    def _emit_code(self, device_id: int, code: str, *, source: str) -> None:
        code = code.strip()
        if not code:
            return
        code, prefix_warning = restore_missing_gs1_marking_prefix(code)
        if prefix_warning:
            logger.warning(
                "Windows %s scanner restored scanner prefix: %s; device=%s code=%r",
                source,
                prefix_warning,
                self._device_label(device_id),
                visible(code),
            )
        if _is_malformed_gs1_like_hid_code(code):
            logger.warning(
                "Windows %s scanner dropped malformed GS1-like scan: device=%s code=%r",
                source,
                self._device_label(device_id),
                visible(code),
            )
            return
        now = time.monotonic()
        if (
            code == self._last_emitted_code
            and now - self._last_emitted_at < self._dedupe_window_sec
        ):
            return
        self._last_emitted_code = code
        self._last_emitted_at = now
        self.code_scanned.emit(code)

    def _emit_fallback_code(self, code: str) -> None:
        """Emit code received from the low-level keyboard hook fallback."""

        self._emit_code(0, code, source="fallback")

    def _on_fallback_error(self, message: str) -> None:
        """Report fallback errors only when Raw Input is unavailable."""

        if self._raw_input_active:
            logger.warning(
                "Windows HID fallback scanner failed while Raw Input is active: %s", message
            )
            return
        self.error_occurred.emit(message)

    def _start_fallback(self) -> None:
        if self._fallback_scanner is None:
            return
        self._fallback_scanner.start()

    def _stop_fallback(self) -> None:
        if self._fallback_scanner is None:
            return
        self._fallback_scanner.stop()

    def _remember_device_name(self, device_id: int, handle: int | None) -> None:
        if device_id in self._device_names or self._user32 is None or not handle:
            return
        size = wintypes.UINT(0)
        self._user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, None, ctypes.byref(size))
        if size.value <= 0:
            self._device_names[device_id] = f"0x{device_id:X}"
            return
        buffer = ctypes.create_unicode_buffer(size.value)
        result = self._user32.GetRawInputDeviceInfoW(
            handle,
            RIDI_DEVICENAME,
            buffer,
            ctypes.byref(size),
        )
        if result == wintypes.UINT(-1).value:
            self._device_names[device_id] = f"0x{device_id:X}"
            return
        self._device_names[device_id] = buffer.value or f"0x{device_id:X}"
        logger.info("Windows Raw Input keyboard device seen: %s", self._device_names[device_id])

    def _device_label(self, device_id: int) -> str:
        return self._device_names.get(device_id, f"0x{device_id:X}")

    @staticmethod
    def _configure_winapi(user32: Any) -> None:
        user32.RegisterRawInputDevices.argtypes = [
            ctypes.POINTER(RawInputDevice),
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.RegisterRawInputDevices.restype = wintypes.BOOL
        user32.GetRawInputData.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.UINT),
            wintypes.UINT,
        ]
        user32.GetRawInputData.restype = wintypes.UINT
        user32.GetRawInputDeviceInfoW.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.UINT),
        ]
        user32.GetRawInputDeviceInfoW.restype = wintypes.UINT
