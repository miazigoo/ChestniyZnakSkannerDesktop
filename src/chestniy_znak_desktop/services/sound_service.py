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

    def __init__(
        self,
        enabled: bool = True,
        volume: float = 0.85,
        sound_files: dict[SoundEvent, str] | None = None,
    ) -> None:
        """Создает кеш звуковых эффектов."""

        self._effects: dict[SoundEvent, QSoundEffect] = {}
        self._preview_effects: dict[str, QSoundEffect] = {}
        self._enabled = enabled
        self._volume = max(0.0, min(volume, 1.0))
        self._sound_files = {event: event.value for event in SoundEvent}
        if sound_files is not None:
            self._sound_files.update(sound_files)

    def set_enabled(self, enabled: bool) -> None:
        """Включает или выключает звуковую обратную связь."""

        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        """Устанавливает громкость звуков от 0.0 до 1.0."""

        self._volume = max(0.0, min(volume, 1.0))
        for effect in self._effects.values():
            effect.setVolume(self._volume)
        for effect in self._preview_effects.values():
            effect.setVolume(self._volume)

    def set_sound_file(self, event: SoundEvent, filename: str) -> None:
        """Меняет файл звука для события и сбрасывает кеш эффекта."""

        self._sound_files[event] = filename
        self._effects.pop(event, None)

    def play(self, event: SoundEvent) -> None:
        """Проигрывает звук для указанного события."""

        if not self._enabled:
            return
        self._effect_for_event(event).play()

    def preview_file(self, filename: str) -> None:
        """Проигрывает выбранный файл звука независимо от общей настройки."""

        effect = self._preview_effects.get(filename)
        if effect is None:
            effect = self._create_effect(filename, volume=self._volume)
            self._preview_effects[filename] = effect
        effect.play()

    @staticmethod
    def available_sound_files() -> list[str]:
        """Возвращает список доступных mp3-файлов звуков."""

        return sorted(
            path.name
            for path in files("chestniy_znak_desktop.resources.sounds").iterdir()
            if path.name.endswith(".mp3")
        )

    def _effect_for_event(self, event: SoundEvent) -> QSoundEffect:
        """Возвращает кешированный эффект для события."""

        effect = self._effects.get(event)
        if effect is None:
            effect = self._create_effect(self._sound_files[event], volume=self._volume)
            self._effects[event] = effect
        return effect

    @staticmethod
    def _create_effect(filename: str, volume: float) -> QSoundEffect:
        """Создает Qt-эффект для mp3-файла из ресурсов."""

        path = files("chestniy_znak_desktop.resources.sounds").joinpath(filename)
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(path)))
        effect.setVolume(volume)
        return effect
