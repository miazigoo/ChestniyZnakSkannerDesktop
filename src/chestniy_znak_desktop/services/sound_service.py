"""Сервис звуковой обратной связи."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

logger = logging.getLogger(__name__)


class SoundEvent(str, Enum):
    """События, для которых приложение проигрывает звук."""

    OK = "ok_02.mp3"
    ERROR = "error.mp3"
    WARNING = "other.mp3"
    VICTORY = "victory.mp3"


@dataclass(slots=True)
class SoundPlayback:
    """Связка media-player и audio-output для одного звука."""

    player: QMediaPlayer
    audio_output: QAudioOutput


class SoundService:
    """Проигрывает короткие звуковые сигналы оператору."""

    def __init__(
        self,
        enabled: bool = True,
        volume: float = 0.85,
        sound_files: dict[SoundEvent, str] | None = None,
        player_factory: Callable[[], QMediaPlayer] = QMediaPlayer,
        audio_output_factory: Callable[[], QAudioOutput] = QAudioOutput,
    ) -> None:
        """Создает кеш MP3-плееров для звуковых эффектов."""

        self._playbacks: dict[SoundEvent, SoundPlayback] = {}
        self._preview_playbacks: dict[str, SoundPlayback] = {}
        self._enabled = enabled
        self._volume = max(0.0, min(volume, 1.0))
        self._sound_files = {event: event.value for event in SoundEvent}
        self._player_factory = player_factory
        self._audio_output_factory = audio_output_factory
        if sound_files is not None:
            self._sound_files.update(sound_files)

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает звуковую обратную связь."""

        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        """Устанавливает громкость звуков от 0.0 до 1.0."""

        self._volume = max(0.0, min(volume, 1.0))
        for playback in self._playbacks.values():
            playback.audio_output.setVolume(self._volume)
        for playback in self._preview_playbacks.values():
            playback.audio_output.setVolume(self._volume)

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
            playback = self._create_playback(filename, volume=self._volume)
            self._preview_playbacks[filename] = playback
        self._play(playback)

    @staticmethod
    def available_sound_files() -> list[str]:
        """Возвращает список доступных mp3-файлов звуков."""

        return sorted(
            path.name
            for path in files("chestniy_znak_desktop.resources.sounds").iterdir()
            if path.name.endswith(".mp3")
        )

    def _playback_for_event(self, event: SoundEvent) -> SoundPlayback:
        """Возвращает кешированный плеер для события."""

        playback = self._playbacks.get(event)
        if playback is None:
            playback = self._create_playback(self._sound_files[event], volume=self._volume)
            self._playbacks[event] = playback
        return playback

    def _create_playback(self, filename: str, volume: float) -> SoundPlayback:
        """Создает Qt media-player для mp3-файла из ресурсов."""

        path = files("chestniy_znak_desktop.resources.sounds").joinpath(filename)
        player = self._player_factory()
        audio_output = self._audio_output_factory()
        audio_output.setVolume(volume)
        player.setAudioOutput(audio_output)
        player.setSource(QUrl.fromLocalFile(str(path)))
        player.errorOccurred.connect(
            lambda _error, message, filename=filename: self._log_player_error(
                filename,
                message,
            )
        )
        return SoundPlayback(player=player, audio_output=audio_output)

    @staticmethod
    def _play(playback: SoundPlayback) -> None:
        """Запускает звук с начала файла."""

        playback.player.setPosition(0)
        playback.player.play()

    @staticmethod
    def _log_player_error(filename: str, message: str) -> None:
        """Пишет в лог ошибку Qt Multimedia."""

        logger.warning("Не удалось воспроизвести звук %s: %s", filename, message)
