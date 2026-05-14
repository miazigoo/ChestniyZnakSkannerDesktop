"""Тесты моделей runtime-состояния."""

from __future__ import annotations

from chestniy_znak_desktop.runtime.state_models import (
    ConnectionState,
    ConnectionStatus,
    RuntimeSnapshot,
    ScannerState,
    ScannerStatus,
    SessionState,
    SessionStatus,
)


def test_connection_state_marks_connecting_as_blocking() -> None:
    """Проверяет блокировку UI во время подключения."""

    state = ConnectionState(status=ConnectionStatus.CONNECTING)
    assert state.is_blocking is True
    assert state.is_connected is False


def test_runtime_snapshot_blocks_without_auth_session() -> None:
    """Проверяет блокировку рабочих действий без авторизации."""

    snapshot = RuntimeSnapshot(
        connection=ConnectionState(status=ConnectionStatus.CONNECTED),
        session=SessionState(status=SessionStatus.UNAUTHENTICATED),
        scanner=ScannerState(status=ScannerStatus.RUNNING, port="COM7"),
    )
    assert snapshot.is_blocking is True


def test_runtime_snapshot_allows_work_when_connected_and_authenticated() -> None:
    """Проверяет рабочее состояние без блокировки."""

    snapshot = RuntimeSnapshot(
        connection=ConnectionState(status=ConnectionStatus.CONNECTED),
        session=SessionState(status=SessionStatus.AUTHENTICATED, user_name="operator"),
        scanner=ScannerState(status=ScannerStatus.RUNNING, port="COM7"),
    )
    assert snapshot.is_blocking is False
