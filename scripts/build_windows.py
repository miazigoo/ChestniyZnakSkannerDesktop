"""Запуск сборки Windows-дистрибутива через PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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


def main() -> int:
    """Запускает PyInstaller и возвращает код завершения процесса."""

    ensure_windows_platform()
    root = project_root()
    subprocess.run(build_command(root), cwd=root, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
