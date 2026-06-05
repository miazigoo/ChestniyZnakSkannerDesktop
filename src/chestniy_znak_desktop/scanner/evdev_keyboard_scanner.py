"""Raw Linux evdev keyboard-wedge scanner source."""

from __future__ import annotations

import glob
import logging
import struct
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

from PySide6.QtCore import QObject, QTimer, Signal

from chestniy_znak_desktop.domain.scanner_normalizer import GS, split_completed_gs1_buffer_text

logger = logging.getLogger(__name__)

DEFAULT_HID_IDLE_FLUSH_MS = 180
EVDEV_RESTART_DELAY_MS = 1_000
EVDEV_HEALTH_CHECK_MS = 15_000
EVDEV_SLEEP_GAP_RESTART_SEC = 120
HUMAN_KEYBOARD_PATH_MARKERS = (
    "a4tech",
    "apple",
    "cherry",
    "chicony",
    "dell",
    "hp_",
    "hewlett",
    "keychron",
    "lenovo",
    "lite-on",
    "logitech",
    "microsoft",
    "mosart",
    "primax",
    "razer",
)

EV_KEY = 0x01
KEY_UP = 0
KEY_DOWN = 1
KEY_REPEAT = 2
KEY_ENTER = 28
KEY_LEFTCTRL = 29
KEY_RIGHTCTRL = 97
KEY_LEFTSHIFT = 42
KEY_RIGHTSHIFT = 54
KEY_TAB = 15
KEY_I = 23
KEY_J = 36
KEY_M = 50
KEY_RIGHTBRACE = 27
KEY_F8 = 66

EVENT_STRUCT = struct.Struct("<qqHHI")
SHIFT_KEYS = {KEY_LEFTSHIFT, KEY_RIGHTSHIFT}
CTRL_KEYS = {KEY_LEFTCTRL, KEY_RIGHTCTRL}
TERMINATOR_KEYS = {KEY_ENTER, KEY_TAB}
CONTROL_TERMINATOR_KEYS = {KEY_I, KEY_J, KEY_M}
KEYMAP: dict[int, tuple[str, str]] = {
    2: ("1", "!"),
    3: ("2", "@"),
    4: ("3", "#"),
    5: ("4", "$"),
    6: ("5", "%"),
    7: ("6", "^"),
    8: ("7", "&"),
    9: ("8", "*"),
    10: ("9", "("),
    11: ("0", ")"),
    12: ("-", "_"),
    13: ("=", "+"),
    16: ("q", "Q"),
    17: ("w", "W"),
    18: ("e", "E"),
    19: ("r", "R"),
    20: ("t", "T"),
    21: ("y", "Y"),
    22: ("u", "U"),
    23: ("i", "I"),
    24: ("o", "O"),
    25: ("p", "P"),
    26: ("[", "{"),
    27: ("]", "}"),
    30: ("a", "A"),
    31: ("s", "S"),
    32: ("d", "D"),
    33: ("f", "F"),
    34: ("g", "G"),
    35: ("h", "H"),
    36: ("j", "J"),
    37: ("k", "K"),
    38: ("l", "L"),
    39: (";", ":"),
    40: ("'", '"'),
    41: ("`", "~"),
    43: ("\\", "|"),
    44: ("z", "Z"),
    45: ("x", "X"),
    46: ("c", "C"),
    47: ("v", "V"),
    48: ("b", "B"),
    49: ("n", "N"),
    50: ("m", "M"),
    51: (",", "<"),
    52: (".", ">"),
    53: ("/", "?"),
    57: (" ", " "),
}


class EvdevKeyboardScanner(QObject):
    """Reads a Linux keyboard-wedge scanner before X11/Wine key translation."""

    code_scanned = Signal(str)
    code_scanned_at = Signal(str, float, int)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        device_path: str | None = None,
        idle_flush_ms: int = DEFAULT_HID_IDLE_FLUSH_MS,
        dedupe_window_ms: int = 750,
        parent: QObject | None = None,
    ) -> None:
        """Create a raw evdev scanner source."""

        super().__init__(parent)
        self._device_path = device_path or default_evdev_scanner_path()
        self._idle_flush_sec = idle_flush_ms / 1000
        self._dedupe_window_sec = dedupe_window_ms / 1000
        self._buffer: list[str] = []
        self._shift_down: set[int] = set()
        self._ctrl_down: set[int] = set()
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream: BinaryIO | None = None
        self._idle_timer: threading.Timer | None = None
        self._is_running = False
        self._last_event_age_ms = 0

    @property
    def is_running(self) -> bool:
        """Return True while the evdev reader thread is active."""

        return self._is_running

    @property
    def device_path(self) -> str:
        """Return the configured evdev path."""

        return self._device_path

    def start(self) -> None:
        """Start the raw evdev reader thread."""

        if self._is_running:
            return
        if not self._device_path:
            self.error_occurred.emit("USB HID evdev scanner device not found")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="EvdevKeyboardScanner",
            daemon=True,
        )
        self._thread.start()
        self._is_running = True

    def stop(self) -> None:
        """Stop reading raw evdev input."""

        if not self._is_running:
            return
        self._is_running = False
        self._stop_event.set()
        self._cancel_idle_timer()
        stream = self._stream
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._stream = None
        with self._lock:
            self._buffer.clear()
            self._shift_down.clear()
            self._ctrl_down.clear()
        self.stopped.emit()

    def _run(self) -> None:
        """Read Linux input_event structs and translate them to scanner text."""

        try:
            path = Path(self._device_path)
            with path.open("rb", buffering=0) as stream:
                self._stream = stream
                logger.info("Evdev HID scanner opened device=%s", self._device_path)
                self.started.emit()
                while not self._stop_event.is_set():
                    data = stream.read(EVENT_STRUCT.size)
                    if len(data) != EVENT_STRUCT.size:
                        continue
                    self._handle_event(data)
        except PermissionError:
            self.error_occurred.emit(f"Нет доступа к USB HID сканеру: {self._device_path}")
            logger.exception("Evdev HID scanner permission denied device=%s", self._device_path)
        except OSError as exc:
            if not self._stop_event.is_set():
                self.error_occurred.emit(f"Ошибка USB HID сканера: {exc!s}")
                logger.exception("Evdev HID scanner failed device=%s", self._device_path)
        finally:
            self._stream = None
            if self._is_running:
                self._is_running = False
                self.stopped.emit()

    def _handle_event(self, data: bytes) -> None:
        sec, usec, event_type, code, value = EVENT_STRUCT.unpack(data)
        self._last_event_age_ms = self._event_age_ms(sec, usec)
        if event_type != EV_KEY or value == KEY_REPEAT:
            return
        if code in SHIFT_KEYS:
            self._track_modifier(self._shift_down, code, value)
            return
        if code in CTRL_KEYS:
            self._track_modifier(self._ctrl_down, code, value)
            return
        if value != KEY_DOWN:
            return
        ctrl_down = bool(self._ctrl_down)
        if is_evdev_terminator_key(code, ctrl_down=ctrl_down):
            self._flush_buffer()
            return
        if is_evdev_gs_key(code, ctrl_down=ctrl_down):
            self._append_text(GS)
            return
        text = translate_evdev_key(code, shift_pressed=bool(self._shift_down))
        if text:
            self._append_text(text)
            self._flush_completed_gs1_codes()

    @staticmethod
    def _track_modifier(active: set[int], code: int, value: int) -> None:
        if value == KEY_DOWN:
            active.add(code)
        elif value == KEY_UP:
            active.discard(code)

    def _append_text(self, text: str) -> None:
        with self._lock:
            self._buffer.append(text)
        self._restart_idle_timer()

    def _flush_buffer(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            code = "".join(self._buffer).strip()
            self._buffer.clear()
        self._cancel_idle_timer()
        self._emit_code(code)

    def _flush_completed_gs1_codes(self) -> None:
        with self._lock:
            completed_codes = split_completed_gs1_buffer(self._buffer)
        for code in completed_codes:
            self._emit_code(code)

    def _emit_code(self, code: str) -> None:
        if not code:
            return
        now = time.monotonic()
        if (
            code == self._last_emitted_code
            and now - self._last_emitted_at < self._dedupe_window_sec
        ):
            return
        self._last_emitted_code = code
        self._last_emitted_at = now
        logger.info(
            "Evdev HID code emitted device=%s event_age_ms=%s code_len=%s",
            self._device_path,
            self._last_event_age_ms,
            len(code),
        )
        self.code_scanned_at.emit(code, now, self._last_event_age_ms)
        self.code_scanned.emit(code)

    @staticmethod
    def _event_age_ms(sec: int, usec: int) -> int:
        """Return approximate delay between kernel event timestamp and reader handling."""

        event_ts = sec + usec / 1_000_000
        now = time.monotonic()
        age = now - event_ts
        if age < -1 or age > 86_400:
            age = time.time() - event_ts
        return max(0, int(age * 1000))

    def _restart_idle_timer(self) -> None:
        self._cancel_idle_timer()
        timer = threading.Timer(self._idle_flush_sec, self._flush_buffer)
        timer.daemon = True
        self._idle_timer = timer
        timer.start()

    def _cancel_idle_timer(self) -> None:
        if self._idle_timer is None:
            return
        self._idle_timer.cancel()
        self._idle_timer = None


class MultiEvdevKeyboardScanner(QObject):
    """Reads several Linux keyboard-wedge scanners in parallel."""

    code_scanned = Signal(str)
    code_scanned_at = Signal(str, float, int)
    error_occurred = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(
        self,
        device_paths: list[str] | None = None,
        idle_flush_ms: int = DEFAULT_HID_IDLE_FLUSH_MS,
        dedupe_window_ms: int = 750,
        parent: QObject | None = None,
    ) -> None:
        """Create a multi-device evdev scanner source."""

        super().__init__(parent)
        self._auto_discover = device_paths is None
        self._device_paths = default_evdev_scanner_paths() if device_paths is None else device_paths
        self._idle_flush_ms = idle_flush_ms
        self._dedupe_window_ms = dedupe_window_ms
        self._scanners: list[EvdevKeyboardScanner] = []
        self._running_devices: set[str] = set()
        self._is_running = False
        self._started_emitted = False
        self._restart_requested = False
        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.setInterval(EVDEV_RESTART_DELAY_MS)
        self._restart_timer.timeout.connect(self._restart_running_scanners)
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(EVDEV_HEALTH_CHECK_MS)
        self._health_timer.timeout.connect(self._check_device_health)
        self._device_snapshot: dict[str, str] = {}
        self._last_health_wall_time = time.time()

    @property
    def is_running(self) -> bool:
        """Return True while at least one evdev reader is active."""

        return self._is_running

    @property
    def device_paths(self) -> list[str]:
        """Return configured evdev device paths."""

        return list(self._device_paths)

    def start(self) -> None:
        """Start all configured evdev scanner readers."""

        if self._is_running:
            return
        if self._auto_discover:
            self._device_paths = default_evdev_scanner_paths()
        if not self._device_paths:
            self.error_occurred.emit("USB HID evdev scanner device not found")
            return
        self._is_running = True
        self._started_emitted = False
        self._running_devices.clear()
        self._device_snapshot = _device_snapshot(self._device_paths)
        self._last_health_wall_time = time.time()
        self._health_timer.start()
        self._scanners = [
            self._create_scanner(device_path)
            for device_path in self._device_paths
            if Path(device_path).exists()
        ]
        if not self._scanners:
            self._is_running = False
            self._health_timer.stop()
            self.error_occurred.emit("USB HID evdev scanner device not found")
            return
        logger.info(
            "Starting %s evdev HID scanner devices: %s",
            len(self._scanners),
            ", ".join(scanner.device_path for scanner in self._scanners),
        )
        for scanner in self._scanners:
            scanner.start()

    def stop(self) -> None:
        """Stop all evdev scanner readers."""

        if not self._is_running:
            return
        self._is_running = False
        self._restart_requested = False
        self._restart_timer.stop()
        self._health_timer.stop()
        for scanner in list(self._scanners):
            scanner.stop()
        self._scanners.clear()
        self._running_devices.clear()
        self._started_emitted = False
        self.stopped.emit()

    def _create_scanner(self, device_path: str) -> EvdevKeyboardScanner:
        scanner = EvdevKeyboardScanner(
            device_path=device_path,
            idle_flush_ms=self._idle_flush_ms,
            dedupe_window_ms=self._dedupe_window_ms,
            parent=self,
        )
        scanner.code_scanned.connect(self.code_scanned.emit)
        scanner.code_scanned_at.connect(self.code_scanned_at.emit)
        scanner.error_occurred.connect(
            lambda message, path=device_path: self._on_error(path, message)
        )
        scanner.started.connect(lambda path=device_path: self._on_started(path))
        scanner.stopped.connect(lambda path=device_path: self._on_stopped(path))
        return scanner

    def _on_started(self, device_path: str) -> None:
        self._running_devices.add(device_path)
        if self._started_emitted:
            return
        self._started_emitted = True
        self.started.emit()

    def _on_stopped(self, device_path: str) -> None:
        self._running_devices.discard(device_path)
        if not self._is_running:
            return
        if self._restart_requested:
            return
        if self._running_devices:
            return
        self._is_running = False
        self._health_timer.stop()
        self.stopped.emit()

    def _on_error(self, device_path: str, message: str) -> None:
        logger.warning("Evdev HID scanner failed device=%s: %s", device_path, message)
        if self._auto_discover and self._is_running and "Нет доступа" not in message:
            self._running_devices.discard(device_path)
            self._schedule_restart()
            return
        if self._running_devices - {device_path}:
            self._running_devices.discard(device_path)
            return
        self.error_occurred.emit(message)

    def _schedule_restart(self) -> None:
        """Plans rediscovery after one of USB HID devices disappeared."""

        self._restart_requested = True
        if not self._restart_timer.isActive():
            self._restart_timer.start()

    def _check_device_health(self) -> None:
        """Rediscover HID devices after sleep, replug, or by-id target changes."""

        if not self._is_running:
            return
        now = time.time()
        sleep_gap_sec = now - self._last_health_wall_time
        self._last_health_wall_time = now
        current_paths = default_evdev_scanner_paths() if self._auto_discover else self._device_paths
        current_snapshot = _device_snapshot(current_paths)
        if sleep_gap_sec >= EVDEV_SLEEP_GAP_RESTART_SEC:
            logger.info(
                "Evdev HID health restart after sleep gap %.0fs",
                sleep_gap_sec,
            )
            self._device_paths = current_paths
            self._device_snapshot = current_snapshot
            self._schedule_restart()
            return
        if current_paths != self._device_paths or current_snapshot != self._device_snapshot:
            logger.info(
                "Evdev HID device set changed old=%s new=%s",
                self._device_paths,
                current_paths,
            )
            self._device_paths = current_paths
            self._device_snapshot = current_snapshot
            self._schedule_restart()
            return
        if not self._running_devices:
            self._schedule_restart()

    def _restart_running_scanners(self) -> None:
        """Restarts all evdev readers and rediscover currently connected scanners."""

        if not self._restart_requested:
            return
        self._restart_requested = False
        if not self._is_running:
            return
        logger.info("Restarting evdev HID scanners after device change")
        self._is_running = False
        for scanner in list(self._scanners):
            scanner.stop()
        self._scanners.clear()
        self._running_devices.clear()
        self._started_emitted = False
        self.start()


def translate_evdev_key(code: int, *, shift_pressed: bool) -> str:
    """Translate a Linux evdev key code to US ASCII scanner text."""

    pair = KEYMAP.get(code)
    if pair is None:
        return ""
    regular, shifted = pair
    return shifted if shift_pressed else regular


def is_evdev_gs_key(code: int, *, ctrl_down: bool) -> bool:
    """Return True when evdev key event represents a GS separator."""

    return code == KEY_F8 or (code == KEY_RIGHTBRACE and ctrl_down)


def is_evdev_terminator_key(code: int, *, ctrl_down: bool) -> bool:
    """Return True when evdev key event represents a scan suffix."""

    return code in TERMINATOR_KEYS or (ctrl_down and code in CONTROL_TERMINATOR_KEYS)


def split_completed_gs1_buffer(buffer: list[str]) -> list[str]:
    """Emit glued GS1 codes when a following 01+GTIN+21 prefix appears."""

    text = "".join(buffer)
    completed_codes, remainder = split_completed_gs1_buffer_text(text)
    if not completed_codes:
        return []
    buffer[:] = list(remainder)
    return completed_codes


def default_evdev_scanner_path() -> str:
    """Return the first USB HID scanner event path available locally."""

    paths = default_evdev_scanner_paths()
    return paths[0] if paths else ""


def default_evdev_scanner_paths() -> list[str]:
    """Return all scanner-like evdev event paths available locally."""

    return [path for path in candidate_evdev_scanner_paths() if Path(path).exists()]


def candidate_evdev_scanner_paths() -> list[str]:
    """Return scanner-like evdev paths for native Linux and Wine-on-Linux."""

    if sys.platform == "win32":
        return [
            r"Z:\dev\input\by-id\usb-Newtologic_4010E_XXXXXX-event-kbd",
            r"Z:\dev\input\by-id\usb-Newtologic_4010E-event-kbd",
            r"Z:\dev\input\by-id\usb-0581_011a-event-kbd",
            r"Z:\dev\input\by-id\usb-SCANNER_SCANNER_1E6D4D5C0000-event-kbd",
            r"Z:\dev\input\by-id\usb-zlww_USB_Keyboard_BS43-event-kbd",
        ]
    return _ordered_unique(
        [
            "/dev/input/by-id/usb-Newtologic_4010E_XXXXXX-event-kbd",
            "/dev/input/by-id/usb-Newtologic_4010E-event-kbd",
            "/dev/input/by-id/usb-0581_011a-event-kbd",
            "/dev/input/by-id/usb-zlww_USB_Keyboard_BS43-event-kbd",
            *sorted(glob.glob("/dev/input/by-id/usb-Newtologic_*event-kbd")),
            *sorted(glob.glob("/dev/input/by-id/usb-0581_*event-kbd")),
            *sorted(glob.glob("/dev/input/by-id/usb-SCANNER_*event-kbd")),
            *sorted(glob.glob("/dev/input/by-id/usb-zlww_USB_Keyboard_*event-kbd")),
            *_generic_hid_keyboard_paths(),
        ]
    )


def _generic_hid_keyboard_paths() -> list[str]:
    """Return generic keyboard-wedge candidates, excluding obvious real keyboards."""

    return [
        path
        for path in sorted(glob.glob("/dev/input/by-id/*event-kbd"))
        if _is_scanner_like_hid_path(path)
    ]


def _is_scanner_like_hid_path(path: str) -> bool:
    """Return False only for obvious human keyboards."""

    normalized = Path(path).name.lower()
    return not any(marker in normalized for marker in HUMAN_KEYBOARD_PATH_MARKERS)


def _device_snapshot(paths: list[str]) -> dict[str, str]:
    """Return current by-id targets to detect replug with the same symlink name."""

    snapshot: dict[str, str] = {}
    for path in paths:
        device_path = Path(path)
        if not device_path.exists():
            snapshot[path] = ""
            continue
        snapshot[path] = str(device_path.resolve(strict=False))
    return snapshot


def _ordered_unique(paths: list[str]) -> list[str]:
    """Return paths without duplicates, preserving order."""

    seen: set[str] = set()
    unique_paths: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        unique_paths.append(path)
    return unique_paths
