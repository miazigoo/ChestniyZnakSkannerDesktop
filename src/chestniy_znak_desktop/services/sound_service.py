"""Сервис звуковой обратной связи."""

from __future__ import annotations

from enum import Enum
from importlib.resources import files

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect


class SoundEvent(str, Enum):
    """События, для которых приложение проигрывает звук."""

    OK = "ok_02.mp3"
    ERROR = "error.mp3"
    WARNING = "other.mp3"
    VICTORY = "victory.mp3"


class SoundService:
    """Проигрывает короткие звуковые сигналы оператору."""

    def __init__(self, enabled: bool = True, volume: float = 0.85) -> None:
        """Создает кеш звуковых эффектов."""

        self._effects: dict[SoundEvent, QSoundEffect] = {}
        self._enabled = enabled
        self._volume = max(0.0, min(volume, 1.0))

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает звуковую обратную связь."""

        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        """Устанавливает громкость звуков от 0.0 до 1.0."""

        self._volume = max(0.0, min(volume, 1.0))
        for effect in self._effects.values():
            effect.setVolume(self._volume)

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""

        if not self._enabled:
            return
        effect = self._effects.get(event)
        if effect is None:
            effect = self._create_effect(event, volume=self._volume)
            self._effects[event] = effect
        effect.play()

    @staticmethod
    def _create_effect(event: SoundEvent, volume: float) -> QSoundEffect:
        """Создает Qt-эффект для mp3-файла из ресурсов."""

        path = files("chestniy_znak_desktop.resources.sounds").joinpath(event.value)
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(path)))
        effect.setVolume(volume)
        return effect
