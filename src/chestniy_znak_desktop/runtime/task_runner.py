"""Фоновое выполнение блокирующих задач."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


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

    def submit(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Запускает задачу в пуле Qt-потоков."""

        worker = FunctionWorker(task)
        worker.signals.succeeded.connect(on_success)
        worker.signals.failed.connect(on_error)
        self._thread_pool.start(worker)
