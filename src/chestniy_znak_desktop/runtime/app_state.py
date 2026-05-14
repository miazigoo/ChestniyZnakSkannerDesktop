"""Глобальное состояние desktop-приложения."""

from __future__ import annotations

from dataclasses import dataclass

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.runtime.state_models import (
    ConnectionState,
    RuntimeSnapshot,
    ScannerState,
    SessionState,
    SessionStatus,
)


@dataclass(slots=True)
class AppState:
    """Хранит состояние, общее для UI и runtime-сервисов."""

    config: AppConfig
    connection: ConnectionState = ConnectionState()
    session: SessionState = SessionState()
    scanner: ScannerState = ScannerState()

    @property
    def is_connected(self) -> bool:
        """Возвращает `True`, если backend-соединение активно."""

        return self.connection.is_connected

    @property
    def current_user_name(self) -> str:
        """Возвращает имя текущего пользователя для UI."""

        return self.session.user_name

    @property
    def snapshot(self) -> RuntimeSnapshot:
        """Возвращает неизменяемый снимок runtime-состояния."""

        return RuntimeSnapshot(
            connection=self.connection,
            session=self.session,
            scanner=self.scanner,
        )

    def set_authenticated_user(self, user_name: str) -> None:
        """Помечает текущую сессию как авторизованную."""

        self.session = SessionState(status=SessionStatus.AUTHENTICATED, user_name=user_name)

    def clear_user(self) -> None:
        """Сбрасывает текущую пользовательскую сессию."""

        self.session = SessionState(status=SessionStatus.UNAUTHENTICATED)
