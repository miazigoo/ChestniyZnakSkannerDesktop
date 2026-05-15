"""Тесты настройки файлового логирования."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from chestniy_znak_desktop.app.logging_config import configure_logging


def test_configure_logging_uses_one_day_rotation(
    tmp_path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    """Проверяет ротацию desktop.log в пределах суток."""

    captured: dict[str, Any] = {}

    def fake_basic_config(**kwargs: Any) -> None:
        """Запоминает параметры logging.basicConfig."""

        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    configure_logging(tmp_path)

    file_handler = next(
        handler for handler in captured["handlers"] if isinstance(handler, TimedRotatingFileHandler)
    )

    assert file_handler.when == "H"
    assert file_handler.interval == 60 * 60
    assert file_handler.backupCount == 23
    file_handler.close()
