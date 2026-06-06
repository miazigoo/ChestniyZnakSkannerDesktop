"""Извлечение токена авторизации из QR или строки сканера."""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, unquote, urlparse


def extract_auth_token(raw_value: str) -> str | None:
    """Возвращает токен из JSON, URL query или plain-text строки."""

    normalized = raw_value.strip().strip("\"'")
    if not normalized:
        return None
    json_token = _extract_json_token(normalized)
    if json_token:
        return json_token
    query_token = _extract_query_token(normalized)
    if query_token:
        return query_token
    return _normalize_activation_token(normalized)


def _extract_json_token(value: str) -> str | None:
    """Извлекает поле `token` из JSON-строки."""

    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    token = payload.get("token") or payload.get("activation_code") or payload.get("app_token")
    return _normalize_activation_token(str(token)) if token else None


def _extract_query_token(value: str) -> str | None:
    """Извлекает `token` из URL или query-like строки."""

    parsed = urlparse(value)
    query = parsed.query or value.lstrip("?")
    values = parse_qs(query)
    token_values = values.get("token")
    if not token_values:
        return None
    return _normalize_activation_token(unquote(token_values[0]))


def _normalize_activation_token(value: str) -> str | None:
    """Нормализует app-token `XXXX-XXXX-XXXX` и отбрасывает случайные HID-клавиши."""

    token = value.strip().upper()
    if _TOKEN_PATTERN.fullmatch(token):
        return token
    compact = token.replace("-", "")
    if _COMPACT_TOKEN_PATTERN.fullmatch(compact):
        return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}"
    return None


_TOKEN_PATTERN = re.compile(r"[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}")
_COMPACT_TOKEN_PATTERN = re.compile(r"[A-Z0-9]{12}")
