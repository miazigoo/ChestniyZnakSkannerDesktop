"""Файловые хранилища HTTP-сессии."""

from __future__ import annotations

import json
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class BearerSession:
    """Bearer-токены SaaS app-сессии."""

    access_token: str
    refresh_token: str


class FileBearerTokenStore:
    """Хранит bearer-токены SaaS app-сессии в JSON-файле."""

    def __init__(self, path: Path) -> None:
        """Запоминает путь к JSON-файлу сессии."""

        self._path = path

    def load(self) -> BearerSession | None:
        """Загружает bearer-сессию или возвращает `None`."""

        if not self._path.exists():
            return None
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        access_token = str(payload.get("access_token") or "")
        refresh_token = str(payload.get("refresh_token") or "")
        if not access_token or not refresh_token:
            return None
        return BearerSession(access_token=access_token, refresh_token=refresh_token)

    def save(self, session: BearerSession) -> None:
        """Сохраняет bearer-сессию."""

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(
                {
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Удаляет файл bearer-сессии."""

        self._path.unlink(missing_ok=True)
