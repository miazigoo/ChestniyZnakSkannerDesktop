"""Build Linux desktop artifacts: PyInstaller onedir, .deb and portable tar.gz."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

APP_ID = "chestniy-znak-desktop"
APP_TITLE = "Chestniy Znak Desktop"
EXE_NAME = "ChestniyZnakDesktop"
ARCH = "amd64"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def version(root: Path) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("Cannot read project version from pyproject.toml")


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build_pyinstaller(root: Path) -> Path:
    spec_path = root / "packaging" / "chestniy_znak_desktop.spec"
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec_path)], cwd=root)
    dist_dir = root / "dist" / EXE_NAME
    exe = dist_dir / EXE_NAME
    if not exe.exists():
        raise RuntimeError(f"PyInstaller did not create {exe}")
    return dist_dir


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def build_deb(root: Path, dist_dir: Path, app_version: str) -> Path:
    package_root = root / "build" / "linux-deb" / f"{APP_ID}_{app_version}_{ARCH}"
    if package_root.exists():
        shutil.rmtree(package_root)

    app_dir = package_root / "opt" / APP_ID
    copy_tree(dist_dir, app_dir)

    icon_source = (
        root / "src" / "chestniy_znak_desktop" / "resources" / "icons" / "chestniy_znak_app.png"
    )
    icon_dir = package_root / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_source, icon_dir / f"{APP_ID}.png")

    desktop_entry = f"""[Desktop Entry]
Type=Application
Name={APP_TITLE}
Name[ru]=Честный знак Desktop
Comment=Industrial scanning workplace for Chestniy Znak SaaS
Comment[ru]=Рабочее место сканирования для Честного Знака SaaS
Exec=/opt/{APP_ID}/{EXE_NAME}
Icon={APP_ID}
Terminal=false
Categories=Utility;
StartupWMClass={EXE_NAME}
"""
    write_text(package_root / "usr" / "share" / "applications" / f"{APP_ID}.desktop", desktop_entry)

    control = f"""Package: {APP_ID}
Version: {app_version}
Section: utils
Priority: optional
Architecture: {ARCH}
Maintainer: DevAndProd <support@chestniy-z.ru>
Installed-Size: {installed_size_kb(app_dir)}
Depends: libc6, libglib2.0-0, libx11-6, libxext6, libxcb1, libxkbcommon0, libgl1
Description: Chestniy Znak Desktop scanner workplace
 Desktop client for scanner-based packing and verification workflows in Chestniy Znak SaaS.
"""
    write_text(package_root / "DEBIAN" / "control", control)
    write_text(
        package_root / "DEBIAN" / "postinst",
        (
            "#!/bin/sh\n"
            "set -e\n"
            "command -v update-desktop-database >/dev/null 2>&1 "
            "&& update-desktop-database /usr/share/applications || true\n"
            "exit 0\n"
        ),
        0o755,
    )
    write_text(
        package_root / "DEBIAN" / "postrm",
        (
            "#!/bin/sh\n"
            "set -e\n"
            "command -v update-desktop-database >/dev/null 2>&1 "
            "&& update-desktop-database /usr/share/applications || true\n"
            "exit 0\n"
        ),
        0o755,
    )

    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    deb_path = artifacts_dir / f"{APP_ID}_{app_version}_{ARCH}.deb"
    run(["dpkg-deb", "--build", "--root-owner-group", str(package_root), str(deb_path)], cwd=root)
    return deb_path


def installed_size_kb(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            total += (Path(root) / name).stat().st_size
    return max(1, total // 1024)


def build_tarball(root: Path, dist_dir: Path, app_version: str) -> Path:
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    tar_path = artifacts_dir / f"{APP_ID}-{app_version}-linux-x64.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(dist_dir, arcname=f"{APP_ID}-{app_version}-linux-x64")
    return tar_path


def main() -> int:
    if sys.platform != "linux":
        raise RuntimeError("Linux packages must be built on Linux")
    root = project_root()
    app_version = version(root)
    dist_dir = build_pyinstaller(root)
    deb_path = build_deb(root, dist_dir, app_version)
    tar_path = build_tarball(root, dist_dir, app_version)
    print(f"Built {deb_path}")
    print(f"Built {tar_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
