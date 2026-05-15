"""Тесты сервиса звуковой обратной связи."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QUrl

from chestniy_znak_desktop.services.sound_service import SoundEvent, SoundService


class FakeSignal:
    """Минимальный fake Qt-сигнала."""

    def __init__(self) -> None:
        """Создает список подключенных callback."""

        self.callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        """Запоминает callback сигнала."""

        self.callbacks.append(callback)


class FakeAudioOutput:
    """Fake audio-output для проверки громкости."""

    instances: list["FakeAudioOutput"] = []

    def __init__(self) -> None:
        """Создает fake audio-output."""

        self.volume = 0.0
        self.instances.append(self)

    def setVolume(self, volume: float) -> None:  # noqa: N802
        """Запоминает громкость в Qt-совместимом методе."""

        self.volume = volume


class FakePlayer:
    """Fake media-player для проверки запуска звука."""

    instances: list["FakePlayer"] = []

    def __init__(self) -> None:
        """Создает fake media-player."""

        self.audio_output: FakeAudioOutput | None = None
        self.source = QUrl()
        self.positions: list[int] = []
        self.play_count = 0
        self.errorOccurred = FakeSignal()
        self.instances.append(self)

    def setAudioOutput(self, audio_output: FakeAudioOutput) -> None:  # noqa: N802
        """Запоминает audio-output в Qt-совместимом методе."""

        self.audio_output = audio_output

    def setSource(self, source: QUrl) -> None:  # noqa: N802
        """Запоминает source в Qt-совместимом методе."""

        self.source = source

    def setPosition(self, position: int) -> None:  # noqa: N802
        """Запоминает позицию старта в Qt-совместимом методе."""

        self.positions.append(position)

    def play(self) -> None:
        """Запоминает запуск проигрывания."""

        self.play_count += 1


def _service(enabled: bool = True, volume: float = 0.85) -> SoundService:
    """Создает SoundService с fake multimedia объектами."""

    FakePlayer.instances = []
    FakeAudioOutput.instances = []
    return SoundService(
        enabled=enabled,
        volume=volume,
        player_factory=FakePlayer,  # type: ignore[arg-type]
        audio_output_factory=FakeAudioOutput,  # type: ignore[arg-type]
    )


def test_sound_service_plays_event_mp3_with_media_player() -> None:
    """Проверяет запуск звука события через media-player."""

    service = _service(volume=0.4)

    service.play(SoundEvent.OK)

    player = FakePlayer.instances[0]
    assert player.play_count == 1
    assert player.positions == [0]
    assert player.source.toLocalFile().endswith("/ok_02.mp3")
    assert player.audio_output is not None
    assert player.audio_output.volume == 0.4


def test_sound_service_preview_plays_selected_file() -> None:
    """Проверяет прослушивание выбранного mp3-файла."""

    service = _service()

    service.preview_file("error_02.mp3")

    player = FakePlayer.instances[0]
    assert player.play_count == 1
    assert player.source.toLocalFile().endswith("/error_02.mp3")


def test_sound_service_disabled_does_not_play_events() -> None:
    """Проверяет отключение звуков событий."""

    service = _service(enabled=False)

    service.play(SoundEvent.ERROR)

    assert FakePlayer.instances == []


def test_sound_service_updates_cached_player_volume() -> None:
    """Проверяет обновление громкости у уже созданных плееров."""

    service = _service(volume=0.2)
    service.play(SoundEvent.OK)
    service.preview_file("error.mp3")

    service.set_volume(0.7)

    assert [audio.volume for audio in FakeAudioOutput.instances] == [0.7, 0.7]
