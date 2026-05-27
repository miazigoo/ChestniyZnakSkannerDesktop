"""Тесты общего состояния приложения."""

from __future__ import annotations

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.state_models import SessionStatus


def test_app_state_sets_authenticated_user() -> None:
    """Проверяет установку авторизованного пользователя."""

    state = AppState(config=AppConfig())
    state.set_authenticated_user(
        "Operator",
        plant_id="plant-1",
        device_id="device-1",
    )
    assert state.current_user_name == "Operator"
    assert state.session.status == SessionStatus.AUTHENTICATED
    assert state.session.plant_id == "plant-1"
    assert state.session.device_id == "device-1"


def test_app_state_clears_user() -> None:
    """Проверяет сброс пользовательской сессии."""

    state = AppState(config=AppConfig())
    state.set_authenticated_user("Operator")
    state.clear_user()
    assert state.current_user_name == ""
    assert state.session.status == SessionStatus.UNAUTHENTICATED
