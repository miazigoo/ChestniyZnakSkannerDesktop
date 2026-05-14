"""DTO авторизации."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AccountDto(BaseModel):
    """Данные авторизованного пользователя."""

    id: int
    username: str
    first_name: str = Field(default="")
    last_name: str = Field(default="")

    @property
    def display_name(self) -> str:
        """Возвращает отображаемое имя пользователя."""

        return " ".join([self.first_name, self.last_name]).strip() or self.username


class AuthCheckDto(BaseModel):
    """Ответ проверки текущей сессии."""

    authenticated: bool
    user: str
    user_id: int
