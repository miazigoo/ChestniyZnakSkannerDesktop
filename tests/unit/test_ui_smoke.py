"""Smoke-тесты UI-виджетов без запуска основного event loop."""

from __future__ import annotations

import os
import sys
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QPixmap  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QCheckBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
)

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
from chestniy_znak_desktop.controllers.auto_packing_controller import (  # noqa: E402
    AutoPackingBoxItemUi,
    AutoPackingUiState,
)
from chestniy_znak_desktop.controllers.boxes_controller import (  # noqa: E402
    BoxDetailItemUi,
    BoxDetailUi,
    BoxRowUi,
    BoxesUiState,
)
from chestniy_znak_desktop.controllers.box_lookup_controller import (  # noqa: E402
    BoxLookupUiState,
)
from chestniy_znak_desktop.controllers.defect_controller import DefectUiState  # noqa: E402
from chestniy_znak_desktop.controllers.diagnostics_controller import (  # noqa: E402
    DiagnosticsUiState,
)
from chestniy_znak_desktop.controllers.packing_controller import (  # noqa: E402
    CloseBoxUiEvent,
    PackingBoxUi,
    PackingItemUi,
    PackingUiState,
)
from chestniy_znak_desktop.controllers.printer_controller import (  # noqa: E402
    PrinterOptionUi,
    PrinterUiState,
)
from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState  # noqa: E402
from chestniy_znak_desktop.controllers.verify_controller import VerifyUiState  # noqa: E402
from chestniy_znak_desktop.i18n import set_current_language  # noqa: E402
from chestniy_znak_desktop.ui.screens.main_screen import MainScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.auto_packing_screen import (  # noqa: E402
    AutoPackingScreen,
)
from chestniy_znak_desktop.ui.screens.login_screen import LoginScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.box_lookup_screen import BoxLookupScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.defect_screen import DefectScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.diagnostics_screen import DiagnosticsScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.verify_screen import VerifyScreen  # noqa: E402
from chestniy_znak_desktop.ui.screens.settings_pages.theme_page import (  # noqa: E402
    ThemeOptionCard,
)
from chestniy_znak_desktop.ui.i18n_widgets import retranslate_widget_tree  # noqa: E402
from chestniy_znak_desktop.ui.widgets.adaptive_scroll_area import (  # noqa: E402
    AdaptiveScrollArea,
)
from chestniy_znak_desktop.ui.widgets.blocking_overlay import BlockingOverlay  # noqa: E402
from chestniy_znak_desktop.ui.widgets.close_box_dialog import (  # noqa: E402
    CloseBoxConfirmDialog,
    CloseBoxDialog,
    CloseBoxProgressDialog,
)
from chestniy_znak_desktop.ui.widgets.runtime_status_bar import RuntimeStatusBar  # noqa: E402
from chestniy_znak_desktop.ui.widgets.settings_saved_dialog import (  # noqa: E402
    SettingsSavedDialog,
    SvgBackdrop,
)


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

    assert len(screen._nav_items) == 8  # noqa: SLF001
    assert screen._nav_items[0].property("active") is True  # noqa: SLF001

    screen.show_boxes()

    assert screen._nav_items[2].property("active") is True  # noqa: SLF001

    screen.show_packing()

    assert screen._nav_items[0].property("active") is True  # noqa: SLF001


def test_main_screen_does_not_force_tall_window() -> None:
    """Проверяет, что рабочий экран не растягивает окно по высоте."""

    qapp()
    screen = MainScreen()

    assert screen.minimumSizeHint().height() <= 640


def test_main_work_screens_are_scrollable() -> None:
    """Проверяет, что рабочие экраны завернуты в адаптивный скролл."""

    qapp()
    screen = MainScreen()

    wrappers = screen.findChildren(AdaptiveScrollArea)

    assert len(wrappers) == 8
    assert all(wrapper.minimumSizeHint().height() <= 240 for wrapper in wrappers)


def test_main_sidebar_keeps_navigation_compact() -> None:
    """Проверяет, что сайдбар не сжимает блок сессии поверх меню."""

    qapp()
    screen = MainScreen()

    scroll_area = screen.findChild(QScrollArea, "mainSidebarScroll")

    assert scroll_area is not None
    assert screen._session_panel.minimumHeight() == 124  # noqa: SLF001
    assert all(item.minimumHeight() == 58 for item in screen._nav_items)  # noqa: SLF001


def test_main_screen_switches_to_compact_mode() -> None:
    """Проверяет компактный режим главного экрана на небольшом окне."""

    qapp()
    screen = MainScreen()
    screen.resize(900, 620)
    screen.show()
    qapp().processEvents()

    assert screen._is_compact is True  # noqa: SLF001
    assert screen._sidebar is not None  # noqa: SLF001
    assert screen._sidebar.width() == 214  # noqa: SLF001


def test_boxes_screen_has_backend_status_filters() -> None:
    """Проверяет наличие backend-фильтров списка коробок."""

    qapp()
    screen = BoxesScreen()

    values = [
        screen._status_filter.itemData(index)  # noqa: SLF001
        for index in range(screen._status_filter.count())  # noqa: SLF001
    ]

    assert values == ["all", "active", "open", "edit", "closed", "empty"]


def test_auto_packing_screen_shows_local_box_state() -> None:
    """Проверяет экран локального бокса автосканера."""

    qapp()
    screen = AutoPackingScreen()
    code_with_gs = "010460123456789021A10000000291VDMY\x1d91RATR2\x1d92TAIL"
    visible_code = "010460123456789021A10000000291VDMY<GS>91RATR2<GS>92TAIL"
    screen.apply_state(
        AutoPackingUiState(
            codes_per_item=2,
            pending_items=[
                AutoPackingBoxItemUi(
                    code_id=1,
                    raw_code=code_with_gs,
                    gtin="04646151697261",
                    serial="SERIAL1",
                    visible_code=code_with_gs,
                    order_key="26-0001/0001",
                )
            ],
            current_box=PackingBoxUi(
                box_id=7,
                order_name="26-0001/0001",
                sscc="",
                filled=1,
                capacity=12,
                count_in_packing=True,
                is_closed=False,
                items=[
                    PackingItemUi(
                        id=11,
                        gtin="04646151697261",
                        serial="SERIAL1",
                        visible_code=code_with_gs,
                    )
                ],
            ),
            status_message="Код добавлен",
        )
    )

    assert screen._pending_table.rowCount() == 1  # noqa: SLF001
    assert screen._box_items_table.rowCount() == 1  # noqa: SLF001
    assert screen._status_title.text() == "Бокс не заполнен: 1 / 2"  # noqa: SLF001
    assert screen._tables_tabs.tabText(0) == "Локальный бокс (1/2)"  # noqa: SLF001
    assert screen._tables_tabs.tabText(1) == "Текущая коробка (1)"  # noqa: SLF001
    assert screen._pending_table.item(0, 4).text() == visible_code  # noqa: SLF001
    assert screen._box_items_table.item(0, 3).text() == visible_code  # noqa: SLF001


def test_boxes_screen_shows_rows_and_detail_panel() -> None:
    """Проверяет современный экран списка и деталей коробок."""

    qapp()
    screen = BoxesScreen()
    screen.apply_state(
        BoxesUiState(
            total=1,
            rows=[
                BoxRowUi(
                    box_id=77,
                    order_name="Заказ 77",
                    sscc="046012345678901234",
                    filled="2 / 10",
                    status="Открыта",
                    operator="Operator",
                )
            ],
            selected_box_id=77,
            detail=BoxDetailUi(
                box_id=77,
                order_name="Заказ 77",
                sscc="046012345678901234",
                filled=2,
                capacity=10,
                status="Открыта",
                count_in_packing="Да",
                operator="Operator",
                items=[
                    BoxDetailItemUi(
                        id=501,
                        gtin="04601234567890",
                        serial="SERIAL77",
                        visible_code="04601234567890SERIAL77\x1d91ABC",
                    )
                ],
            ),
            status_message="Коробки загружены",
            detail_status_message="Коробка #77 загружена",
        )
    )

    assert screen._table.rowCount() == 1  # noqa: SLF001
    assert screen._detail_items_table.rowCount() == 1  # noqa: SLF001
    assert "увидеть состав" in screen._table.item(0, 0).toolTip()  # noqa: SLF001
    assert "Удалить все коды" in screen._clear_box_button.toolTip()  # noqa: SLF001
    assert (  # noqa: SLF001
        screen._detail_items_table.item(0, 3).text() == "04601234567890SERIAL77<GS>91ABC"
    )


def test_boxes_screen_loads_detail_on_single_click() -> None:
    """Проверяет запрос деталей коробки по одному клику строки."""

    qapp()
    screen = BoxesScreen()
    requested: list[int] = []
    screen.box_detail_requested.connect(requested.append)
    screen.apply_state(
        BoxesUiState(
            total=1,
            rows=[
                BoxRowUi(
                    box_id=77,
                    order_name="Заказ 77",
                    sscc="046012345678901234",
                    filled="2 / 10",
                    status="Открыта",
                    operator="Operator",
                )
            ],
            status_message="Коробки загружены",
        )
    )

    screen._table.cellClicked.emit(0, 0)  # noqa: SLF001

    assert requested == [77]


def test_box_lookup_screen_shows_scanner_result() -> None:
    """Проверяет современный scanner-only экран поиска коробки."""

    qapp()
    screen = BoxLookupScreen()
    screen.apply_runtime_snapshot(
        RuntimeSnapshot(
            scanner=ScannerState(
                status=ScannerStatus.RUNNING,
                port="/dev/rfcomm0",
            )
        )
    )
    screen.apply_state(
        BoxLookupUiState(
            status_message="Коробка #77 найдена",
            last_scanned_code="(00)046012345678901234",
            found_box_id=77,
            found_box_summary="#77 | Заказ 77 | 046012345678901234 | 2/10",
            log=["(00)046012345678901234: #77 | Заказ 77"],
        )
    )

    assert "Сканер готов" in screen._scanner_status.text()  # noqa: SLF001
    assert "Коробка:" in screen._found.text()  # noqa: SLF001
    assert "Коробки" in screen._found_hint.text()  # noqa: SLF001
    assert screen._reset_button.toolTip()  # noqa: SLF001
    assert screen._reset_button.isEnabled() is True  # noqa: SLF001


def test_defect_screen_shows_processed_code() -> None:
    """Проверяет современный scanner-only экран брака."""

    qapp()
    screen = DefectScreen()
    screen.apply_runtime_snapshot(
        RuntimeSnapshot(
            scanner=ScannerState(
                status=ScannerStatus.RUNNING,
                port="/dev/rfcomm0",
            )
        )
    )
    screen.apply_state(
        DefectUiState(
            status_message="Код обработан",
            result_message="Код отправлен в брак",
            last_visible_code="010460123456789021SERIAL",
            order_name="26-0001",
            device_name="Device",
            removed_box_message="Удалено из коробки #10 | SSCC | остаток 3",
            warnings=["Проверить этикетку"],
            log=["010460123456789021SERIAL: Код отправлен в брак"],
        )
    )

    assert "Сканер готов" in screen._scanner_status.text()  # noqa: SLF001
    assert "Проверить этикетку" in screen._warnings.text()  # noqa: SLF001
    assert "Код отправлен" in screen._result.text()  # noqa: SLF001


def test_verify_screen_shows_processed_code() -> None:
    """Проверяет современный scanner-only экран проверки."""

    qapp()
    screen = VerifyScreen()
    screen.apply_runtime_snapshot(
        RuntimeSnapshot(
            scanner=ScannerState(
                status=ScannerStatus.RUNNING,
                port="/dev/rfcomm0",
            )
        )
    )
    screen.apply_state(
        VerifyUiState(
            status_message="Код обработан",
            result_message="Код найден",
            last_visible_code="010460123456789021SERIAL",
            technical_status="OK",
            order_name="26-0001",
            device_name="Device",
            box_id=101,
            box_sscc="SSCC-101",
            box_status="закрыта",
            box_hint="Код уже лежит в закрытой коробке #101. SSCC: SSCC-101",
            exists=True,
            warnings=["Повторная проверка"],
            log=["010460123456789021SERIAL: Код найден"],
        )
    )

    assert "Сканер готов" in screen._scanner_status.text()  # noqa: SLF001
    assert "Код найден" in screen._result.text()  # noqa: SLF001
    assert "код найден" in screen._exists.text()  # noqa: SLF001
    assert "SSCC-101" in screen._box.text()  # noqa: SLF001
    assert "закрыта" in screen._box_status.text()  # noqa: SLF001
    assert "SSCC-101" in screen._box_hint.text()  # noqa: SLF001
    assert "Повторная проверка" in screen._warnings.text()  # noqa: SLF001


def test_verify_screen_emits_duplicate_check_toggle() -> None:
    """Проверяет переключатель учета дублей на экране проверки."""

    qapp()
    screen = VerifyScreen()
    changed: list[bool] = []
    screen.duplicate_check_changed.connect(changed.append)

    screen.apply_state(VerifyUiState(check_duplicates=True))
    checkbox = screen.findChild(QCheckBox, "verifyDuplicateCheck")

    assert checkbox is not None
    assert checkbox.isChecked() is True

    checkbox.setChecked(False)

    assert changed == [False]


def test_diagnostics_screen_shows_runtime_and_logs() -> None:
    """Проверяет современный экран диагностики."""

    qapp()
    screen = DiagnosticsScreen()
    screen.apply_state(
        DiagnosticsUiState(
            api_base_url="http://backend/api/v2/",
            websocket_url="ws://backend/ws/",
            device_id="pc-1",
            data_dir="/tmp/app",
            log_file="/tmp/app/desktop.log",
            log_text="line one\nline two",
            status_message="Логи обновлены",
        )
    )
    screen.apply_runtime_snapshot(
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
                port="/dev/rfcomm0",
                message="Сканер читает порт",
            ),
        )
    )

    assert "backend" in screen._backend_value.text()  # noqa: SLF001
    assert "Связь подключена" in screen._connection_value.text()  # noqa: SLF001
    assert "Сессия активна" in screen._session_value.text()  # noqa: SLF001
    assert "Сканер работает" in screen._scanner_value.text()  # noqa: SLF001
    assert screen._refresh_button.toolTip()  # noqa: SLF001
    assert "line two" in screen._log_view.toPlainText()  # noqa: SLF001


def test_diagnostics_screen_emits_clear_logs() -> None:
    """Проверяет сигнал очистки логов из диагностики."""

    qapp()
    screen = DiagnosticsScreen()
    requests: list[bool] = []
    screen.logs_clear_requested.connect(lambda: requests.append(True))

    screen._clear_button.click()  # noqa: SLF001

    assert requests == [True]


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
                items=[
                    PackingItemUi(
                        id=1,
                        gtin="04601234567890",
                        serial="ABC123",
                        visible_code="04601234567890ABC123\x1d91ABC",
                    )
                ],
            ),
            status_message="Код добавлен",
            result_message="OK",
            last_scanned_code="04601234567890ABC123",
        )
    )
    clear_requests: list[bool] = []
    screen.clear_box_requested.connect(lambda: clear_requests.append(True))

    assert screen._progress_bar.value() == 1  # noqa: SLF001
    assert screen._items_table.rowCount() == 1  # noqa: SLF001
    assert screen._items_table.item(0, 3).text() == "04601234567890ABC123<GS>91ABC"  # noqa: SLF001
    assert screen._close_box_button.isEnabled() is True  # noqa: SLF001
    assert screen._summary_card._clear_box_button.isEnabled() is True  # noqa: SLF001
    assert screen._summary_card._choose_order_button.isEnabled() is False  # noqa: SLF001

    screen._summary_card._clear_box_button.click()  # noqa: SLF001

    assert clear_requests == [True]


def test_settings_screen_shows_printer_selection() -> None:
    """Проверяет выбор SSCC-принтера на странице настроек."""

    qapp()
    screen = SettingsScreen()
    screen.apply_printer_state(
        PrinterUiState(
            options=[PrinterOptionUi(id=7, label="Zebra")],
            selected_printer_id=7,
            status_message="Выбран принтер: Zebra",
        )
    )

    assert screen._printer_page._printer_combo.count() == 1  # noqa: SLF001
    assert screen._printer_page._printer_combo.currentText() == "Zebra"  # noqa: SLF001
    assert "Zebra" in screen._printer_page._status_label.text()  # noqa: SLF001


def test_close_box_dialog_uses_android_assets() -> None:
    """Проверяет модалку результата закрытия коробки с картинкой."""

    qapp()
    dialog = CloseBoxDialog(
        CloseBoxUiEvent(
            ok=True,
            box_id=42,
            sscc="046012345678901234",
            filled=10,
            capacity=10,
            is_full=True,
            title="Коробка закрыта",
            message="Коробка #42 закрыта",
        )
    )

    image = dialog.findChild(QLabel, "closeBoxDialogImage")

    assert image is not None
    assert image.pixmap() is not None
    assert image.pixmap().isNull() is False
    assert dialog.minimumWidth() >= 760


def test_close_box_confirm_dialog_has_primary_box_image() -> None:
    """Проверяет модалку подтверждения закрытия неполной коробки."""

    qapp()
    dialog = CloseBoxConfirmDialog(filled=4, capacity=10)

    image = dialog.findChild(QLabel, "closeBoxDialogImage")

    assert image is not None
    assert image.pixmap() is not None
    assert image.pixmap().isNull() is False
    assert dialog.minimumWidth() >= 720


def test_close_box_progress_dialog_has_indeterminate_progress() -> None:
    """Проверяет модалку ожидания закрытия коробки."""

    qapp()
    dialog = CloseBoxProgressDialog()
    progress = dialog.findChild(QProgressBar, "closeBoxProgressBar")

    assert progress is not None
    assert progress.minimum() == 0
    assert progress.maximum() == 0


def test_settings_saved_dialog_has_svg_backdrop_and_ok_button() -> None:
    """Проверяет красивую модалку успешного сохранения настроек."""

    qapp()
    dialog = SettingsSavedDialog("Настройки сохранены")

    backdrop = dialog.findChild(SvgBackdrop, "settingsSavedSvgBackdrop")
    ok_button = dialog.findChild(QPushButton, "settingsSavedButton")

    assert backdrop is not None
    assert backdrop.pixmap() is not None
    assert backdrop.pixmap().isNull() is False
    assert ok_button is not None
    assert ok_button.text() == "OK"
    assert dialog.minimumWidth() >= 700


def test_settings_screen_has_grouped_pages() -> None:
    """Проверяет, что настройки разнесены по страницам."""

    qapp()
    screen = SettingsScreen()

    assert screen._stack.count() == 6  # noqa: SLF001
    assert "Backend" in screen._hub_page.findChildren(QPushButton)[0].text()  # noqa: SLF001
    assert len(screen._theme_page.findChildren(ThemeOptionCard)) == 10  # noqa: SLF001


def test_settings_theme_card_emits_immediate_selection() -> None:
    """Проверяет выбор темы кликом без кнопки сохранения."""

    qapp()
    screen = SettingsScreen()
    selected: list[str] = []
    screen.theme_selected.connect(selected.append)
    screen.apply_settings_state(
        SettingsUiState(
            api_base_url="http://backend/api/v2/",
            device_id="pc-1",
            language="ru",
            theme_name="light",
            sound_enabled=True,
            sound_volume=0.85,
            sound_ok_file="ok_02.mp3",
            sound_warning_file="other.mp3",
            sound_error_file="error.mp3",
            sound_victory_file="victory.mp3",
            available_sound_files=[],
        )
    )

    screen._theme_page.theme_selected.emit("graphite")  # noqa: SLF001

    assert selected == ["graphite"]
    assert screen._settings_state.theme_name == "graphite"  # noqa: SLF001


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
            language="ru",
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


def test_login_screen_emits_language_selection() -> None:
    """Проверяет выбор языка до авторизации."""

    qapp()
    screen = LoginScreen()
    selected: list[str] = []
    screen.language_changed.connect(selected.append)

    screen._language_select.setCurrentIndex(1)  # noqa: SLF001

    assert selected == ["en"]


def test_login_screen_has_compact_minimum_size() -> None:
    """Проверяет, что логин не требует большой монитор."""

    qapp()
    screen = LoginScreen()

    assert screen.minimumWidth() <= 640
    assert screen.minimumHeight() <= 460


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
    assert widget._version_label.text() == "Версия: v1.0.1"  # noqa: SLF001


def test_existing_widgets_retranslate_after_language_change() -> None:
    """Проверяет смену языка без пересоздания основных виджетов."""

    qapp()
    set_current_language("ru")
    main = MainScreen()
    assert main._workspace_title.text() == "Операционный центр"  # noqa: SLF001

    set_current_language("zh")
    main.retranslate()
    assert main._workspace_title.text() == "运营中心"  # noqa: SLF001
    assert main._nav_items[0]._title.text() == "包装"  # noqa: SLF001

    set_current_language("ru")
    login = LoginScreen()
    assert login._manual_button.text() == "Войти"  # noqa: SLF001

    set_current_language("en")
    retranslate_widget_tree(login)
    assert login._manual_button.text() == "Sign in"  # noqa: SLF001

    login.set_language("zh")
    assert login._language_select.currentData() == "zh"  # noqa: SLF001


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
