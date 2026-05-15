"""Сервис чтения диагностических логов."""

from __future__ import annotations

from collections import deque
from pathlib import Path


class LogService:
    """Читает последние строки файла логов приложения."""

    def __init__(self, log_file: Path) -> None:
        """Сохраняет путь к файлу логов."""

        self._log_file = log_file

    @property
    def log_file(self) -> Path:
        """Возвращает путь к файлу логов."""

        return self._log_file

    def tail(self, max_lines: int = 200) -> str:
        """Возвращает последние строки лог-файла."""

        if not self._log_file.exists():
            return "Лог-файл еще не создан"
        with self._log_file.open("r", encoding="utf-8", errors="replace") as file:
            lines = deque(file, maxlen=max_lines)
        return "".join(lines).rstrip()

    def clear(self) -> None:
        """Очищает лог-файл приложения."""

        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._log_file.write_text("", encoding="utf-8")
