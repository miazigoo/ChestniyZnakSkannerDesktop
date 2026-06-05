"""Probe raw serial scanner bytes with visible separators and timing."""

from __future__ import annotations

import argparse
import string
import sys
import time
from pathlib import Path

import serial

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

TERMINATORS = {b"\r": "<CR>", b"\n": "<LF>", b"\t": "<TAB>"}


def main() -> int:
    """Run a timed serial scanner probe."""

    args = _parse_args()
    deadline = time.monotonic() + args.duration if args.duration > 0 else None
    buffer = bytearray()
    tokens: list[str] = []
    byte_events: list[str] = []
    last_byte_at: float | None = None
    with serial.Serial(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
    ) as stream:
        print(
            f"Listening on {args.port} baudrate={args.baudrate}. " "Scan a code; Ctrl+C to stop.",
            flush=True,
        )
        try:
            while deadline is None or time.monotonic() < deadline:
                chunk = stream.read(args.chunk_size)
                now = time.monotonic()
                if not chunk:
                    if (
                        buffer
                        and last_byte_at is not None
                        and now - last_byte_at >= args.idle_flush
                    ):
                        _flush(buffer, tokens, byte_events, reason="idle")
                    continue
                for byte in chunk:
                    last_byte_at = now
                    item = bytes([byte])
                    label = _byte_label(byte)
                    byte_events.append(f"{byte:02X}:{label}")
                    if item in TERMINATORS:
                        tokens.append(TERMINATORS[item])
                        _flush(buffer, tokens, byte_events, reason=TERMINATORS[item])
                        continue
                    if byte == ord(GS):
                        buffer.extend(item)
                        tokens.append("<GS>")
                        continue
                    buffer.extend(item)
                    tokens.append(label)
        except KeyboardInterrupt:
            pass
    if buffer or tokens:
        _flush(buffer, tokens, byte_events, reason="stop")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=0.1)
    parser.add_argument("--idle-flush", type=float, default=0.9)
    parser.add_argument("--chunk-size", type=int, default=64)
    return parser.parse_args()


def _byte_label(byte: int) -> str:
    if byte == ord(GS):
        return "<GS>"
    char = chr(byte)
    if char in string.printable and char not in "\r\n\t\x0b\x0c":
        return char
    return f"<0x{byte:02X}>"


def _flush(
    buffer: bytearray,
    tokens: list[str],
    byte_events: list[str],
    *,
    reason: str,
) -> None:
    raw = bytes(buffer)
    buffer.clear()
    token_text = "".join(tokens)
    tokens.clear()
    if not raw and not token_text:
        return
    text = raw.decode("latin-1", errors="replace").strip(" \r\n\t")
    print(f"FLUSH reason={reason}")
    print(f"TOKENS {token_text!r}")
    print(f"BYTES {' '.join(byte_events)}")
    byte_events.clear()
    print(f"RAW len={len(text)} visible={visible(text)!r}")
    try:
        parsed = parse_marking_code(text)
    except MarkingCodeParseError as exc:
        print(f"PARSE error={exc}")
    else:
        print(
            "PARSE "
            f"gtin={parsed.gtin} serial_len={len(parsed.serial)} "
            f"serial={parsed.serial!r} ai={parsed.ai_parts}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
