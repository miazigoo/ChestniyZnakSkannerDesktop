"""Тесты конфигурации сборки desktop-приложения."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.build_windows import build_command, ensure_windows_platform, project_root
from scripts.build_windows_installer import (
    build_installer_command,
    installer_output_dir,
    installer_script_path,
)


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


def test_inno_setup_script_is_present() -> None:
    """Проверяет наличие Inno Setup script и установочных картинок."""

    root = project_root()
    script_text = installer_script_path(root).read_text(encoding="utf-8")

    assert "ChestniyZnakDesktopSetup" in script_text
    assert "WizardImageFile=installer_assets\\installer_wizard.bmp" in script_text
    assert "WizardSmallImageFile=installer_assets\\installer_small.bmp" in script_text
    assert 'Source: "{#MyBuildDir}\\*"' in script_text
    assert (root / "packaging" / "installer_assets" / "installer_wizard.svg").is_file()
    assert (root / "packaging" / "installer_assets" / "installer_small.svg").is_file()


def test_inno_setup_command_uses_iss_script() -> None:
    """Проверяет команду запуска Inno Setup Compiler."""

    root = project_root()
    command = build_installer_command(root, "ISCC.exe")

    assert command[0] == "ISCC.exe"
    assert Path(command[1]) == root / "packaging" / "windows_installer.iss"


def test_installer_output_dir_points_to_project_artifact() -> None:
    """Проверяет папку выходного установщика."""

    assert installer_output_dir(project_root()).name == "installer"
