"""Тесты сервиса звуковой обратной связи."""

from __future__ import annotations

from typing import Any

import pytest

from chestniy_znak_desktop.services.sound_service import SoundEvent, SoundService


class FakeProcess:
    """Fake external audio process."""

    def __init__(self, running: bool = False) -> None:
        """Создает fake-процесс."""

        self._running = running

    def poll(self) -> int | None:
        """Возвращает статус процесса."""

        return None if self._running else 0


class FakeProcessFactory:
    """Запоминает команды запуска внешнего проигрывателя."""

    def __init__(self) -> None:
        """Создает recorder запусков."""

        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> FakeProcess:
        """Запоминает запуск и возвращает завершенный fake-процесс."""

        self.calls.append((command, kwargs))
        return FakeProcess()


def _service(
    enabled: bool = True,
    volume: float = 0.85,
    process_factory: FakeProcessFactory | None = None,
) -> tuple[SoundService, FakeProcessFactory]:
    """Создает SoundService с fake external player."""

    factory = process_factory or FakeProcessFactory()
    return (
        SoundService(
            enabled=enabled,
            volume=volume,
            process_factory=factory,  # type: ignore[arg-type]
            player_command=["player", "--quiet"],
        ),
        factory,
    )


def test_sound_service_plays_event_mp3_with_external_player() -> None:
    """Проверяет запуск звука события внешним процессом."""

    service, factory = _service(volume=0.4)

    service.play(SoundEvent.OK)

    assert len(factory.calls) == 1
    command, kwargs = factory.calls[0]
    assert command[:2] == ["player", "--quiet"]
    assert command[-1].endswith("/ok_02.mp3")
    assert kwargs["start_new_session"] is True


def test_sound_service_preview_plays_selected_file() -> None:
    """Проверяет прослушивание выбранного mp3-файла."""

    service, factory = _service()

    service.preview_file("error_02.mp3")

    assert factory.calls[0][0][-1].endswith("/error_02.mp3")


def test_sound_service_disabled_does_not_play_events() -> None:
    """Проверяет отключение звуков событий."""

    service, factory = _service(enabled=False)

    service.play(SoundEvent.ERROR)

    assert factory.calls == []


def test_sound_service_skips_while_same_sound_is_running() -> None:
    """Проверяет защиту от пачки внешних процессов на быстром потоке сканов."""

    factory = FakeProcessFactory()
    service, _factory = _service(process_factory=factory)

    service.play(SoundEvent.OK)
    service._playbacks[SoundEvent.OK].process = FakeProcess(running=True)  # noqa: SLF001
    service.play(SoundEvent.OK)

    assert len(factory.calls) == 1


def test_sound_service_set_volume_keeps_public_contract() -> None:
    """Проверяет, что настройка громкости не требует Qt audio output."""

    service, factory = _service(volume=0.2)
    service.set_volume(0.7)

    service.play(SoundEvent.WARNING)

    assert len(factory.calls) == 1


def test_sound_service_detects_pipewire_player(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет fallback на стандартный Linux PipeWire player."""

    monkeypatch.setattr(
        "chestniy_znak_desktop.services.sound_service.shutil.which",
        lambda binary: "/usr/bin/pw-play" if binary == "pw-play" else None,
    )
    factory = FakeProcessFactory()
    service = SoundService(volume=0.55, process_factory=factory)  # type: ignore[arg-type]

    service.play(SoundEvent.OK)

    command = factory.calls[0][0]
    assert command[:3] == ["pw-play", "--volume", "0.55"]
