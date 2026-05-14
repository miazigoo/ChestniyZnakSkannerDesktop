"""Smoke-тесты UI-виджетов без запуска основного event loop."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from chestniy_znak_desktop.runtime.state_models import (  # noqa: E402
    ConnectionState,
    ConnectionStatus,
    RuntimeSnapshot,
    ScannerState,
    ScannerStatus,
    SessionState,
    SessionStatus,
)
from chestniy_znak_desktop.controllers.auth_controller import AuthUiState  # noqa: E402
from chestniy_znak_desktop.controllers.packing_controller import (  # noqa: E402
    PackingBoxUi,
    PackingItemUi,
    PackingUiState,
)
from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState  # noqa: E402
from chestniy_znak_desktop.ui.screens.main_screen import MainScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.login_screen import LoginScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from chestniy_znak_desktop.ui.widgets.blocking_overlay import BlockingOverlay  # noqa: E402
from chestniy_znak_desktop.ui.widgets.runtime_status_bar import RuntimeStatusBar  # noqa: E402


def qapp() -> QApplication:
    """Возвращает существующий QApplication или создает новый."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return cast(QApplication, app)


def test_main_screen_can_be_created() -> None:
    """Проверяет создание главного экрана с рабочей навигацией."""

    qapp()
    screen = MainScreen()
    assert screen is not None


def test_main_screen_updates_active_navigation() -> None:
    """Проверяет активное состояние современной навигации."""

    qapp()
    screen = MainScreen()

    assert len(screen._nav_items) == 7  # noqa: SLF001
    assert screen._nav_items[0].property("active") is True  # noqa: SLF001

    screen.show_boxes()

    assert screen._nav_items[1].property("active") is True  # noqa: SLF001


def test_boxes_screen_has_backend_status_filters() -> None:
    """Проверяет наличие backend-фильтров списка коробок."""

    qapp()
    screen = BoxesScreen()

    values = [
        screen._status_filter.itemData(index)  # noqa: SLF001
        for index in range(screen._status_filter.count())  # noqa: SLF001
    ]

    assert values == ["all", "active", "open", "edit", "closed", "empty"]


def test_packing_screen_shows_box_progress_and_items() -> None:
    """Проверяет современный экран упаковки с открытой коробкой."""

    qapp()
    screen = PackingScreen()
    screen.apply_runtime_snapshot(
        RuntimeSnapshot(
            scanner=ScannerState(
                status=ScannerStatus.RUNNING,
                port="/dev/rfcomm0",
            )
        )
    )
    screen.apply_state(
        PackingUiState(
            current_box=PackingBoxUi(
                box_id=42,
                order_name="Заказ 100",
                sscc="046012345678901234",
                filled=1,
                capacity=10,
                count_in_packing=True,
                is_closed=False,
                print_ok=False,
                print_error="",
                items=[
                    PackingItemUi(
                        id=1,
                        gtin="04601234567890",
                        serial="ABC123",
                        visible_code="04601234567890ABC123",
                    )
                ],
            ),
            status_message="Код добавлен",
            result_message="OK",
            last_scanned_code="04601234567890ABC123",
        )
    )

    assert screen._progress_bar.value() == 1  # noqa: SLF001
    assert screen._items_table.rowCount() == 1  # noqa: SLF001
    assert screen._close_box_button.isEnabled() is True  # noqa: SLF001


def test_settings_screen_has_grouped_pages() -> None:
    """Проверяет, что настройки разнесены по страницам."""

    qapp()
    screen = SettingsScreen()

    assert screen._stack.count() == 6  # noqa: SLF001


def test_settings_screen_emits_sound_preview() -> None:
    """Проверяет сигнал прослушивания звука из страницы звуков."""

    qapp()
    screen = SettingsScreen()
    previews: list[str] = []
    screen.sound_preview_requested.connect(previews.append)
    screen.apply_settings_state(
        SettingsUiState(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.85,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
            available_sound_files=["ok_02.mp3", "other.mp3", "error.mp3", "victory.mp3"],
        )
    )

    screen._sound_page.preview_requested.emit("ok_02.mp3")  # noqa: SLF001

    assert previews == ["ok_02.mp3"]


def test_main_screen_emits_logout_request() -> None:
    """Проверяет проброс запроса выхода из рабочего экрана."""

    qapp()
    screen = MainScreen()
    requests: list[bool] = []
    screen.logout_requested.connect(lambda: requests.append(True))

    screen.logout_requested.emit()

    assert requests == [True]


def test_login_screen_shows_token_preview() -> None:
    """Проверяет, что логин показывает факт последнего скана."""

    qapp()
    screen = LoginScreen()
    screen.apply_state(
        AuthUiState(
            status_message="Авторизация не выполнена.",
            error_message="Неверный токен",
            token_preview="abcd...1234",
        )
    )

    assert screen is not None


def test_login_screen_renders_vector_background() -> None:
    """Проверяет, что login-экран рисует непустой векторный фон."""

    qapp()
    screen = LoginScreen()
    screen.resize(1180, 760)
    pixmap = QPixmap(screen.size())
    pixmap.fill(Qt.GlobalColor.transparent)

    screen.render(pixmap)
    sample = QColor(pixmap.toImage().pixel(20, 20))

    assert sample.alpha() > 0
    assert sample != QColor(Qt.GlobalColor.transparent)


def test_runtime_status_bar_accepts_snapshot() -> None:
    """Проверяет обновление статусной панели runtime snapshot."""

    qapp()
    widget = RuntimeStatusBar()
    widget.update_snapshot(
        RuntimeSnapshot(
            connection=ConnectionState(
                status=ConnectionStatus.CONNECTED,
                message="Соединение активно",
            ),
            session=SessionState(
                status=SessionStatus.AUTHENTICATED,
                user_name="Operator",
            ),
            scanner=ScannerState(
                status=ScannerStatus.RUNNING,
                port="COM7",
            ),
        )
    )
    assert widget is not None


def test_blocking_overlay_changes_visibility() -> None:
    """Проверяет показ и скрытие блокирующего overlay."""

    qapp()
    overlay = BlockingOverlay()
    overlay.set_blocking(True, "Нет связи")
    assert overlay.isVisible() is True
    overlay.set_blocking(False, "")
    assert overlay.isVisible() is False


def test_boxes_screen_confirm_accepts_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет подтверждение опасного действия в экране коробок."""

    qapp()
    screen = BoxesScreen()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    assert screen._confirm("Удалить", "Подтвердите") is True  # noqa: SLF001
