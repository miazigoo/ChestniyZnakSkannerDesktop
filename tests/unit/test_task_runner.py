"""Тесты оберток фонового запуска задач."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.errors import UnauthorizedError
from chestniy_znak_desktop.runtime.task_runner import FunctionWorker, QtTaskRunner
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


class RecordingThreadPool:
    """Тестовый пул, который только запоминает переданный worker."""

    def __init__(self) -> None:
        """Создает пустой список запущенных задач."""

        self.started_workers: list[FunctionWorker] = []

    def start(self, worker: FunctionWorker) -> None:
        """Запоминает worker без запуска отдельного потока."""

        self.started_workers.append(worker)


def test_qt_runner_keeps_worker_alive_until_signal_delivery() -> None:
    """Проверяет защиту от преждевременного удаления QRunnable в PySide."""

    pool = RecordingThreadPool()
    runner = QtTaskRunner(thread_pool=pool)  # type: ignore[arg-type]

    runner.submit(
        task=lambda: "ok",
        on_success=lambda _result: None,
        on_error=lambda _exc: None,
    )

    worker = pool.started_workers[0]
    assert worker.autoDelete() is False
    assert worker in runner._active_workers

    runner._forget_worker(worker)

    assert worker not in runner._active_workers


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
