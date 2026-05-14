"""Тесты сборщика сканов из байтового потока."""

from __future__ import annotations

from chestniy_znak_desktop.scanner.scan_assembler import ScanAssembler, ScanAssemblerConfig


class FakeClock:
    """Управляемые часы для проверки таймаутов."""

    def __init__(self) -> None:
        """Создает часы с нулевым временем."""

        self.value = 0.0

    def __call__(self) -> float:
        """Возвращает текущее тестовое время."""

        return self.value

    def advance(self, seconds: float) -> None:
        """Сдвигает тестовое время вперед."""

        self.value += seconds


def test_assembler_emits_code_on_terminator() -> None:
    """Проверяет выдачу кода после CR-терминатора."""

    clock = FakeClock()
    assembler = ScanAssembler(ScanAssemblerConfig(), clock=clock)
    assert assembler.feed(b"010460") == []
    assert assembler.feed(b"\r") == ["010460"]


def test_assembler_emits_multiple_codes_from_one_chunk() -> None:
    """Проверяет несколько кодов в одном байтовом фрагменте."""

    assembler = ScanAssembler(ScanAssemblerConfig())
    assert assembler.feed(b"CODE1\rCODE2\n") == ["CODE1", "CODE2"]


def test_assembler_deduplicates_fast_repeat() -> None:
    """Проверяет подавление быстрого дубля одного и того же кода."""

    clock = FakeClock()
    assembler = ScanAssembler(ScanAssemblerConfig(dedupe_window_sec=0.75), clock=clock)
    assert assembler.feed(b"CODE\r") == ["CODE"]
    clock.advance(0.2)
    assert assembler.feed(b"CODE\r") == []
    clock.advance(0.8)
    assert assembler.feed(b"CODE\r") == ["CODE"]


def test_assembler_flushes_code_after_idle_without_terminator() -> None:
    """Проверяет выдачу кода по idle-таймауту без терминатора."""

    clock = FakeClock()
    assembler = ScanAssembler(ScanAssemblerConfig(idle_flush_sec=0.25), clock=clock)
    assembler.feed(b"CODE")
    clock.advance(0.1)
    assert assembler.flush_if_idle() is None
    clock.advance(0.2)
    assert assembler.flush_if_idle() == "CODE"


def test_assembler_clears_stale_partial_buffer() -> None:
    """Проверяет очистку старого незавершенного буфера."""

    clock = FakeClock()
    assembler = ScanAssembler(ScanAssemblerConfig(idle_flush_sec=0.25), clock=clock)
    assembler.feed(b"OLD")
    clock.advance(0.3)
    assert assembler.feed(b"NEW\r") == ["NEW"]
