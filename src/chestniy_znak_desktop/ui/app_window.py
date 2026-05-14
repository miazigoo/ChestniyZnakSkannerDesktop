"""Главное окно desktop-приложения."""

from __future__ import annotations

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditController
from chestniy_znak_desktop.controllers.boxes_controller import BoxesController
from chestniy_znak_desktop.controllers.defect_controller import DefectController
from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsController
from chestniy_znak_desktop.controllers.packing_controller import PackingController
from chestniy_znak_desktop.controllers.printer_controller import PrinterController
from chestniy_znak_desktop.controllers.scanner_controller import ScannerController
from chestniy_znak_desktop.controllers.settings_controller import SettingsController
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.ui.screens.login_screen import LoginScreen
from chestniy_znak_desktop.ui.screens.main_screen import MainScreen
from chestniy_znak_desktop.ui.widgets.blocking_overlay import BlockingOverlay
from chestniy_znak_desktop.ui.widgets.runtime_status_bar import RuntimeStatusBar


class AppWindow(QMainWindow):
    """Главное окно с навигацией между экранами приложения."""

    def __init__(
        self,
        app_state: AppState,
        runtime_controller: RuntimeController,
        auth_controller: AuthController,
        packing_controller: PackingController,
        boxes_controller: BoxesController,
        box_edit_controller: BoxEditController,
        defect_controller: DefectController,
        diagnostics_controller: DiagnosticsController,
        printer_controller: PrinterController,
        scanner_controller: ScannerController,
        settings_controller: SettingsController,
    ) -> None:
        """Создает главное окно и регистрирует стартовые экраны."""

        super().__init__()
        self._app_state = app_state
        self._runtime_controller = runtime_controller
        self._auth_controller = auth_controller
        self._packing_controller = packing_controller
        self._boxes_controller = boxes_controller
        self._box_edit_controller = box_edit_controller
        self._defect_controller = defect_controller
        self._diagnostics_controller = diagnostics_controller
        self._printer_controller = printer_controller
        self._scanner_controller = scanner_controller
        self._settings_controller = settings_controller
        self._scan_target = "packing"
        self._central = QWidget()
        self._stack = QStackedWidget()
        self._status_bar = RuntimeStatusBar()
        self._login_screen = LoginScreen()
        self._main_screen = MainScreen()
        self._stack.addWidget(self._login_screen)
        self._stack.addWidget(self._main_screen)
        layout = QVBoxLayout(self._central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._status_bar)
        layout.addWidget(self._stack, stretch=1)
        self.setCentralWidget(self._central)
        self._blocking_overlay = BlockingOverlay(self._central)
        self._blocking_overlay.retry_requested.connect(self._runtime_controller.retry_connection)
        self._runtime_controller.snapshot_changed.connect(self._status_bar.update_snapshot)
        self._runtime_controller.snapshot_changed.connect(self._login_screen.apply_runtime_snapshot)
        self._runtime_controller.snapshot_changed.connect(self._main_screen.apply_runtime_snapshot)
        self._runtime_controller.blocking_changed.connect(self._set_work_area_blocking)
        self._auth_controller.state_changed.connect(self._login_screen.apply_state)
        self._auth_controller.authenticated.connect(lambda _user: self.show_main_screen())
        self._auth_controller.unauthenticated.connect(self.show_login_screen)
        self._main_screen.logout_requested.connect(self._auth_controller.logout)
        self._main_screen.screen_changed.connect(self._set_scan_target)
        self._packing_controller.state_changed.connect(self._main_screen.packing_screen.apply_state)
        self._defect_controller.state_changed.connect(self._main_screen.defect_screen.apply_state)
        self._diagnostics_controller.state_changed.connect(
            self._main_screen.diagnostics_screen.apply_state
        )
        self._main_screen.diagnostics_screen.logs_refresh_requested.connect(
            self._diagnostics_controller.refresh_logs
        )
        self._printer_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_printer_state
        )
        self._boxes_controller.state_changed.connect(self._main_screen.boxes_screen.apply_state)
        self._box_edit_controller.state_changed.connect(
            self._main_screen.boxes_screen.apply_edit_state
        )
        self._box_edit_controller.box_changed.connect(self._boxes_controller.load_detail)
        self._box_edit_controller.box_deleted.connect(
            lambda _box_id: self._boxes_controller.refresh()
        )
        self._main_screen.boxes_screen.refresh_requested.connect(self._boxes_controller.refresh)
        self._main_screen.boxes_screen.search_requested.connect(self._boxes_controller.set_query)
        self._main_screen.boxes_screen.status_filter_changed.connect(
            self._boxes_controller.set_status_filter
        )
        self._main_screen.boxes_screen.next_page_requested.connect(self._boxes_controller.next_page)
        self._main_screen.boxes_screen.previous_page_requested.connect(
            self._boxes_controller.previous_page
        )
        self._main_screen.boxes_screen.box_detail_requested.connect(
            self._boxes_controller.load_detail
        )
        self._main_screen.boxes_screen.print_label_requested.connect(
            self._boxes_controller.print_selected_label
        )
        self._main_screen.boxes_screen.edit_open_requested.connect(
            self._box_edit_controller.open_edit
        )
        self._main_screen.boxes_screen.edit_close_requested.connect(
            self._box_edit_controller.close_edit
        )
        self._main_screen.boxes_screen.remove_item_requested.connect(
            self._box_edit_controller.remove_item
        )
        self._main_screen.boxes_screen.clear_box_requested.connect(
            self._box_edit_controller.clear_box
        )
        self._main_screen.boxes_screen.delete_empty_box_requested.connect(
            self._box_edit_controller.delete_empty_box
        )
        self._main_screen.packing_screen.refresh_requested.connect(
            self._packing_controller.refresh_current_box
        )
        self._main_screen.packing_screen.open_box_requested.connect(
            self._packing_controller.open_box
        )
        self._main_screen.packing_screen.close_box_requested.connect(
            self._packing_controller.close_current_box
        )
        self._main_screen.packing_screen.count_in_packing_changed.connect(
            self._packing_controller.set_count_in_packing
        )
        self._scanner_controller.code_scanned.connect(self._handle_scanned_code)
        self._scanner_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_scanner_state
        )
        self._settings_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_settings_state
        )
        self._main_screen.settings_screen.settings_save_requested.connect(
            self._settings_controller.save_form
        )
        self._main_screen.settings_screen.printer_refresh_requested.connect(
            self._printer_controller.refresh
        )
        self._main_screen.settings_screen.printer_selected.connect(
            self._printer_controller.select_printer
        )
        self._main_screen.settings_screen.scanner_ports_refresh_requested.connect(
            self._scanner_controller.refresh_ports
        )
        self._main_screen.settings_screen.scanner_start_requested.connect(
            self._scanner_controller.start
        )
        self._main_screen.settings_screen.scanner_stop_requested.connect(
            self._scanner_controller.stop
        )
        self._main_screen.settings_screen.scanner_port_changed.connect(
            self._scanner_controller.set_selected_port
        )
        self._main_screen.settings_screen.scanner_port_changed.connect(
            self._settings_controller.set_scanner_port
        )
        self._main_screen.settings_screen.scanner_baudrate_changed.connect(
            self._scanner_controller.set_baudrate
        )
        self._main_screen.settings_screen.scanner_baudrate_changed.connect(
            self._settings_controller.set_scanner_baudrate
        )
        self.setWindowTitle(app_state.config.app_name)
        self.resize(1180, 760)

    def show_login_screen(self) -> None:
        """Переключает окно на экран авторизации."""

        self._stack.setCurrentWidget(self._login_screen)
        self._blocking_overlay.set_blocking(False, "")

    def show_main_screen(self) -> None:
        """Переключает окно на главный рабочий экран."""

        self._stack.setCurrentWidget(self._main_screen)

    def _set_work_area_blocking(self, is_blocking: bool, message: str) -> None:
        """Блокирует только рабочие экраны, оставляя логин доступным."""

        if self._stack.currentWidget() is self._login_screen:
            self._blocking_overlay.set_blocking(False, "")
            return
        self._blocking_overlay.set_blocking(is_blocking, message)

    def _set_scan_target(self, screen_name: str) -> None:
        """Сохраняет активный рабочий сценарий для входящих сканов."""

        self._scan_target = screen_name

    def _handle_scanned_code(self, code: str) -> None:
        """Маршрутизирует код сканера в активный рабочий сценарий."""

        if self._stack.currentWidget() is self._login_screen:
            self._auth_controller.login_with_raw_token(code)
            return
        if self._scan_target == "defect":
            self._defect_controller.on_code_scanned(code)
            return
        if self._scan_target == "packing":
            self._packing_controller.on_code_scanned(code)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Подгоняет blocking overlay под размер центрального виджета."""

        super().resizeEvent(event)
        self._blocking_overlay.setGeometry(self._central.rect())
