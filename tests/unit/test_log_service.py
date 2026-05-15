"""Тесты сервиса чтения логов."""

from __future__ import annotations

from chestniy_znak_desktop.services.log_service import LogService


def test_log_service_reads_tail(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет чтение последних строк лог-файла."""

    log_file = tmp_path / "desktop.log"
    log_file.write_text("1\n2\n3\n", encoding="utf-8")

    assert LogService(log_file).tail(max_lines=2) == "2\n3"


def test_log_service_reports_missing_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет понятный текст для отсутствующего лог-файла."""

    assert LogService(tmp_path / "missing.log").tail() == "Лог-файл еще не создан"


def test_log_service_clears_log_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Проверяет очистку существующего лог-файла."""

    log_file = tmp_path / "desktop.log"
    log_file.write_text("line\n", encoding="utf-8")

    LogService(log_file).clear()

    assert log_file.read_text(encoding="utf-8") == ""
