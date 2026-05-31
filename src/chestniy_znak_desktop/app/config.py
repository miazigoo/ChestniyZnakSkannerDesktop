"""Конфигурация desktop-приложения."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Хранит базовые настройки запуска desktop-клиента."""

    api_base_url: str = "https://api.chestniy-z.ru/api/v1/"
    device_id: str = "DESKTOP-CHZ-01"
    app_name: str = "Честный знак Desktop"
    organization_name: str = "DevAndProd"
    data_dir: Path = Path.home() / ".chestniy_znak_desktop"
    request_timeout_sec: float = 40.0

    @property
    def websocket_url(self) -> str:
        """Возвращает URL WebSocket-монитора для текущего backend."""

        base = self.api_base_url.rstrip("/")
        if base.startswith("https://"):
            host = base.removeprefix("https://").split("/")[0]
            scheme = "wss"
        else:
            host = base.removeprefix("http://").split("/")[0]
            scheme = "ws"
        return f"{scheme}://{host}/ws/chestniy-znak/client/?device_id={self.device_id}"


def load_app_config() -> AppConfig:
    """Создает конфигурацию приложения из значений по умолчанию."""

    return AppConfig()
