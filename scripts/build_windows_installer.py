"""Сборка Windows setup.exe через PyInstaller и Inno Setup."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from scripts.build_windows import ensure_windows_platform, main as build_windows, project_root


def installer_script_path(root: Path) -> Path:
    """Возвращает путь к Inno Setup script."""

    return root / "packaging" / "windows_installer.iss"


def installer_assets_dir(root: Path) -> Path:
    """Возвращает папку исходников и BMP-ресурсов установщика."""

    return root / "packaging" / "installer_assets"


def installer_output_dir(root: Path) -> Path:
    """Возвращает папку, куда Inno Setup положит готовый setup.exe."""

    return root / "installer"


def find_iscc() -> str:
    """Находит Inno Setup Compiler в PATH или стандартных каталогах."""

    executable = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if executable:
        return executable

    program_files = [
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("ProgramFiles", ""),
    ]
    for base_dir in program_files:
        if not base_dir:
            continue
        candidate = Path(base_dir) / "Inno Setup 6" / "ISCC.exe"
        if candidate.is_file():
            return str(candidate)

    raise RuntimeError(
        "Не найден Inno Setup Compiler. Установите Inno Setup 6 или добавьте ISCC.exe в PATH."
    )


def render_svg_to_bmp(svg_path: Path, bmp_path: Path, width: int, height: int) -> None:
    """Рендерит SVG-исходник в BMP, совместимый с Inno Setup."""

    from PySide6.QtCore import QSize
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Некорректный SVG установщика: {svg_path}")

    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()

    if not image.scaled(QSize(width, height)).save(str(bmp_path), "BMP"):
        raise RuntimeError(f"Не удалось сохранить BMP установщика: {bmp_path}")


def prepare_installer_assets(root: Path) -> None:
    """Готовит BMP-картинки мастера установки из SVG-исходников."""

    assets_dir = installer_assets_dir(root)
    render_svg_to_bmp(
        assets_dir / "installer_wizard.svg",
        assets_dir / "installer_wizard.bmp",
        164,
        314,
    )
    render_svg_to_bmp(
        assets_dir / "installer_small.svg",
        assets_dir / "installer_small.bmp",
        55,
        55,
    )


def build_installer_command(root: Path, iscc_path: str) -> list[str]:
    """Формирует команду компиляции Inno Setup установщика."""

    return [iscc_path, str(installer_script_path(root))]


def main() -> int:
    """Собирает приложение и setup.exe для Windows."""

    ensure_windows_platform()
    root = project_root()
    build_windows()
    prepare_installer_assets(root)
    installer_output_dir(root).mkdir(exist_ok=True)
    subprocess.run(build_installer_command(root, find_iscc()), cwd=root, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
