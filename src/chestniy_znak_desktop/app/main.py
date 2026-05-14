"""Точка входа desktop-приложения."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from chestniy_znak_desktop.app.bootstrap import create_app_window
from chestniy_znak_desktop.app.config import load_app_config
from chestniy_znak_desktop.app.logging_config import configure_logging


def main() -> int:
    """Запускает Qt-приложение и возвращает код завершения."""

    config = load_app_config()
    configure_logging(config.data_dir / "logs")
    qt_app = QApplication(sys.argv)
    window = create_app_window(qt_app=qt_app, config=config)
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
