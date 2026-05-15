"""Mock-тесты контроллера диагностики."""

from __future__ import annotations

from chestniy_znak_desktop.app.config import AppConfig
from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsController
from chestniy_znak_desktop.services.log_service import LogService


def test_diagnostics_controller_refreshes_logs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет обновление логов на экране диагностики."""

    log_file = tmp_path / "desktop.log"
    log_file.write_text("line\n", encoding="utf-8")
    controller = DiagnosticsController(
        config=AppConfig(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            data_dir=tmp_path,
        ),
        log_service=LogService(log_file),
    )

    controller.refresh_logs()

    assert controller.state.log_text == "line"
    assert controller.state.status_message == "Логи обновлены"
    assert controller.state.device_id == "pc-1"


def test_diagnostics_controller_clears_logs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет очистку логов через диагностику."""

    log_file = tmp_path / "desktop.log"
    log_file.write_text("line\n", encoding="utf-8")
    controller = DiagnosticsController(
        config=AppConfig(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            data_dir=tmp_path,
        ),
        log_service=LogService(log_file),
    )

    controller.clear_logs()

    assert log_file.read_text(encoding="utf-8") == ""
    assert controller.state.log_text == ""
    assert controller.state.status_message == "Логи очищены"
