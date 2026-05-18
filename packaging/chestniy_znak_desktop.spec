# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для сборки desktop-клиента под Windows."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(SPECPATH).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
PACKAGE_DIR = SRC_DIR / "chestniy_znak_desktop"
ENTRYPOINT = PACKAGE_DIR / "app" / "main.py"

SOUNDS_DIR = PACKAGE_DIR / "resources" / "sounds"
ICONS_DIR = PACKAGE_DIR / "resources" / "icons"

datas = [
    (str(SOUNDS_DIR), "chestniy_znak_desktop/resources/sounds"),
    (str(ICONS_DIR), "chestniy_znak_desktop/resources/icons"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtMultimedia",
    "PySide6.QtNetwork",
    "PySide6.QtWebSockets",
    "PySide6.QtWidgets",
    "serial.tools.list_ports",
]
hiddenimports += collect_submodules("anyio")
hiddenimports += collect_submodules("httpcore")
hiddenimports += collect_submodules("httpx")
hiddenimports += collect_submodules("pydantic")

a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ChestniyZnakDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ChestniyZnakDesktop",
)
