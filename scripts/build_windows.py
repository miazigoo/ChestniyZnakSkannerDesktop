"""Запуск сборки Windows-дистрибутива через PyInstaller."""

from __future__ import annotations

import importlib as importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

REQUIRED_BUILD_MODULES = {
    "httpx": "httpx",
    "pydantic": "pydantic",
    "PyInstaller": "pyinstaller",
    "PySide6": "PySide6",
    "serial": "pyserial",
}


def project_root() -> Path:
    """Возвращает корень проекта относительно текущего скрипта."""

    return Path(__file__).resolve().parents[1]


def build_command(root: Path) -> list[str]:
    """Формирует команду PyInstaller для стабильной onedir-сборки."""

    spec_path = root / "packaging" / "chestniy_znak_desktop.spec"
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_path),
    ]


def ensure_windows_platform() -> None:
    """Останавливает сборку, если запущена не на Windows."""

    if sys.platform == "win32":
        return
    raise RuntimeError(
        "Windows .exe нужно собирать на Windows с Windows Python. "
        "PyInstaller не делает корректную Windows-сборку из Linux."
    )


def ensure_required_modules() -> None:
    """Проверяет, что сборка запущена из окружения со всеми зависимостями."""

    missing_packages = [
        package_name
        for module_name, package_name in REQUIRED_BUILD_MODULES.items()
        if importlib.util.find_spec(module_name) is None
    ]
    if not missing_packages:
        return
    packages = ", ".join(sorted(missing_packages))
    raise RuntimeError(
        f"В текущем Python-окружении не хватает зависимостей: {packages}. "
        "Выполните: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
    )


def main() -> int:
    """Запускает PyInstaller и возвращает код завершения процесса."""

    ensure_windows_platform()
    ensure_required_modules()
    root = project_root()
    subprocess.run(build_command(root), cwd=root, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
