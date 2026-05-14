"""Сборка байтов serial-потока в строки DataMatrix."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanAssemblerConfig:
    """Настройки сборщика одного скана из байтового потока."""

    encoding: str = "latin-1"
    idle_flush_sec: float = 0.25
    dedupe_window_sec: float = 0.75
    terminators: tuple[bytes, ...] = (b"\r", b"\n", b"\t")


class ScanAssembler:
    """Преобразует поток байтов сканера в готовые строки кодов."""

    def __init__(
        self,
        config: ScanAssemblerConfig,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Создает сборщик с настройками и источником времени."""

        self._config = config
        self._clock = clock or time.monotonic
        self._buffer = bytearray()
        self._last_byte_at: float | None = None
        self._last_emitted_code = ""
        self._last_emitted_at = 0.0

    def feed(self, chunk: bytes) -> list[str]:
        """Добавляет байты и возвращает все завершенные коды."""

        now = self._clock()
        if (
            self._last_byte_at is not None
            and now - self._last_byte_at > self._config.idle_flush_sec
        ):
            self._buffer.clear()
        self._last_byte_at = now

        emitted: list[str] = []
        for byte in chunk:
            current = bytes([byte])
            if current in self._config.terminators:
                code = self._emit_buffer(now)
                if code is not None:
                    emitted.append(code)
                continue
            self._buffer.extend(current)
        return emitted

    def flush_if_idle(self) -> str | None:
        """Возвращает код без терминатора, если поток долго молчит."""

        if not self._buffer or self._last_byte_at is None:
            return None
        now = self._clock()
        if now - self._last_byte_at < self._config.idle_flush_sec:
            return None
        return self._emit_buffer(now)

    def reset(self) -> None:
        """Очищает буфер текущего незавершенного скана."""

        self._buffer.clear()
        self._last_byte_at = None

    def _emit_buffer(self, now: float) -> str | None:
        """Декодирует буфер, применяет trim и дедупликацию."""

        if not self._buffer:
            return None
        code = self._buffer.decode(self._config.encoding, errors="replace").strip(" \r\n\t")
        self._buffer.clear()
        if not code:
            return None
        if (
            code == self._last_emitted_code
            and now - self._last_emitted_at < self._config.dedupe_window_sec
        ):
            return None
        self._last_emitted_code = code
        self._last_emitted_at = now
        return code
