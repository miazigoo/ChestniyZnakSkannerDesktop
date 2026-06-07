"""Общие pytest-настройки проекта."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from chestniy_znak_desktop.i18n import DEFAULT_LANGUAGE, set_current_language


@pytest.fixture(autouse=True)
def reset_i18n_language() -> Iterator[None]:
    """Изолирует тесты от глобального языка приложения."""

    set_current_language(DEFAULT_LANGUAGE)
    yield
    set_current_language(DEFAULT_LANGUAGE)
