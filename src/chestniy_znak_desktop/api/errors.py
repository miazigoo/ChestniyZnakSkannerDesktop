"""Исключения API-клиента."""

from __future__ import annotations


class ApiError(RuntimeError):
    """Базовая ошибка обращения к backend API."""


class UnauthorizedError(ApiError):
    """Ошибка истекшей или отсутствующей сессии."""
