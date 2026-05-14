"""Тесты оберток фонового запуска задач."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.errors import UnauthorizedError
from chestniy_znak_desktop.runtime.task_runner import UnauthorizedAwareTaskRunner


class ImmediateTaskRunner:
    """TaskRunner, который выполняет задачу сразу в тестовом потоке."""

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Синхронно запускает задачу и вызывает callback."""

        try:
            result = task()
        except Exception as exc:
            on_error(exc)
            return
        on_success(result)


def test_unauthorized_runner_handles_session_expiration() -> None:
    """Проверяет централизованный перехват истекшей сессии."""

    unauthorized_errors: list[str] = []
    local_errors: list[str] = []
    runner = UnauthorizedAwareTaskRunner(
        base_runner=ImmediateTaskRunner(),
        on_unauthorized=lambda exc: unauthorized_errors.append(str(exc)),
    )

    runner.submit(
        task=lambda: _raise_unauthorized(),
        on_success=lambda _result: None,
        on_error=lambda exc: local_errors.append(str(exc)),
    )

    assert unauthorized_errors == ["Сессия истекла"]
    assert local_errors == []


def test_unauthorized_runner_delegates_regular_errors() -> None:
    """Проверяет передачу обычных ошибок в callback контроллера."""

    unauthorized_errors: list[str] = []
    local_errors: list[str] = []
    runner = UnauthorizedAwareTaskRunner(
        base_runner=ImmediateTaskRunner(),
        on_unauthorized=lambda exc: unauthorized_errors.append(str(exc)),
    )

    runner.submit(
        task=lambda: _raise_runtime_error(),
        on_success=lambda _result: None,
        on_error=lambda exc: local_errors.append(str(exc)),
    )

    assert unauthorized_errors == []
    assert local_errors == ["Обычная ошибка"]


def _raise_unauthorized() -> object:
    """Выбрасывает ошибку истекшей сессии для теста."""

    raise UnauthorizedError("Сессия истекла")


def _raise_runtime_error() -> object:
    """Выбрасывает обычную ошибку для теста."""

    raise RuntimeError("Обычная ошибка")
