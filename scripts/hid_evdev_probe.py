"""Probe Linux evdev keyboard-wedge scanner input before Wine/X11 translation."""

from __future__ import annotations

import argparse
import select
import struct
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from chestniy_znak_desktop.domain.scanner_normalizer import (  # noqa: E402
    GS,
    MarkingCodeParseError,
    parse_marking_code,
    visible,
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
KEY_ESC = 1
KEY_F8 = 66
EVENT_STRUCT = struct.Struct("llHHI")

SHIFT_KEYS = {KEY_LEFTSHIFT, KEY_RIGHTSHIFT}
CTRL_KEYS = {KEY_LEFTCTRL, KEY_RIGHTCTRL}
CONTROL_TERMINATOR_KEYS = {KEY_I, KEY_J, KEY_M}
KEY_NAMES = {
    KEY_ESC: "ESC",
    KEY_TAB: "TAB",
    KEY_ENTER: "ENTER",
    KEY_LEFTCTRL: "LEFTCTRL",
    KEY_RIGHTCTRL: "RIGHTCTRL",
    KEY_LEFTSHIFT: "LEFTSHIFT",
    KEY_RIGHTSHIFT: "RIGHTSHIFT",
    KEY_I: "I",
    KEY_J: "J",
    KEY_M: "M",
    KEY_F8: "F8",
}
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


def main() -> int:
    """Run a short raw evdev scan probe."""

    args = _parse_args()
    device = Path(args.device)
    deadline = time.monotonic() + args.duration if args.duration > 0 else None
    buffer: list[str] = []
    tokens: list[str] = []
    events: list[str] = []
    shift_down: set[int] = set()
    ctrl_down: set[int] = set()

    try:
        with device.open("rb", buffering=0) as stream:
            print(f"Listening on {device}. Scan a code; Ctrl+C to stop.")
            while deadline is None or time.monotonic() < deadline:
                timeout = None if deadline is None else max(0.0, deadline - time.monotonic())
                readable, _, _ = select.select([stream], [], [], timeout)
                if not readable:
                    break
                data = stream.read(EVENT_STRUCT.size)
                if len(data) != EVENT_STRUCT.size:
                    continue
                _sec, _usec, event_type, code, value = EVENT_STRUCT.unpack(data)
                if event_type != EV_KEY or value == KEY_REPEAT:
                    continue
                if code in SHIFT_KEYS:
                    _track_modifier(shift_down, code, value)
                    events.append(_event_text(code, value, _key_name(code), shift_down, ctrl_down))
                    continue
                if code in CTRL_KEYS:
                    _track_modifier(ctrl_down, code, value)
                    events.append(_event_text(code, value, _key_name(code), shift_down, ctrl_down))
                    continue
                if value != KEY_DOWN:
                    events.append(_event_text(code, value, _key_name(code), shift_down, ctrl_down))
                    continue
                if code in {KEY_ENTER, KEY_TAB} or (ctrl_down and code in CONTROL_TERMINATOR_KEYS):
                    tokens.append(f"<{_key_name(code)}>")
                    events.append(_event_text(code, value, _key_name(code), shift_down, ctrl_down))
                    _flush(buffer, tokens, events)
                    continue
                if code == KEY_RIGHTBRACE and ctrl_down:
                    buffer.append(GS)
                    tokens.append("<GS:CTRL+]>")
                    events.append(_event_text(code, value, "<GS>", shift_down, ctrl_down))
                    continue
                if code == KEY_F8:
                    buffer.append(GS)
                    tokens.append("<GS:F8>")
                    events.append(_event_text(code, value, "<GS>", shift_down, ctrl_down))
                    continue
                translated = _translate_key(code, bool(shift_down))
                events.append(
                    _event_text(
                        code,
                        value,
                        translated or f"<{_key_name(code)}>",
                        shift_down,
                        ctrl_down,
                    )
                )
                if translated:
                    buffer.append(translated)
                    tokens.append(translated)
    except PermissionError:
        print(f"Permission denied: {device}", file=sys.stderr)
        print("Add the user to the input group or run with sudo for diagnostics.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        pass
    if buffer:
        _flush(buffer, tokens, events)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--device",
        default="/dev/input/by-id/usb-Newtologic_4010E_XXXXXX-event-kbd",
        help="evdev event device for the scanner",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="seconds to listen; 0 means until interrupted",
    )
    return parser.parse_args()


def _track_modifier(active: set[int], code: int, value: int) -> None:
    if value == KEY_DOWN:
        active.add(code)
        return
    if value == KEY_UP:
        active.discard(code)


def _translate_key(code: int, shift_pressed: bool) -> str:
    pair = KEYMAP.get(code)
    if pair is None:
        return ""
    regular, shifted = pair
    return shifted if shift_pressed else regular


def _key_name(code: int) -> str:
    return KEY_NAMES.get(code, f"KEY_{code}")


def _event_text(
    code: int,
    value: int,
    text: str,
    shift_down: set[int],
    ctrl_down: set[int],
) -> str:
    state = "down" if value == KEY_DOWN else "up"
    modifiers = []
    if shift_down:
        modifiers.append("S")
    if ctrl_down:
        modifiers.append("C")
    modifier_text = "".join(modifiers) or "-"
    return f"{code}:{_key_name(code)}:{state}:{modifier_text}:{text}"


def _flush(buffer: list[str], tokens: list[str], events: list[str]) -> None:
    raw_code = "".join(buffer).strip()
    buffer.clear()
    token_text = "".join(tokens)
    tokens.clear()
    if not raw_code and not token_text:
        return
    print(f"TOKENS {token_text!r}")
    print(f"RAW len={len(raw_code)} visible={visible(raw_code)!r}")
    try:
        parsed = parse_marking_code(raw_code)
    except MarkingCodeParseError as exc:
        print(f"PARSE error={exc}")
    else:
        print(
            "PARSE "
            f"gtin={parsed.gtin} serial_len={len(parsed.serial)} "
            f"serial={parsed.serial!r} ai={parsed.ai_parts}"
        )
    print("EVENTS " + " ".join(events[-160:]))
    events.clear()


if __name__ == "__main__":
    raise SystemExit(main())
