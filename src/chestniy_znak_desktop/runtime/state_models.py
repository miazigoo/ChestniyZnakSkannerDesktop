"""Типизированные модели runtime-состояния приложения."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConnectionStatus(str, Enum):
    """Состояние WebSocket-связи с backend."""

    STOPPED = "stopped"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class SessionStatus(str, Enum):
    """Состояние пользовательской сессии."""

    UNKNOWN = "unknown"
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"


class ScannerStatus(str, Enum):
    """Состояние источника сканов."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ConnectionState:
    """Снимок состояния WebSocket-соединения."""

    status: ConnectionStatus = ConnectionStatus.STOPPED
    message: str = "Монитор связи остановлен"
    reconnect_delay_sec: int = 0
    heartbeat_age_sec: int = 0

    @property
    def is_connected(self) -> bool:
        """Возвращает `True`, если связь с backend активна."""

        return self.status == ConnectionStatus.CONNECTED

    @property
    def is_blocking(self) -> bool:
        """Возвращает `True`, если рабочие действия нужно блокировать."""

        return self.status in {ConnectionStatus.CONNECTING, ConnectionStatus.DISCONNECTED}


@dataclass(frozen=True, slots=True)
class SessionState:
    """Снимок состояния пользовательской сессии."""

    status: SessionStatus = SessionStatus.UNKNOWN
    user_name: str = ""
    plant_id: str = ""
    device_id: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    plant_name: str = ""
    client_device_id: str = ""
    subscription_status: str = ""

    @property
    def is_authenticated(self) -> bool:
        """Возвращает `True`, если пользователь авторизован."""

        return self.status == SessionStatus.AUTHENTICATED


@dataclass(frozen=True, slots=True)
class ScannerState:
    """Снимок состояния подключенного сканера."""

    status: ScannerStatus = ScannerStatus.STOPPED
    port: str = ""
    message: str = "Сканер не запущен"

    @property
    def is_running(self) -> bool:
        """Возвращает `True`, если сканер читает порт."""

        return self.status == ScannerStatus.RUNNING


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Общий снимок runtime-состояния приложения."""

    connection: ConnectionState = ConnectionState()
    session: SessionState = SessionState()
    scanner: ScannerState = ScannerState()

    @property
    def is_blocking(self) -> bool:
        """Возвращает `True`, если UI должен блокировать рабочие операции."""

        return self.connection.is_blocking or not self.session.is_authenticated
