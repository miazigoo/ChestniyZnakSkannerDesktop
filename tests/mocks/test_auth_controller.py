"""Mock-тесты контроллера авторизации."""

from __future__ import annotations

from collections.abc import Callable

from chestniy_znak_desktop.api.errors import UnauthorizedError
from chestniy_znak_desktop.api.models.auth import AccountDto, AuthCheckDto
from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.state_models import SessionStatus
from tests.mocks.test_runtime_controller import FakeConnectionMonitor


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


class FakeAuthService:
    """Fake backend авторизации для тестов AuthController."""

    def __init__(self) -> None:
        """Создает fake-сервис с изменяемыми результатами."""

        self.login_result = AccountDto(id=1, username="operator", first_name="Test")
        self.auth_check_result = AuthCheckDto(authenticated=True, user="operator", user_id=1)
        self.login_error: Exception | None = None
        self.restore_error: Exception | None = None
        self.last_token = ""

    def login_by_token(self, token: str) -> AccountDto:
        """Возвращает результат входа или выбрасывает ошибку."""

        self.last_token = token
        if self.login_error is not None:
            raise self.login_error
        return self.login_result

    def auth_check(self) -> AuthCheckDto:
        """Возвращает результат проверки сессии или ошибку."""

        if self.restore_error is not None:
            raise self.restore_error
        return self.auth_check_result

    def logout(self) -> None:
        """Имитирует успешный logout."""


def _controller_pair() -> tuple[AuthController, RuntimeController, FakeAuthService]:
    """Создает AuthController с fake-зависимостями."""

    runtime = RuntimeController(
        app_state=AppState(config=AppConfig()),
        connection_monitor=FakeConnectionMonitor(),
    )
    service = FakeAuthService()
    controller = AuthController(
        auth_service=service,
        runtime_controller=runtime,
        task_runner=ImmediateTaskRunner(),
    )
    return controller, runtime, service


def test_auth_controller_logs_in_with_json_token() -> None:
    """Проверяет вход по JSON-токену и обновление runtime-сессии."""

    controller, runtime, service = _controller_pair()
    controller.login_with_raw_token('{"token":"abc"}')

    assert service.last_token == "abc"
    assert runtime.snapshot.session.status == SessionStatus.AUTHENTICATED
    assert runtime.snapshot.session.user_name == "Test"


def test_auth_controller_reports_bad_token() -> None:
    """Проверяет ошибку для пустого токена."""

    controller, runtime, _service = _controller_pair()
    controller.login_with_raw_token(" ")

    assert controller.state.error_message == "QR-код не содержит токен авторизации"
    assert runtime.snapshot.session.status == SessionStatus.UNKNOWN


def test_auth_controller_restore_session_failure_marks_unauthenticated() -> None:
    """Проверяет сброс сессии при неуспешном восстановлении."""

    controller, runtime, service = _controller_pair()
    service.restore_error = UnauthorizedError("Нет сессии")
    controller.restore_session()

    assert runtime.snapshot.session.status == SessionStatus.UNAUTHENTICATED
    assert controller.state.error_message == ""


def test_auth_controller_logout_clears_session() -> None:
    """Проверяет очистку session state после logout."""

    controller, runtime, _service = _controller_pair()
    controller.login_with_raw_token("abc")
    controller.logout()

    assert runtime.snapshot.session.status == SessionStatus.UNAUTHENTICATED
