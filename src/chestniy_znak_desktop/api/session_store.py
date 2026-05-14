"""Файловое хранилище HTTP cookies."""

from __future__ import annotations

from http.cookiejar import LoadError, MozillaCookieJar
from pathlib import Path


class FileCookieStore:
    """Загружает и сохраняет cookies сессии в формате Mozilla."""

    def __init__(self, path: Path) -> None:
        """Запоминает путь к cookie-файлу."""

        self._path = path

    def load(self) -> MozillaCookieJar:
        """Загружает cookie jar или возвращает пустое хранилище."""

        jar = MozillaCookieJar(str(self._path))
        if not self._path.exists():
            return jar
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except (LoadError, OSError):
            return MozillaCookieJar(str(self._path))
        return jar

    def save(self, jar: MozillaCookieJar) -> None:
        """Сохраняет cookies на диск."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        jar.save(ignore_discard=True, ignore_expires=True)

    def clear(self) -> None:
        """Удаляет cookie-файл с диска."""

        self._path.unlink(missing_ok=True)
