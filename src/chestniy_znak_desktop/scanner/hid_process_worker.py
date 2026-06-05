"""Out-of-process HID keyboard scanner for Windows."""

from __future__ import annotations

import ctypes
import logging
import multiprocessing as mp
import queue
import sys
import time
from collections import deque
from collections.abc import Callable
from ctypes import wintypes
from multiprocessing.context import BaseContext
from multiprocessing.queues import Queue as MpQueue
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from chestniy_znak_desktop.domain.scanner_normalizer import (
    GS,
    has_gs1_marking_prefix,
    is_complete_gs1_marking_code,
    restore_missing_gs1_marking_prefix,
    split_completed_gs1_buffer_text,
    visible,
)

logger = logging.getLogger(__name__)

QueueMessage = tuple[str, str]
KeyboardEvent = tuple[int, int, bool]
LRESULT = getattr(wintypes, "LRESULT", ctypes.c_ssize_t)
DEFAULT_HID_IDLE_FLUSH_MS = 0
STALE_HID_BUFFER_DROP_SEC = 2.0

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
PM_REMOVE = 0x0001
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_CAPITAL = 0x14
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_0 = 0x30
VK_9 = 0x39
VK_A = 0x41
VK_I = 0x49
VK_J = 0x4A
VK_M = 0x4D
VK_Z = 0x5A
VK_NUMPAD0 = 0x60
VK_NUMPAD9 = 0x69
VK_MULTIPLY = 0x6A
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_DECIMAL = 0x6E
VK_DIVIDE = 0x6F
VK_F8 = 0x77
VK_OEM_1 = 0xBA
VK_OEM_PLUS = 0xBB
VK_OEM_COMMA = 0xBC
VK_OEM_MINUS = 0xBD
VK_OEM_PERIOD = 0xBE
VK_OEM_2 = 0xBF
VK_OEM_3 = 0xC0
VK_OEM_4 = 0xDB
VK_OEM_5 = 0xDC
VK_OEM_6 = 0xDD
VK_OEM_7 = 0xDE
VK_OEM_102 = 0xE2

SHIFT_DIGITS: dict[int, str] = {
    0x30: ")",
    0x31: "!",
    0x32: "@",
    0x33: "#",
    0x34: "$",
    0x35: "%",
    0x36: "^",
    0x37: "&",
    0x38: "*",
    0x39: "(",
}
OEM_KEYS: dict[int, tuple[str, str]] = {
    VK_OEM_1: (";", ":"),
    VK_OEM_PLUS: ("=", "+"),
    VK_OEM_COMMA: (",", "<"),
    VK_OEM_MINUS: ("-", "_"),
    VK_OEM_PERIOD: (".", ">"),
    VK_OEM_2: ("/", "?"),
    VK_OEM_3: ("`", "~"),
    VK_OEM_4: ("[", "{"),
    VK_OEM_5: ("\\", "|"),
    VK_OEM_6: ("]", "}"),
    VK_OEM_7: ("'", '"'),
    VK_OEM_102: ("\\", "|"),
}
NUMPAD_KEYS: dict[int, str] = {
    VK_MULTIPLY: "*",
    VK_ADD: "+",
    VK_SUBTRACT: "-",
    VK_DECIMAL: ".",
    VK_DIVIDE: "/",
}
SHIFT_KEYS = {VK_SHIFT, VK_LSHIFT, VK_RSHIFT}
CONTROL_KEYS = {VK_CONTROL, VK_LCONTROL, VK_RCONTROL}
CONTROL_TERMINATOR_KEYS = {VK_I, VK_J, VK_M}
SHIFT_SCAN_CODES = {0x2A, 0x36}
CONTROL_SCAN_CODES = {0x1D}
US_SCAN_CODE_KEYS: dict[int, tuple[str, str]] = {
    0x02: ("1", "!"),
    0x03: ("2", "@"),
    0x04: ("3", "#"),
    0x05: ("4", "$"),
    0x06: ("5", "%"),
    0x07: ("6", "^"),
    0x08: ("7", "&"),
    0x09: ("8", "*"),
    0x0A: ("9", "("),
    0x0B: ("0", ")"),
    0x0C: ("-", "_"),
    0x0D: ("=", "+"),
    0x10: ("q", "Q"),
    0x11: ("w", "W"),
    0x12: ("e", "E"),
    0x13: ("r", "R"),
    0x14: ("t", "T"),
    0x15: ("y", "Y"),
    0x16: ("u", "U"),
    0x17: ("i", "I"),
    0x18: ("o", "O"),
    0x19: ("p", "P"),
    0x1A: ("[", "{"),
    0x1B: ("]", "}"),
    0x1E: ("a", "A"),
    0x1F: ("s", "S"),
    0x20: ("d", "D"),
    0x21: ("f", "F"),
    0x22: ("g", "G"),
    0x23: ("h", "H"),
    0x24: ("j", "J"),
    0x25: ("k", "K"),
    0x26: ("l", "L"),
    0x27: (";", ":"),
    0x28: ("'", '"'),
    0x29: ("`", "~"),
    0x2B: ("\\", "|"),
    0x2C: ("z", "Z"),
    0x2D: ("x", "X"),
    0x2E: ("c", "C"),
    0x2F: ("v", "V"),
    0x30: ("b", "B"),
    0x31: ("n", "N"),
    0x32: ("m", "M"),
    0x33: (",", "<"),
    0x34: (".", ">"),
    0x35: ("/", "?"),
    0x39: (" ", " "),
}


class KbdLlHookStruct(ctypes.Structure):
    """Win32 KBDLLHOOKSTRUCT."""

    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


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


HookProc = (
    ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
    if hasattr(ctypes, "WINFUNCTYPE")
    else ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
)


class HidProcessScanner(QObject):
    """Runs Windows HID keyboard scanner capture in a helper process."""

    code_scanned = Signal(str)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        idle_flush_ms: int = DEFAULT_HID_IDLE_FLUSH_MS,
        dedupe_window_ms: int = 750,
        poll_interval_ms: int = 15,
        process_factory: Callable[..., mp.Process] | None = None,
        context: BaseContext | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create a scanner bridge that polls a multiprocessing queue."""

        super().__init__(parent)
        self._idle_flush_ms = idle_flush_ms
        self._dedupe_window_ms = dedupe_window_ms
        self._context = context or mp.get_context("spawn")
        self._process_factory = (
            process_factory or self._context.Process  # type: ignore[attr-defined]
        )
        self._queue: MpQueue[QueueMessage] | None = None
        self._stop_event: mp.synchronize.Event | None = None
        self._process: mp.Process | None = None
        self._is_running = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(poll_interval_ms)
        self._poll_timer.timeout.connect(self._poll_queue)

    @property
    def is_running(self) -> bool:
        """Return True when the helper process is active."""

        return self._is_running

    def start(self) -> None:
        """Start the helper process."""

        if self._is_running:
            return
        if not _is_windows():
            self.started.emit()
            self._is_running = True
            return
        self._queue = self._context.Queue()
        self._stop_event = self._context.Event()
        self._process = self._process_factory(
            target=_run_windows_hid_hook,
            args=(
                self._queue,
                self._stop_event,
                self._idle_flush_ms,
                self._dedupe_window_ms,
            ),
            daemon=True,
        )
        self._process.start()
        self._is_running = True
        self._poll_timer.start()
        self.started.emit()

    def stop(self) -> None:
        """Stop the helper process."""

        if not self._is_running:
            return
        self._is_running = False
        self._poll_timer.stop()
        if self._stop_event is not None:
            self._stop_event.set()
        if self._process is not None:
            self._process.join(timeout=1.5)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0)
        self._queue = None
        self._stop_event = None
        self._process = None
        self.stopped.emit()

    def _poll_queue(self) -> None:
        """Drain helper messages into Qt signals."""

        if self._queue is None:
            return
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break
            if kind == "code":
                self.code_scanned.emit(payload)
            elif kind == "error":
                self.error_occurred.emit(payload)
            elif kind == "started":
                logger.info("%s", payload)
            elif kind == "info":
                logger.info("%s", payload)
            elif kind == "warning":
                logger.warning("%s", payload)
        if self._process is not None and self._process.exitcode is not None:
            exitcode = self._process.exitcode
            self._is_running = False
            self._poll_timer.stop()
            self._queue = None
            self._stop_event = None
            self._process = None
            if exitcode != 0:
                self.error_occurred.emit(f"Windows HID worker stopped: exit code {exitcode}")
            self.stopped.emit()


def _run_windows_hid_hook(
    output_queue: MpQueue[QueueMessage],
    stop_event: mp.synchronize.Event,
    idle_flush_ms: int,
    dedupe_window_ms: int,
) -> None:
    """Capture global keyboard input in a Windows helper process."""

    if not _is_windows():
        return

    windll = ctypes.windll  # type: ignore[attr-defined]
    user32 = windll.user32
    kernel32 = windll.kernel32
    _configure_winapi(user32, kernel32)
    scan_code_buffer: list[str] = []
    vk_code_buffer: list[str] = []
    last_key_at = 0.0
    last_emitted_code = ""
    last_emitted_at = 0.0
    callback_error_reported = False
    idle_flush_sec = idle_flush_ms / 1000
    dedupe_window_sec = dedupe_window_ms / 1000
    event_queue: deque[KeyboardEvent] = deque()
    shift_keys_down: set[int] = set()
    control_keys_down: set[int] = set()
    buffered_key_events = 0
    buffered_shift_events = 0
    buffered_control_events = 0

    def emit_code(code: str) -> None:
        nonlocal last_emitted_code, last_emitted_at
        code = code.strip()
        if not code:
            return
        code, prefix_warning = restore_missing_gs1_marking_prefix(code)
        if prefix_warning:
            output_queue.put(
                (
                    "warning",
                    "Windows HID restored scanner prefix: "
                    f"{prefix_warning}; code={visible(code)!r}",
                )
            )
        if _is_malformed_gs1_like_hid_code(code):
            output_queue.put(
                (
                    "warning",
                    "Windows HID dropped malformed GS1-like scan: "
                    f"{visible(code)!r}; expected prefix 01 + 14 digits + 21",
                )
            )
            return
        now = time.monotonic()
        if code == last_emitted_code and now - last_emitted_at < dedupe_window_sec:
            return
        last_emitted_code = code
        last_emitted_at = now
        output_queue.put(("code", code))

    def flush() -> None:
        nonlocal buffered_control_events, buffered_key_events, buffered_shift_events
        nonlocal scan_code_buffer, vk_code_buffer
        if not scan_code_buffer and not vk_code_buffer:
            return
        scan_code = "".join(scan_code_buffer)
        vk_code = "".join(vk_code_buffer)
        buffer_len = max(len(scan_code_buffer), len(vk_code_buffer))
        scan_code_buffer = []
        vk_code_buffer = []
        code, selected_mode = _select_hid_decode(scan_code, vk_code)
        output_queue.put(
            (
                "info",
                "Windows HID scan assembled "
                f"selected={selected_mode} buffer_len={buffer_len} "
                f"key_events={buffered_key_events} shift_events={buffered_shift_events} "
                f"control_events={buffered_control_events}",
            )
        )
        buffered_key_events = 0
        buffered_shift_events = 0
        buffered_control_events = 0
        if scan_code.strip() and vk_code.strip() and scan_code.strip() != vk_code.strip():
            output_queue.put(
                (
                    "warning",
                    "Windows HID decoded scan/vk differently; "
                    f"selected={selected_mode} scan={visible(scan_code)!r} "
                    f"vk={visible(vk_code)!r}",
                )
            )
        emit_code(code)

    def drop_buffer_without_suffix() -> None:
        nonlocal buffered_control_events, buffered_key_events, buffered_shift_events
        nonlocal scan_code_buffer, vk_code_buffer
        if not scan_code_buffer and not vk_code_buffer:
            return
        scan_code = "".join(scan_code_buffer)
        vk_code = "".join(vk_code_buffer)
        scan_code_buffer = []
        vk_code_buffer = []
        output_queue.put(
            (
                "warning",
                "Windows HID dropped buffered scan because suffix did not arrive: "
                f"scan={visible(scan_code)!r} vk={visible(vk_code)!r}",
            )
        )
        buffered_key_events = 0
        buffered_shift_events = 0
        buffered_control_events = 0

    def handle_key(vk_code: int, scan_code: int, is_key_down: bool) -> None:
        nonlocal buffered_control_events, buffered_key_events, buffered_shift_events
        nonlocal last_key_at
        if vk_code in SHIFT_KEYS or scan_code in SHIFT_SCAN_CODES:
            if is_key_down:
                shift_keys_down.add(scan_code or vk_code)
            else:
                shift_keys_down.clear()
            buffered_shift_events += 1
            return
        if vk_code in CONTROL_KEYS or scan_code in CONTROL_SCAN_CODES:
            if is_key_down:
                control_keys_down.add(scan_code or vk_code)
            else:
                control_keys_down.clear()
            buffered_control_events += 1
            return
        if not is_key_down:
            return
        last_key_at = time.monotonic()
        buffered_key_events += 1
        control_pressed = bool(control_keys_down)
        if is_windows_terminator_key(vk_code, control_pressed=control_pressed):
            output_queue.put(
                (
                    "info",
                    "Windows HID scan suffix received "
                    f"vk=0x{vk_code:02X} scan=0x{scan_code:02X} "
                    f"buffer_len={max(len(scan_code_buffer), len(vk_code_buffer))}",
                )
            )
            flush()
            return
        if is_windows_gs_key(vk_code, control_pressed=control_pressed):
            scan_code_buffer.append(GS)
            vk_code_buffer.append(GS)
            return
        shift_pressed = bool(shift_keys_down)
        scan_text = _translate_key(
            user32,
            vk_code,
            scan_code,
            shift_pressed=shift_pressed,
            prefer_scan_code=True,
        )
        vk_text = _translate_key(
            user32,
            vk_code,
            scan_code,
            shift_pressed=shift_pressed,
            prefer_scan_code=False,
        )
        if len(scan_text) == 1 and scan_text.isprintable():
            scan_code_buffer.append(scan_text)
        if len(vk_text) == 1 and vk_text.isprintable():
            vk_code_buffer.append(vk_text)

    def drain_keyboard_events() -> None:
        while event_queue:
            vk_code, scan_code, is_key_down = event_queue.popleft()
            handle_key(vk_code, scan_code, is_key_down)

    def report_callback_error(exc: Exception) -> None:
        nonlocal callback_error_reported
        if callback_error_reported:
            return
        callback_error_reported = True
        output_queue.put(("error", f"Ошибка обработки Windows HID-клавиши: {exc!s}"))

    def callback(n_code: int, w_param: int, l_param: int) -> int:
        if n_code >= 0 and w_param in {
            WM_KEYDOWN,
            WM_KEYUP,
            WM_SYSKEYDOWN,
            WM_SYSKEYUP,
        }:
            try:
                event = ctypes.cast(l_param, ctypes.POINTER(KbdLlHookStruct)).contents
                event_queue.append(
                    (
                        int(event.vkCode),
                        int(event.scanCode),
                        w_param in {WM_KEYDOWN, WM_SYSKEYDOWN},
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive Win32 callback guard
                report_callback_error(exc)
        return int(user32.CallNextHookEx(None, n_code, w_param, l_param))

    hook_callback = HookProc(callback)
    hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL,
        hook_callback,
        kernel32.GetModuleHandleW(None),
        0,
    )
    if not hook:
        error_code = kernel32.GetLastError()
        output_queue.put(("error", f"Не удалось запустить Windows HID hook: WinError {error_code}"))
        return
    output_queue.put(("started", "Windows HID hook active"))

    try:
        msg = Msg()
        while not stop_event.is_set():
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == WM_QUIT:
                    return
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            drain_keyboard_events()
            if scan_code_buffer or vk_code_buffer:
                idle_for = time.monotonic() - last_key_at
                if idle_flush_sec > 0 and idle_for >= idle_flush_sec:
                    flush()
                elif idle_for >= STALE_HID_BUFFER_DROP_SEC:
                    drop_buffer_without_suffix()
            time.sleep(0.005)
    finally:
        user32.UnhookWindowsHookEx(hook)


def _is_windows() -> bool:
    """Return True on Windows."""

    return sys.platform == "win32"


def _split_completed_gs1_buffer(buffer: list[str]) -> list[str]:
    """Emit complete glued GS1 codes when a next 01+GTIN+21 prefix has started."""

    text = "".join(buffer)
    completed_codes, remainder = split_completed_gs1_buffer_text(text)
    if not completed_codes:
        return []
    buffer[:] = list(remainder)
    return completed_codes


def _select_hid_decode(scan_code: str, vk_code: str) -> tuple[str, str]:
    """Choose the safer Windows HID decoding candidate."""

    scan_code = scan_code.strip()
    vk_code = vk_code.strip()
    if not scan_code:
        return vk_code, "vk"
    if not vk_code:
        return scan_code, "scan"
    if scan_code == vk_code:
        return vk_code, "same"

    scan_score = _score_hid_decode(scan_code)
    vk_score = _score_hid_decode(vk_code)
    if vk_score >= scan_score:
        return vk_code, "vk"
    return scan_code, "scan"


def _score_hid_decode(code: str) -> int:
    """Score a HID candidate by GS1 plausibility."""

    if not code:
        return -1
    score = 0
    if is_complete_gs1_marking_code(code):
        score += 100
    elif has_gs1_marking_prefix(code):
        score += 50
    if GS in code:
        score += 10
    return score


def _is_malformed_gs1_like_hid_code(code: str) -> bool:
    """Return True for HID payloads that look like broken ChZ DataMatrix scans."""

    normalized = code.strip()
    if has_gs1_marking_prefix(normalized):
        return False
    return normalized.startswith("01")


def is_windows_gs_key(vk_code: int, *, control_pressed: bool) -> bool:
    """Return True when a Windows keyboard event represents a GS separator."""

    return vk_code == VK_F8 or (vk_code == VK_OEM_6 and control_pressed)


def is_windows_terminator_key(vk_code: int, *, control_pressed: bool) -> bool:
    """Return True when a Windows keyboard event represents a scan suffix."""

    return vk_code in {VK_RETURN, VK_TAB} or (
        control_pressed and vk_code in CONTROL_TERMINATOR_KEYS
    )


def _configure_winapi(user32: Any, kernel32: Any) -> None:
    """Configure ctypes prototypes for Win32 calls used by the hook process."""

    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int,
        HookProc,
        wintypes.HINSTANCE,
        wintypes.DWORD,
    ]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.PeekMessageW.argtypes = [
        ctypes.POINTER(Msg),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.PeekMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(Msg)]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(Msg)]
    user32.DispatchMessageW.restype = LRESULT
    user32.GetKeyboardState.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
    user32.GetKeyboardState.restype = wintypes.BOOL
    user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
    user32.GetKeyboardLayout.restype = ctypes.c_void_p
    user32.ToUnicodeEx.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_ubyte),
        wintypes.LPWSTR,
        ctypes.c_int,
        wintypes.UINT,
        ctypes.c_void_p,
    ]
    user32.ToUnicodeEx.restype = ctypes.c_int
    user32.GetKeyState.argtypes = [ctypes.c_int]
    user32.GetKeyState.restype = ctypes.c_short
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD


def _modifier_pressed(user32: Any, vk_code: int) -> bool:
    """Return True when a Win32 modifier key is down."""

    return bool(user32.GetKeyState(vk_code) & 0x8000)


def _any_modifier_pressed(user32: Any, vk_codes: set[int]) -> bool:
    """Return True when any of the given Win32 modifiers is down."""

    return any(_modifier_pressed(user32, vk_code) for vk_code in vk_codes)


def _key_toggled(user32: Any, vk_code: int) -> bool:
    """Return True when a Win32 toggle key is enabled."""

    return bool(user32.GetKeyState(vk_code) & 0x0001)


def _translate_key(
    user32: Any,
    vk_code: int,
    scan_code: int,
    *,
    shift_pressed: bool | None = None,
    prefer_scan_code: bool = False,
) -> str:
    """Translate a Windows HID key to scanner ASCII."""

    if vk_code in {
        VK_BACK,
        VK_CONTROL,
        VK_MENU,
        VK_SHIFT,
        VK_CAPITAL,
        VK_ESCAPE,
    }:
        return ""
    if shift_pressed is None:
        shift_pressed = _modifier_pressed(user32, VK_SHIFT)
    if prefer_scan_code:
        scan_text = _translate_scan_code(scan_code, shift_pressed=shift_pressed)
        if scan_text:
            return scan_text
        return _translate_virtual_key(vk_code, shift_pressed=shift_pressed)
    vk_text = _translate_virtual_key(vk_code, shift_pressed=shift_pressed)
    if vk_text:
        return vk_text
    return _translate_scan_code(scan_code, shift_pressed=shift_pressed)


def _translate_scan_code(scan_code: int, *, shift_pressed: bool) -> str:
    """Translate a physical scan code by the US keyboard wedge map."""

    scan_code_key = US_SCAN_CODE_KEYS.get(scan_code & 0xFF)
    if scan_code_key is not None:
        regular, shifted = scan_code_key
        return shifted if shift_pressed else regular
    return ""


def _translate_virtual_key(vk_code: int, *, shift_pressed: bool) -> str:
    """Translate a virtual key by the scanner's expected US ASCII map."""

    if VK_A <= vk_code <= VK_Z:
        char = chr(vk_code)
        if shift_pressed:
            return char
        return char.lower()
    if VK_0 <= vk_code <= VK_9:
        if shift_pressed:
            return SHIFT_DIGITS.get(vk_code, "")
        return chr(vk_code)
    if VK_NUMPAD0 <= vk_code <= VK_NUMPAD9:
        return str(vk_code - VK_NUMPAD0)
    if vk_code in NUMPAD_KEYS:
        return NUMPAD_KEYS[vk_code]
    if vk_code in OEM_KEYS:
        regular, shifted = OEM_KEYS[vk_code]
        return shifted if shift_pressed else regular
    if vk_code == VK_SPACE:
        return " "
    return ""
