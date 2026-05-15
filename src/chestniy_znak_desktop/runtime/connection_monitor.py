"""WebSocket-монитор связи с backend."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWebSockets import QWebSocket

from chestniy_znak_desktop.runtime.state_models import ConnectionState, ConnectionStatus


class ConnectionMonitor(QObject):
    """Следит за WebSocket-соединением и сообщает UI о потере связи."""

    state_changed = Signal(ConnectionState)
    message_received = Signal(str)

    def __init__(
        self,
        websocket_url: str,
        parent: QObject | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Создает монитор для указанного WebSocket URL."""

        super().__init__(parent)
        self._websocket_url = websocket_url
        self._clock = clock or time.monotonic
        self._socket = QWebSocket()
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(5_000)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._open_socket)
        self._base_reconnect_delay_ms = 5_000
        self._max_reconnect_delay_ms = 30_000
        self._current_reconnect_delay_ms = self._base_reconnect_delay_ms
        self._heartbeat_timeout_sec = 45.0
        self._last_inbound_at: float | None = None
        self._started = False
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_text_message)
        self._socket.errorOccurred.connect(self._on_error)

    def start(self) -> None:
        """Открывает WebSocket-соединение с backend."""

        if self._started:
            return
        self._started = True
        self._current_reconnect_delay_ms = self._base_reconnect_delay_ms
        self._emit_state(
            ConnectionState(
                status=ConnectionStatus.CONNECTING,
                message="Подключаемся к серверу...",
            )
        )
        self._open_socket()

    def stop(self) -> None:
        """Останавливает heartbeat и закрывает WebSocket."""

        self._started = False
        self._heartbeat_timer.stop()
        self._reconnect_timer.stop()
        self._socket.close()
        self._emit_state(ConnectionState())

    def retry_now(self) -> None:
        """Принудительно запускает повторное подключение без ожидания таймера."""

        if not self._started:
            self.start()
            return
        self._reconnect_timer.stop()
        self._current_reconnect_delay_ms = self._base_reconnect_delay_ms
        self._socket.abort()
        self._open_socket()

    def send_json(self, payload: dict[str, object]) -> bool:
        """Отправляет JSON-сообщение через активный WebSocket."""

        if self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
            return False
        message = json.dumps(payload, ensure_ascii=False)
        return self._socket.sendTextMessage(message) > 0

    def _open_socket(self) -> None:
        """Открывает WebSocket и переводит монитор в состояние подключения."""

        if not self._started:
            return
        self._emit_state(
            ConnectionState(
                status=ConnectionStatus.CONNECTING,
                message="Подключаемся к серверу...",
            )
        )
        self._socket.open(self._websocket_url)

    def _send_heartbeat(self) -> None:
        """Отправляет heartbeat backend-сервису."""

        if self._last_inbound_at is not None:
            heartbeat_age = self._clock() - self._last_inbound_at
            if heartbeat_age > self._heartbeat_timeout_sec:
                self._mark_disconnected("Нет heartbeat от сервера")
                self._schedule_reconnect()
                return
        self._socket.sendTextMessage('{"type":"heartbeat"}')

    def _on_connected(self) -> None:
        """Обрабатывает успешное подключение WebSocket."""

        self._last_inbound_at = self._clock()
        self._current_reconnect_delay_ms = self._base_reconnect_delay_ms
        self._heartbeat_timer.start()
        self._emit_state(
            ConnectionState(
                status=ConnectionStatus.CONNECTED,
                message="Соединение с сервером активно",
            )
        )

    def _on_disconnected(self) -> None:
        """Обрабатывает закрытие WebSocket-соединения."""

        self._heartbeat_timer.stop()
        if not self._started:
            return
        self._mark_disconnected("Соединение с сервером разорвано")
        self._schedule_reconnect()

    def _on_text_message(self, message: str) -> None:
        """Передает входящее WebSocket-сообщение подписчикам."""

        self._last_inbound_at = self._clock()
        self.message_received.emit(message)
        message_type = self._message_type(message)
        if message_type in {"connected", "heartbeat", "pong"}:
            self._current_reconnect_delay_ms = self._base_reconnect_delay_ms
            self._emit_state(
                ConnectionState(
                    status=ConnectionStatus.CONNECTED,
                    message="Соединение с сервером активно",
                )
            )

    def _on_error(self, error: QAbstractSocket.SocketError) -> None:
        """Преобразует ошибку WebSocket в текст для UI."""

        if not self._started:
            return
        self._mark_disconnected(f"Ошибка WebSocket: {error.name}")
        self._schedule_reconnect()

    def _mark_disconnected(self, message: str) -> None:
        """Переводит монитор в состояние потери связи."""

        self._heartbeat_timer.stop()
        self._socket.abort()
        self._emit_state(
            ConnectionState(
                status=ConnectionStatus.DISCONNECTED,
                message=message,
            )
        )

    def _schedule_reconnect(self) -> None:
        """Планирует повторное подключение с backoff."""

        if not self._started or self._reconnect_timer.isActive():
            return
        delay_ms = self._current_reconnect_delay_ms
        self._emit_state(
            ConnectionState(
                status=ConnectionStatus.DISCONNECTED,
                message=f"Связь потеряна. Автоподключение через {delay_ms // 1000} сек.",
                reconnect_delay_sec=delay_ms // 1000,
            )
        )
        self._reconnect_timer.start(delay_ms)
        self._current_reconnect_delay_ms = min(
            self._current_reconnect_delay_ms * 2,
            self._max_reconnect_delay_ms,
        )

    def _emit_state(self, state: ConnectionState) -> None:
        """Публикует новое состояние подключения."""

        self.state_changed.emit(state)

    @staticmethod
    def _message_type(message: str) -> str:
        """Возвращает `type` из JSON-сообщения WebSocket."""

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return ""
        if not isinstance(payload, dict):
            return ""
        value = payload.get("type", "")
        return str(value)
