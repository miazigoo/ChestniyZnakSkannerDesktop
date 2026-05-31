"""Локальная отправка подготовленных заданий печати."""

from __future__ import annotations

import socket
from typing import Protocol

from chestniy_znak_desktop.api.models.printers import PrintJobDto
from chestniy_znak_desktop.i18n import tr


class PrintTransport(Protocol):
    """Контракт транспорта печати."""

    def send(self, job: PrintJobDto) -> tuple[bool, str]:
        """Отправляет print job и возвращает результат."""


class RawTcpPrintTransport:
    """Отправляет ZPL/TSPL в локально доступный TCP-принтер."""

    def __init__(self, timeout_sec: float = 5.0) -> None:
        """Создает транспорт с сетевым timeout."""

        self._timeout_sec = timeout_sec

    def send(self, job: PrintJobDto) -> tuple[bool, str]:
        """Печатает подготовленный backend payload через raw TCP."""

        if job.transport != "raw_tcp":
            return False, tr("printer.unsupportedTransport", transport=job.transport or "-")
        printer = job.printer
        if printer is None:
            return False, tr("printer.jobMissingPrinter")
        payload = job.payload or ""
        if not payload:
            return False, tr("printer.emptyJob")
        try:
            data = payload.encode(job.encoding or "utf-8")
            with socket.create_connection(
                (printer.ip_address, printer.port),
                timeout=self._timeout_sec,
            ) as sock:
                sock.sendall(data)
        except Exception as exc:
            return False, str(exc)
        return True, ""
