"""Тесты конфигурации приложения."""

from __future__ import annotations

from chestniy_znak_desktop.app.config import AppConfig


def test_websocket_url_is_built_from_http_base_url() -> None:
    """Проверяет сборку ws URL из HTTP base URL."""

    config = AppConfig(api_base_url="http://srv-dnp.argos.loc/api/v2/", device_id="pc-1")
    assert config.websocket_url == "ws://srv-dnp.argos.loc/ws/chestniy-znak/client/?device_id=pc-1"


def test_websocket_url_is_built_from_https_base_url() -> None:
    """Проверяет сборку wss URL из HTTPS base URL."""

    config = AppConfig(api_base_url="https://example.org/api/v2/", device_id="pc-2")
    assert config.websocket_url == "wss://example.org/ws/chestniy-znak/client/?device_id=pc-2"
