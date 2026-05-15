"""WebSocket-сервис проверки кодов для автосканерной упаковки."""

from __future__ import annotations

import json
from uuid import uuid4

from pydantic import ValidationError
from PySide6.QtCore import QObject, QTimer, Signal

from chestniy_znak_desktop.api.models.verify import VerifyExistsResponseDto
from chestniy_znak_desktop.runtime.connection_monitor import ConnectionMonitor


class AutoPackWsVerifier(QObject):
    """Отправляет проверки автоскана по WS и сопоставляет ответы с запросами."""

    verified = Signal(str, str, object)
    failed = Signal(str, str, str)

    def __init__(
        self,
        connection_monitor: ConnectionMonitor,
        timeout_ms: int = 7_000,
        parent: QObject | None = None,
    ) -> None:
        """Создает WS-verifier поверх общего монитора соединения."""

        super().__init__(parent)
        self._connection_monitor = connection_monitor
        self._timeout_ms = timeout_ms
        self._pending_codes: dict[str, str] = {}
        self._timers: dict[str, QTimer] = {}
        self._connection_monitor.message_received.connect(self._on_message)

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
    ) -> str | None:
        """Отправляет WS-запрос проверки и возвращает request_id."""

        request_id = uuid4().hex
        payload: dict[str, object] = {
            "type": "auto_pack_verify",
            "request_id": request_id,
            "code": code,
            "scanner_id": scanner_id,
            "allow_duplicate": allow_duplicate,
            "save_scan": True,
        }
        if not self._connection_monitor.send_json(payload):
            return None
        self._pending_codes[request_id] = code
        self._start_timeout(request_id)
        return request_id

    def _on_message(self, message: str) -> None:
        """Разбирает входящие WS-сообщения проверки автоскана."""

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict) or payload.get("type") != "auto_pack_verify_result":
            return
        request_id = str(payload.get("request_id") or "")
        if request_id not in self._pending_codes:
            return
        raw_code = self._pending_codes.pop(request_id)
        self._stop_timeout(request_id)
        error = str(payload.get("error") or "")
        if error:
            self.failed.emit(request_id, raw_code, error)
            return
        result_payload = payload.get("result")
        if not isinstance(result_payload, dict):
            self.failed.emit(request_id, raw_code, "Backend вернул пустой WS-ответ")
            return
        try:
            result = VerifyExistsResponseDto.model_validate(result_payload)
        except ValidationError as exc:
            self.failed.emit(request_id, raw_code, f"Некорректный WS-ответ: {exc}")
            return
        self.verified.emit(request_id, raw_code, result)

    def _start_timeout(self, request_id: str) -> None:
        """Запускает таймер ожидания ответа backend."""

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(self._timeout_ms)
        timer.timeout.connect(lambda: self._on_timeout(request_id))
        self._timers[request_id] = timer
        timer.start()

    def _stop_timeout(self, request_id: str) -> None:
        """Останавливает таймер завершенного WS-запроса."""

        timer = self._timers.pop(request_id, None)
        if timer is None:
            return
        timer.stop()
        timer.deleteLater()

    def _on_timeout(self, request_id: str) -> None:
        """Сообщает о таймауте WS-проверки."""

        raw_code = self._pending_codes.pop(request_id, "")
        self._stop_timeout(request_id)
        if raw_code:
            self.failed.emit(request_id, raw_code, "Backend не ответил по WS")
