"""Фоновое выполнение блокирующих задач."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Protocol

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from chestniy_znak_desktop.api.errors import UnauthorizedError


class TaskRunner(Protocol):
    """Контракт запуска фоновой задачи."""

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Запускает задачу и вызывает callback результата."""


class WorkerSignals(QObject):
    """Qt-сигналы результата фоновой задачи."""

    succeeded = Signal(object)
    failed = Signal(Exception)


class FunctionWorker(QRunnable):
    """QRunnable-обертка над обычной Python-функцией."""

    def __init__(self, task: Callable[[], object]) -> None:
        """Создает worker для указанной задачи."""

        super().__init__()
        self.setAutoDelete(False)
        self.signals = WorkerSignals()
        self._task = task

    @Slot()
    def run(self) -> None:
        """Выполняет функцию и публикует результат или ошибку."""

        try:
            result = self._task()
        except Exception as exc:  # pragma: no cover - путь проверяется через TaskRunner.
            self.signals.failed.emit(exc)
            return
        self.signals.succeeded.emit(result)


class QtTaskRunner:
    """Запускает задачи через `QThreadPool`."""

    def __init__(self, thread_pool: QThreadPool | None = None) -> None:
        """Создает runner с переданным или глобальным пулом потоков."""

        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_workers: set[FunctionWorker] = set()

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Запускает задачу в пуле Qt-потоков."""

        worker = FunctionWorker(task)
        self._active_workers.add(worker)
        worker.signals.succeeded.connect(on_success)
        worker.signals.failed.connect(on_error)
        worker.signals.succeeded.connect(partial(self._forget_worker, worker))
        worker.signals.failed.connect(partial(self._forget_worker, worker))
        self._thread_pool.start(worker)

    def _forget_worker(self, worker: FunctionWorker, _result: object = None) -> None:
        """Освобождает worker только после доставки сигнала результата в UI thread."""

        self._active_workers.discard(worker)


class UnauthorizedAwareTaskRunner:
    """Перехватывает истекшую API-сессию для всех фоновых API-задач."""

    def __init__(
        self,
        base_runner: TaskRunner,
        on_unauthorized: Callable[[UnauthorizedError], None],
    ) -> None:
        """Создает обертку над базовым runner и callback истекшей сессии."""

        self._base_runner = base_runner
        self._on_unauthorized = on_unauthorized

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Запускает задачу и централизованно обрабатывает `UnauthorizedError`."""

        self._base_runner.submit(
            task,
            on_success,
            lambda exc: self._handle_error(exc, on_error),
        )

    def _handle_error(
        self,
        exc: Exception,
        on_error: Callable[[Exception], None],
    ) -> None:
        """Обрабатывает ошибку задачи и делегирует ее контроллеру."""

        if isinstance(exc, UnauthorizedError):
            self._on_unauthorized(exc)
            return
        on_error(exc)
