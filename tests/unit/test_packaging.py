"""Тесты конфигурации сборки desktop-приложения."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.build_windows import build_command, ensure_windows_platform, project_root


def test_build_script_points_to_project_root() -> None:
    """Проверяет, что скрипт сборки находит корень проекта."""

    assert (project_root() / "pyproject.toml").is_file()


def test_build_command_uses_pyinstaller_spec() -> None:
    """Проверяет команду запуска PyInstaller через текущий Python."""

    command = build_command(project_root())

    assert command[:3] == [sys.executable, "-m", "PyInstaller"]
    assert "--clean" in command
    assert command[-1].endswith("packaging/chestniy_znak_desktop.spec")


def test_pyinstaller_spec_keeps_runtime_resources() -> None:
    """Фиксирует включение ресурсов и Qt-модулей в сборку."""

    spec_text = Path("packaging/chestniy_znak_desktop.spec").read_text(encoding="utf-8")

    assert "PROJECT_ROOT = Path(SPECPATH).parent.parent" in spec_text
    assert "resources/sounds" in spec_text
    assert "resources/icons" in spec_text
    assert "PySide6.QtWebSockets" in spec_text
    assert "PySide6.QtMultimedia" in spec_text
    assert "serial.tools.list_ports" in spec_text
    assert "console=False" in spec_text


def test_build_script_rejects_non_windows_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет, что Windows-сборку нельзя случайно собрать под Linux."""

    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(RuntimeError, match="Windows .exe"):
        ensure_windows_platform()
