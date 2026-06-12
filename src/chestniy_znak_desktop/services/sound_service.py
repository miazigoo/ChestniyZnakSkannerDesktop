"""Сервис звуковой обратной связи без QtMultimedia."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_SOUND_INTERVAL_SEC = 0.08


class SoundEvent(str, Enum):
    """События, для которых приложение проигрывает звук."""

    OK = "ok_02.mp3"
    ERROR = "error.mp3"
    WARNING = "other.mp3"
    VICTORY = "victory.mp3"


@dataclass(slots=True)
class SoundPlayback:
    """Состояние внешнего проигрывания одного звукового файла."""

    path: Path
    command: list[str]
    process: subprocess.Popen[bytes] | None = None
    last_started_at: float = 0.0


ProcessFactory = Callable[..., subprocess.Popen[bytes]]


class SoundService:
    """Проигрывает короткие звуковые сигналы оператору.

    Runtime-звуки специально не используют QtMultimedia: на Linux/Wayland FFmpeg backend
    может падать native segfault и уронить всё приложение после серии сканов.
    """

    def __init__(
        self,
        enabled: bool = True,
        volume: float = 0.85,
        sound_files: dict[SoundEvent, str] | None = None,
        process_factory: ProcessFactory = subprocess.Popen,
        player_command: list[str] | None = None,
    ) -> None:
        """Создает сервис внешнего проигрывания коротких mp3."""

        self._playbacks: dict[SoundEvent, SoundPlayback] = {}
        self._preview_playbacks: dict[str, SoundPlayback] = {}
        self._enabled = enabled
        self._volume = max(0.0, min(volume, 1.0))
        self._sound_files = {event: event.value for event in SoundEvent}
        self._process_factory = process_factory
        self._player_command = player_command or self._detect_player_command()
        if sound_files is not None:
            self._sound_files.update(sound_files)

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает звуковую обратную связь."""

        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        """Сохраняет громкость звуков от 0.0 до 1.0."""

        self._volume = max(0.0, min(volume, 1.0))
        self._playbacks.clear()
        self._preview_playbacks.clear()

    def set_sound_file(self, event: SoundEvent, filename: str) -> None:
        """Меняет файл звука для события и сбрасывает кеш плеера."""

        self._sound_files[event] = filename
        self._playbacks.pop(event, None)

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""

        if not self._enabled:
            return
        self._play(self._playback_for_event(event))

    def preview_file(self, filename: str) -> None:
        """Проигрывает выбранный файл звука независимо от общей настройки."""

        playback = self._preview_playbacks.get(filename)
        if playback is None:
            playback = self._create_playback(filename)
            self._preview_playbacks[filename] = playback
        self._play(playback, force=True)

    @staticmethod
    def available_sound_files() -> list[str]:
        """Возвращает список доступных mp3-файлов звуков."""

        return sorted(
            path.name
            for path in files("chestniy_znak_desktop.resources.sounds").iterdir()
            if path.name.endswith(".mp3")
        )

    def _playback_for_event(self, event: SoundEvent) -> SoundPlayback:
        """Возвращает кешированный playback для события."""

        playback = self._playbacks.get(event)
        if playback is None:
            playback = self._create_playback(self._sound_files[event])
            self._playbacks[event] = playback
        return playback

    def _create_playback(self, filename: str) -> SoundPlayback:
        """Создает описание внешнего запуска mp3-файла из ресурсов."""

        path = files("chestniy_znak_desktop.resources.sounds").joinpath(filename)
        return SoundPlayback(
            path=Path(str(path)),
            command=self._build_command_for_path(str(path)),
        )

    def _build_command_for_path(self, path: str) -> list[str]:
        """Собирает команду проигрывания с учетом возможностей выбранного плеера."""

        if not self._player_command:
            return []
        if self._player_command[0] == "pw-play":
            return [*self._player_command, "--volume", f"{self._volume:.2f}", path]
        return [*self._player_command, path]

    def _play(self, playback: SoundPlayback, *, force: bool = False) -> None:
        """Запускает внешний проигрыватель, не блокируя UI."""

        if not playback.command:
            return
        now = time.monotonic()
        if not force and now - playback.last_started_at < MIN_SOUND_INTERVAL_SEC:
            return
        if playback.process is not None and playback.process.poll() is None:
            return
        playback.last_started_at = now
        try:
            playback.process = self._process_factory(
                playback.command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            logger.warning("Не удалось воспроизвести звук %s: %s", playback.path.name, exc)

    @staticmethod
    def _detect_player_command() -> list[str]:
        """Возвращает безопасный внешний проигрыватель, если он установлен."""

        candidates = (
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("mpg123", ["mpg123", "-q"]),
            ("pw-play", ["pw-play"]),
            ("play", ["play", "-q"]),
            ("cvlc", ["cvlc", "--play-and-exit", "--quiet"]),
        )
        for binary, command in candidates:
            if shutil.which(binary):
                return command
        logger.warning("Звуковой проигрыватель не найден; звуки Desktop отключены.")
        return []
