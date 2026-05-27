"""Сервис проверки кодов Честного знака."""

from __future__ import annotations

from chestniy_znak_desktop.api.models.stats import CatalogStatsDto
from chestniy_znak_desktop.api.models.verify import (
    DefectResponseDto,
    VerifyExistsResponseDto,
    VerifyResponseDto,
)
from chestniy_znak_desktop.api.services.api_client_protocol import ApiClientProtocol


class ChestniyZnakService:
    """Выполняет проверку DataMatrix, брак и статистику каталога."""

    def __init__(self, api_client: ApiClientProtocol) -> None:
        """Сохраняет API-клиент сервиса."""

        self._api_client = api_client

    def verify(
        self, code: str, scanner_id: str, allow_duplicate: bool = False
    ) -> VerifyResponseDto:
        """Выполняет полную проверку DataMatrix-кода."""

        payload = self._api_client.post(
            "chestniy-znak/verify",
            json={
                "code": code,
                "scanner_id": scanner_id,
                "allow_duplicate": allow_duplicate,
                "save_scan": True,
            },
        )
        return VerifyResponseDto.model_validate(payload)

    def verify_exists(
        self,
        code: str,
        scanner_id: str,
        allow_duplicate: bool = True,
        save_scan: bool = True,
    ) -> VerifyExistsResponseDto:
        """Проверяет существование DataMatrix-кода в базе."""

        payload = self._api_client.post(
            "chestniy-znak/verify/exists",
            json={
                "code": code,
                "scanner_id": scanner_id,
                "allow_duplicate": allow_duplicate,
                "save_scan": save_scan,
            },
        )
        return VerifyExistsResponseDto.model_validate(payload)

    def mark_defect(self, code: str, scanner_id: str) -> DefectResponseDto:
        """Отправляет отсканированный код в сценарий брака."""

        payload = self._api_client.post(
            "chestniy-znak/laser/defect",
            json={"code": code, "scanner_id": scanner_id},
        )
        return DefectResponseDto.model_validate(payload)

    def stats(self) -> CatalogStatsDto:
        """Получает счетчики справочника ЧЗ."""

        payload = self._api_client.get("chestniy-znak/catalog/stats")
        return CatalogStatsDto.model_validate(payload)
