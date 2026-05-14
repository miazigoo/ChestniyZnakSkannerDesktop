"""Базовые типы слоя сканера."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    """Настройки подключения к COM/SPP-сканеру."""

    port: str
    baudrate: int = 9600
    timeout_sec: float = 0.1
    idle_flush_sec: float = 0.25
    dedupe_window_sec: float = 0.75
    encoding: str = "latin-1"
    terminators: tuple[bytes, ...] = (b"\r", b"\n", b"\t")


@dataclass(frozen=True, slots=True)
class ScannerPort:
    """Описывает один доступный serial-порт."""

    device: str
    description: str
    hwid: str = ""

    @property
    def title(self) -> str:
        """Возвращает текст для отображения в UI."""

        if self.description and self.description != self.device:
            return f"{self.device} - {self.description}"
        return self.device


class ScannerInput(Protocol):
    """Контракт источника строк от сканера."""

    def start(self) -> None:
        """Запускает чтение сканера."""

    def stop(self) -> None:
        """Останавливает чтение сканера."""
