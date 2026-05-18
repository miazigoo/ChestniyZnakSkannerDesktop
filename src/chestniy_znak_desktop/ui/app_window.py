"""Главное окно desktop-приложения."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.auth_controller import AuthController
from chestniy_znak_desktop.controllers.auto_packing_controller import AutoPackingController
from chestniy_znak_desktop.controllers.box_edit_controller import BoxEditController
from chestniy_znak_desktop.controllers.box_lookup_controller import BoxLookupController
from chestniy_znak_desktop.controllers.boxes_controller import BoxesController
from chestniy_znak_desktop.controllers.defect_controller import DefectController
from chestniy_znak_desktop.controllers.diagnostics_controller import DiagnosticsController
from chestniy_znak_desktop.controllers.packing_controller import CloseBoxUiEvent, PackingController
from chestniy_znak_desktop.controllers.printer_controller import PrinterController
from chestniy_znak_desktop.controllers.scanner_controller import ScannerController
from chestniy_znak_desktop.controllers.settings_controller import SettingsController
from chestniy_znak_desktop.controllers.verify_controller import VerifyController
from chestniy_znak_desktop.domain.scanner_input_guard import contains_cyrillic
from chestniy_znak_desktop.runtime.app_state import AppState
from chestniy_znak_desktop.runtime.runtime_controller import RuntimeController
from chestniy_znak_desktop.services.scanner_command_service import (
    ScannerCommand,
    parse_scanner_command,
)
from chestniy_znak_desktop.ui.screens.login_screen import LoginScreen
from chestniy_znak_desktop.ui.screens.main_screen import MainScreen
from chestniy_znak_desktop.ui.widgets.blocking_overlay import BlockingOverlay
from chestniy_znak_desktop.ui.widgets.close_box_dialog import (
    CloseBoxConfirmDialog,
    CloseBoxDialog,
    CloseBoxProgressDialog,
)
from chestniy_znak_desktop.ui.widgets.runtime_status_bar import RuntimeStatusBar
from chestniy_znak_desktop.ui.widgets.settings_saved_dialog import SettingsSavedDialog


class AppWindow(QMainWindow):
    """Главное окно с навигацией между экранами приложения."""

    def __init__(
        self,
        app_state: AppState,
        runtime_controller: RuntimeController,
        auth_controller: AuthController,
        packing_controller: PackingController,
        auto_packing_controller: AutoPackingController,
        boxes_controller: BoxesController,
        box_lookup_controller: BoxLookupController,
        box_edit_controller: BoxEditController,
        defect_controller: DefectController,
        verify_controller: VerifyController,
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
        self._auto_packing_controller = auto_packing_controller
        self._boxes_controller = boxes_controller
        self._box_lookup_controller = box_lookup_controller
        self._box_edit_controller = box_edit_controller
        self._defect_controller = defect_controller
        self._verify_controller = verify_controller
        self._diagnostics_controller = diagnostics_controller
        self._printer_controller = printer_controller
        self._scanner_controller = scanner_controller
        self._settings_controller = settings_controller
        self._scan_target = "packing"
        self._suppress_next_screen_refresh = False
        self._central = QWidget()
        self._stack = QStackedWidget()
        self._status_bar = RuntimeStatusBar()
        self._login_screen = LoginScreen()
        self._main_screen = MainScreen()
        self._close_box_dialogs: list[CloseBoxDialog] = []
        self._settings_saved_dialog: SettingsSavedDialog | None = None
        self._close_progress_dialog: CloseBoxProgressDialog | None = None
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
        self._main_screen.screen_changed.connect(self._handle_screen_changed)
        self._packing_controller.state_changed.connect(self._main_screen.packing_screen.apply_state)
        self._packing_controller.close_completed.connect(self._handle_box_close_completed)
        self._auto_packing_controller.state_changed.connect(
            self._main_screen.auto_packing_screen.apply_state
        )
        self._auto_packing_controller.close_completed.connect(self._handle_auto_box_close_completed)
        self._box_lookup_controller.state_changed.connect(
            self._main_screen.box_lookup_screen.apply_state
        )
        self._box_lookup_controller.box_found.connect(self._open_found_box)
        self._verify_controller.state_changed.connect(self._main_screen.verify_screen.apply_state)
        self._main_screen.verify_screen.duplicate_check_changed.connect(
            self._verify_controller.set_check_duplicates
        )
        self._defect_controller.state_changed.connect(self._main_screen.defect_screen.apply_state)
        self._diagnostics_controller.state_changed.connect(
            self._main_screen.diagnostics_screen.apply_state
        )
        self._main_screen.diagnostics_screen.logs_refresh_requested.connect(
            self._diagnostics_controller.refresh_logs
        )
        self._main_screen.diagnostics_screen.logs_clear_requested.connect(
            self._diagnostics_controller.clear_logs
        )
        self._printer_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_printer_state
        )
        self._boxes_controller.state_changed.connect(self._main_screen.boxes_screen.apply_state)
        self._box_edit_controller.state_changed.connect(
            self._main_screen.boxes_screen.apply_edit_state
        )
        self._box_edit_controller.box_changed.connect(self._handle_box_changed)
        self._box_edit_controller.box_deleted.connect(self._handle_box_deleted)
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
        self._main_screen.box_lookup_screen.reset_requested.connect(
            self._box_lookup_controller.reset_status
        )
        self._main_screen.packing_screen.refresh_requested.connect(
            self._packing_controller.refresh_current_box
        )
        self._main_screen.packing_screen.open_box_requested.connect(
            self._packing_controller.open_box
        )
        self._main_screen.packing_screen.close_box_requested.connect(
            self._request_close_current_box
        )
        self._main_screen.packing_screen.count_in_packing_changed.connect(
            self._packing_controller.set_count_in_packing
        )
        self._main_screen.auto_packing_screen.refresh_requested.connect(
            self._auto_packing_controller.refresh_current_box
        )
        self._main_screen.auto_packing_screen.open_box_requested.connect(
            self._auto_packing_controller.open_box
        )
        self._main_screen.auto_packing_screen.close_box_requested.connect(
            self._request_auto_close_current_box
        )
        self._main_screen.auto_packing_screen.count_in_packing_changed.connect(
            self._auto_packing_controller.set_count_in_packing
        )
        self._main_screen.auto_packing_screen.clear_pending_requested.connect(
            self._auto_packing_controller.clear_pending
        )
        self._main_screen.auto_packing_screen.remove_pending_requested.connect(
            self._auto_packing_controller.remove_pending_at
        )
        self._main_screen.auto_packing_screen.remove_box_item_requested.connect(
            self._request_auto_remove_box_item
        )
        self._main_screen.auto_packing_screen.clear_box_requested.connect(
            self._request_auto_clear_box
        )
        self._main_screen.auto_packing_screen.delete_box_requested.connect(
            self._request_auto_delete_box
        )
        self._main_screen.auto_packing_screen.codes_per_item_changed.connect(
            self._auto_packing_controller.set_codes_per_item
        )
        self._scanner_controller.code_scanned.connect(self._handle_scanned_code)
        self._scanner_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_scanner_state
        )
        self._settings_controller.state_changed.connect(
            self._main_screen.settings_screen.apply_settings_state
        )
        self._settings_controller.settings_saved.connect(self._show_settings_saved_dialog)
        self._main_screen.settings_screen.settings_save_requested.connect(
            self._settings_controller.save_form
        )
        self._main_screen.settings_screen.theme_selected.connect(
            self._settings_controller.set_theme
        )
        self._main_screen.settings_screen.sound_preview_requested.connect(
            self._settings_controller.preview_sound_file
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
        self.setMinimumSize(QSize(640, 460))
        self.setWindowTitle(app_state.config.app_name)
        self._resize_to_available_screen(QSize(1180, 760))

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

    def _handle_screen_changed(self, screen_name: str) -> None:
        """Обновляет активный сценарий и подтягивает актуальные данные экрана."""

        previous_screen = self._scan_target
        if previous_screen != screen_name:
            self._clear_inactive_screen_data(previous_screen)
        self._set_scan_target(screen_name)
        if self._suppress_next_screen_refresh:
            self._suppress_next_screen_refresh = False
            return
        if self._stack.currentWidget() is not self._main_screen:
            return
        self._refresh_screen_data(screen_name)

    def _refresh_screen_data(self, screen_name: str) -> None:
        """Запускает обновление данных для выбранного рабочего экрана."""

        if screen_name == "packing":
            self._packing_controller.refresh_current_box()
            return
        if screen_name == "auto_packing":
            self._auto_packing_controller.refresh_current_box()
            return
        if screen_name == "boxes":
            selected_box_id = self._boxes_controller.state.selected_box_id
            self._boxes_controller.refresh()
            if selected_box_id is not None:
                self._boxes_controller.load_detail(selected_box_id)
            return
        if screen_name == "diagnostics":
            self._diagnostics_controller.refresh_logs()
            return
        if screen_name == "settings":
            self._settings_controller.publish_state()
            self._printer_controller.refresh()
            self._scanner_controller.refresh_ports()

    def _clear_inactive_screen_data(self, screen_name: str) -> None:
        """Освобождает данные экранов, которые больше не активны."""

        if screen_name == "boxes":
            self._boxes_controller.clear_loaded_data()
            return
        if screen_name == "box_lookup":
            self._box_lookup_controller.clear_state()
            return
        if screen_name == "defect":
            self._defect_controller.clear_state()

    def _open_found_box(self, box_id: int) -> None:
        """Открывает найденную коробку в рабочем экране коробок."""

        self._main_screen.show_boxes()
        self._boxes_controller.load_detail(box_id)

    def _request_close_current_box(self) -> None:
        """Запрашивает закрытие коробки с подтверждением неполного заполнения."""

        self._show_packing_without_refresh()
        state = self._packing_controller.state
        box = state.current_box
        if state.is_busy:
            self._show_message("Операция выполняется", state.status_message)
            return
        if box is None:
            self._show_message("Коробка не открыта", "Сначала откройте коробку.")
            return
        if box.filled < box.capacity and not self._confirm_incomplete_box(box.filled, box.capacity):
            return
        self._show_close_progress_dialog()
        self._packing_controller.close_current_box()

    def _confirm_incomplete_box(self, filled: int, capacity: int) -> bool:
        """Просит подтверждение закрытия неполной коробки."""

        dialog = CloseBoxConfirmDialog(filled, capacity, self)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _show_message(self, title: str, text: str) -> None:
        """Показывает короткое информационное сообщение."""

        QMessageBox.information(self, title, text)

    def _request_auto_remove_box_item(self, row: int) -> None:
        """Запрашивает удаление выбранного кода из открытой коробки автоскана."""

        state = self._auto_packing_controller.state
        box = state.current_box
        if box is None or row < 0 or row >= len(box.items):
            self._show_message("Код не выбран", "Выберите код во вкладке текущей коробки.")
            return
        item = box.items[row]
        if self._confirm_action(
            "Удалить код из коробки",
            f"Удалить код #{item.id} из открытой коробки #{box.box_id}?",
        ):
            self._auto_packing_controller.remove_box_item_at(row)

    def _request_auto_clear_box(self) -> None:
        """Запрашивает очистку текущей открытой коробки автоскана."""

        box = self._auto_packing_controller.state.current_box
        if box is None:
            self._show_message("Коробка не открыта", "Открытая коробка не найдена.")
            return
        if self._confirm_action(
            "Очистить коробку",
            f"Удалить все коды из открытой коробки #{box.box_id}?",
        ):
            self._auto_packing_controller.clear_current_box()

    def _request_auto_delete_box(self) -> None:
        """Запрашивает удаление текущей пустой открытой коробки автоскана."""

        box = self._auto_packing_controller.state.current_box
        if box is None:
            self._show_message("Коробка не открыта", "Открытая коробка не найдена.")
            return
        if box.filled > 0:
            self._show_message(
                "Коробка не пустая",
                "Перед удалением коробки удалите коды или очистите коробку.",
            )
            return
        if self._confirm_action(
            "Удалить пустую коробку",
            f"Удалить открытую пустую коробку #{box.box_id}?",
        ):
            self._auto_packing_controller.delete_current_box()

    def _request_auto_close_current_box(self) -> None:
        """Запрашивает закрытие текущей коробки автоскана."""

        state = self._auto_packing_controller.state
        box = state.current_box
        if state.is_busy:
            self._show_message("Операция выполняется", state.status_message)
            return
        if box is None:
            self._show_message("Коробка не открыта", "Сначала откройте коробку.")
            return
        if state.pending_items:
            self._show_message(
                "Локальный бокс не пуст",
                "Сначала отправьте заполненный автоскана-бокс или очистите его.",
            )
            return
        if box.filled < box.capacity and not self._confirm_incomplete_box(box.filled, box.capacity):
            return
        self._show_close_progress_dialog()
        self._auto_packing_controller.close_current_box()

    def _confirm_action(self, title: str, text: str) -> bool:
        """Показывает подтверждение опасного действия."""

        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _handle_box_close_completed(self, event: CloseBoxUiEvent) -> None:
        """Показывает результат закрытия и открывает следующую коробку."""

        self._hide_close_progress_dialog()
        dialog = CloseBoxDialog(event, self)
        self._close_box_dialogs.append(dialog)
        dialog.finished.connect(lambda _code, dialog=dialog: self._forget_close_dialog(dialog))
        dialog.open()
        if event.ok:
            self._packing_controller.open_box()

    def _handle_auto_box_close_completed(self, event: CloseBoxUiEvent) -> None:
        """Показывает результат закрытия автоскана и открывает новую коробку."""

        self._hide_close_progress_dialog()
        dialog = CloseBoxDialog(event, self)
        self._close_box_dialogs.append(dialog)
        dialog.finished.connect(lambda _code, dialog=dialog: self._forget_close_dialog(dialog))
        dialog.open()
        if event.ok:
            self._auto_packing_controller.open_box()

    def _handle_box_changed(self, box_id: int) -> None:
        """Обновляет список и карточку после редактирования коробки."""

        self._boxes_controller.refresh()
        self._boxes_controller.load_detail(box_id)

    def _handle_box_deleted(self, _box_id: int) -> None:
        """Сбрасывает карточку и обновляет список после удаления коробки."""

        self._boxes_controller.clear_detail("Коробка удалена")
        self._boxes_controller.refresh()

    def _show_close_progress_dialog(self) -> None:
        """Показывает модалку ожидания закрытия коробки."""

        if self._close_progress_dialog is not None:
            return
        dialog = CloseBoxProgressDialog(self)
        self._close_progress_dialog = dialog
        dialog.finished.connect(lambda _code: self._clear_close_progress_dialog(dialog))
        dialog.open()

    def _hide_close_progress_dialog(self) -> None:
        """Закрывает модалку ожидания закрытия коробки."""

        dialog = self._close_progress_dialog
        if dialog is None:
            return
        self._close_progress_dialog = None
        dialog.accept()

    def _clear_close_progress_dialog(self, dialog: CloseBoxProgressDialog) -> None:
        """Очищает ссылку на закрытую модалку прогресса."""

        if self._close_progress_dialog is dialog:
            self._close_progress_dialog = None

    def _forget_close_dialog(self, dialog: CloseBoxDialog) -> None:
        """Удаляет закрытую модалку из списка активных окон."""

        if dialog in self._close_box_dialogs:
            self._close_box_dialogs.remove(dialog)

    def _show_settings_saved_dialog(self, message: str) -> None:
        """Показывает модалку успешного сохранения настроек."""

        if self._settings_saved_dialog is not None:
            self._settings_saved_dialog.accept()
        dialog = SettingsSavedDialog(message, self)
        self._settings_saved_dialog = dialog
        dialog.finished.connect(
            lambda _code, dialog=dialog: self._forget_settings_saved_dialog(dialog)
        )
        dialog.open()

    def _forget_settings_saved_dialog(self, dialog: SettingsSavedDialog) -> None:
        """Удаляет закрытую модалку сохранения настроек из списка."""

        if self._settings_saved_dialog is dialog:
            self._settings_saved_dialog = None

    def _show_packing_without_refresh(self) -> None:
        """Показывает упаковку перед быстрым действием без автообновления."""

        self._suppress_next_screen_refresh = True
        self._main_screen.show_packing()

    def _handle_scanned_code(self, code: str) -> None:
        """Маршрутизирует код сканера в активный рабочий сценарий."""

        if contains_cyrillic(code):
            self._show_cyrillic_scan_warning()
            return
        command = parse_scanner_command(code)
        if command is not None and self._handle_scanner_command(command):
            return
        if self._stack.currentWidget() is self._login_screen:
            self._auth_controller.login_with_raw_token(code)
            return
        if self._scan_target == "defect":
            self._defect_controller.on_code_scanned(code)
            return
        if self._scan_target == "box_lookup":
            self._box_lookup_controller.on_code_scanned(code)
            return
        if self._scan_target == "verify":
            self._verify_controller.on_code_scanned(code)
            return
        if self._scan_target == "packing":
            self._packing_controller.on_code_scanned(code)
            return
        if self._scan_target == "auto_packing":
            self._auto_packing_controller.on_code_scanned(code)

    def _show_cyrillic_scan_warning(self) -> None:
        """Предупреждает оператора, что скан пришел в русской раскладке."""

        QMessageBox.warning(
            self,
            "Неверная раскладка",
            "Скан отклонен: в коде есть кириллица. Переключите раскладку на EN "
            "и повторите сканирование.",
        )

    def _handle_scanner_command(self, command: ScannerCommand) -> bool:
        """Выполняет служебную QR-команду сканера."""

        if command == ScannerCommand.CONFIRM_OK:
            self._confirm_active_dialog()
            return True
        if self._stack.currentWidget() is self._login_screen:
            return True
        if command == ScannerCommand.OPEN_NEW_BOX:
            self._show_packing_without_refresh()
            self._packing_controller.open_box()
            return True
        self._request_close_current_box()
        return True

    @staticmethod
    def _confirm_active_dialog() -> bool:
        """Подтверждает активный модальный диалог, если он открыт."""

        active_modal = QApplication.activeModalWidget()
        if isinstance(active_modal, QMessageBox):
            for button in (
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Apply,
                QMessageBox.StandardButton.Save,
            ):
                widget = active_modal.button(button)
                if widget is not None:
                    widget.click()
                    return True
        if isinstance(active_modal, CloseBoxProgressDialog):
            return False
        if isinstance(active_modal, QDialog):
            active_modal.accept()
            return True
        return False

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Подгоняет blocking overlay под размер центрального виджета."""

        super().resizeEvent(event)
        self._blocking_overlay.setGeometry(self._central.rect())

    def _resize_to_available_screen(self, preferred_size: QSize) -> None:
        """Задает стартовый размер окна с учетом доступной области экрана."""

        screen = self.screen()
        available = screen.availableGeometry()
        width = min(preferred_size.width(), max(640, available.width() - 40))
        height = min(preferred_size.height(), max(460, available.height() - 40))
        width = min(width, available.width())
        height = min(height, available.height())
        self.resize(width, height)
        self.move(
            available.x() + max(0, (available.width() - width) // 2),
            available.y() + max(0, (available.height() - height) // 2),
        )
