"""Контроллер авторизации оператора."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from PySide6.QtCore import QObject, Signal

from chestniy_znak_desktop.api.errors import (
    ApiError,
    PlantSubscriptionExpiredError,
    UnauthorizedError,
)
from chestniy_znak_desktop.api.models.auth import AccountDto, AuthCheckDto
from chestniy_znak_desktop.domain.auth_token_extractor import extract_auth_token
from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.runtime.task_runner import TaskRunner

TAuthResult = TypeVar("TAuthResult", AccountDto, AuthCheckDto)


class AuthBackend(Protocol):
    """Контракт backend-сервиса авторизации."""

    def login_by_token(self, token: str) -> AccountDto:
        """Авторизует пользователя по токену."""

    def auth_check(self) -> AuthCheckDto:
        """Проверяет текущую сессию."""

    def logout(self) -> None:
        """Завершает текущую сессию."""


@dataclass(frozen=True, slots=True)
class AuthUiState:
    """Состояние экрана авторизации."""

    is_submitting: bool = False
    status_message: str = field(default_factory=lambda: tr("login.waitStatus"))
    error_message: str = ""
    token_preview: str = ""


class AuthController(QObject):
    """Оркестрирует восстановление сессии и вход по токену."""

    state_changed = Signal(AuthUiState)
    authenticated = Signal(str)
    unauthenticated = Signal()

    def __init__(
        self,
        auth_service: AuthBackend,
        runtime_controller: RuntimeController,
        task_runner: TaskRunner,
        parent: QObject | None = None,
    ) -> None:
        """Создает контроллер авторизации."""

        super().__init__(parent)
        self._auth_service = auth_service
        self._runtime_controller = runtime_controller
        self._task_runner = task_runner
        self._state = AuthUiState()

    @property
    def state(self) -> AuthUiState:
        """Возвращает текущее состояние авторизации."""

        return self._state

    def restore_session(self) -> None:
        """Пробует восстановить локальную app-сессию при старте приложения."""

        self._set_state(
            AuthUiState(
                is_submitting=True,
                status_message=tr("auth.restore"),
            )
        )
        self._task_runner.submit(
            self._auth_service.auth_check,
            self._on_session_restored,
            self._on_restore_failed,
        )

    def login_with_raw_token(self, raw_token: str) -> None:
        """Извлекает токен из строки сканера и запускает вход."""

        if self._state.is_submitting:
            return
        token = extract_auth_token(raw_token)
        if not token:
            self._set_state(
                AuthUiState(
                    status_message=tr("auth.scanAnother"),
                    error_message=tr("auth.tokenMissing"),
                )
            )
            return
        self._set_state(
            AuthUiState(
                is_submitting=True,
                status_message=tr("auth.signingInStatus"),
                token_preview=self._mask_token(token),
            )
        )
        self._task_runner.submit(
            lambda: self._auth_service.login_by_token(token),
            self._on_login_success,
            self._on_login_failed,
        )

    def logout(self) -> None:
        """Завершает текущую сессию и возвращает приложение к экрану входа."""

        self._task_runner.submit(
            self._auth_service.logout,
            self._on_logout_finished,
            self._on_logout_failed,
        )

    def handle_session_expired(self, message: str) -> None:
        """Сбрасывает UI и runtime после истечения backend-сессии."""

        self._runtime_controller.clear_session()
        self._set_state(
            AuthUiState(
                status_message=tr("auth.sessionExpired"),
                error_message=message,
            )
        )
        self.unauthenticated.emit()

    def _on_session_restored(self, result: object) -> None:
        """Обрабатывает успешную проверку сохраненной сессии."""

        auth_check = self._as_type(result, AuthCheckDto)
        if auth_check.authenticated:
            self._runtime_controller.set_authenticated_user(
                auth_check.user,
                plant_id=auth_check.plant_id,
                device_id=auth_check.device_id,
                supplier_id=auth_check.supplier_id,
                supplier_name=auth_check.supplier_name,
                plant_name=auth_check.plant_name,
                client_device_id=auth_check.client_device_id,
                subscription_status=auth_check.subscription_status,
            )
            self._set_state(AuthUiState(status_message=tr("auth.restored")))
            self.authenticated.emit(auth_check.user)
            return
        self._runtime_controller.clear_session()
        self._set_state(AuthUiState(status_message=tr("auth.scanToken")))
        self.unauthenticated.emit()

    def _on_restore_failed(self, exc: Exception) -> None:
        """Обрабатывает ошибку восстановления сессии."""

        self._runtime_controller.clear_session()
        message = tr("auth.scanToken")
        if isinstance(exc, PlantSubscriptionExpiredError):
            error = str(exc)
        else:
            error = "" if isinstance(exc, UnauthorizedError) else str(exc)
        self._set_state(AuthUiState(status_message=message, error_message=error))
        self.unauthenticated.emit()

    def _on_login_success(self, result: object) -> None:
        """Обрабатывает успешный вход по токену."""

        account = self._as_type(result, AccountDto)
        self._runtime_controller.set_authenticated_user(
            account.display_name,
            plant_id=account.plant_id,
            device_id=account.device_id,
            supplier_id=account.supplier_id,
            supplier_name=account.supplier_name,
            plant_name=account.plant_name,
            client_device_id=account.client_device_id,
            subscription_status=account.subscription_status,
        )
        self._set_state(AuthUiState(status_message=tr("auth.loginOk")))
        self.authenticated.emit(account.display_name)

    def _on_login_failed(self, exc: Exception) -> None:
        """Обрабатывает ошибку входа по токену."""

        message = str(exc) if isinstance(exc, ApiError) else tr("auth.loginFailed")
        self._set_state(
            AuthUiState(
                status_message=tr("auth.authFailed"),
                error_message=message,
                token_preview=self._state.token_preview,
            )
        )

    def _on_logout_finished(self, _result: object) -> None:
        """Обрабатывает успешное завершение сессии."""

        self._runtime_controller.clear_session()
        self._set_state(AuthUiState(status_message=tr("auth.loggedOut")))
        self.unauthenticated.emit()

    def _on_logout_failed(self, exc: Exception) -> None:
        """Обрабатывает ошибку выхода, но локально сбрасывает сессию."""

        self._runtime_controller.clear_session()
        self._set_state(
            AuthUiState(
                status_message=tr("auth.localReset"),
                error_message=str(exc),
            )
        )
        self.unauthenticated.emit()

    def _set_state(self, state: AuthUiState) -> None:
        """Сохраняет и публикует состояние авторизации."""

        self._state = state
        self.state_changed.emit(state)

    @staticmethod
    def _mask_token(token: str) -> str:
        """Возвращает короткое безопасное отображение токена."""

        if len(token) <= 8:
            return tr("auth.tokenAccepted")
        return f"{token[:4]}...{token[-4:]}"

    @staticmethod
    def _as_type(result: object, expected_type: type[TAuthResult]) -> TAuthResult:
        """Проверяет тип результата фоновой задачи."""

        if not isinstance(result, expected_type):
            raise TypeError(f"Ожидался результат {expected_type.__name__}")
        return result
