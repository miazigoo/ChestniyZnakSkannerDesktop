"""Тесты автообновления рабочих экранов при навигации."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from chestniy_znak_desktop.ui.app_window import AppWindow


class FakeStack:
    """Минимальный стек с текущим виджетом для тестов AppWindow."""

    def __init__(self, current_widget: object) -> None:
        """Сохраняет текущий виджет."""

        self._current_widget = current_widget

    def currentWidget(self) -> object:
        """Возвращает текущий виджет."""

        return self._current_widget


@dataclass(slots=True)
class Counter:
    """Счетчик вызовов refresh-методов."""

    count: int = 0

    def refresh(self) -> None:
        """Увеличивает счетчик refresh."""

        self.count += 1

    def refresh_current_box(self) -> None:
        """Увеличивает счетчик загрузки текущей коробки."""

        self.count += 1

    def refresh_logs(self) -> None:
        """Увеличивает счетчик обновления логов."""

        self.count += 1

    def publish_state(self) -> None:
        """Увеличивает счетчик публикации состояния."""

        self.count += 1

    def refresh_ports(self) -> None:
        """Увеличивает счетчик обновления портов."""

        self.count += 1


class FakeBoxesController:
    """Fake контроллер коробок для проверки списка и деталей."""

    def __init__(self) -> None:
        """Создает fake state и списки вызовов."""

        self.state = SimpleNamespace(selected_box_id=29)
        self.refresh_count = 0
        self.loaded_details: list[int] = []
        self.clear_messages: list[str] = []
        self.clear_loaded_count = 0

    def refresh(self) -> None:
        """Запоминает обновление списка."""

        self.refresh_count += 1

    def load_detail(self, box_id: int) -> None:
        """Запоминает обновление деталей."""

        self.loaded_details.append(box_id)

    def clear_detail(self, message: str) -> None:
        """Запоминает сброс деталей."""

        self.clear_messages.append(message)

    def clear_loaded_data(self) -> None:
        """Запоминает очистку загруженного списка."""

        self.clear_loaded_count += 1


class FakeClearableController:
    """Fake контроллер с очисткой состояния экрана."""

    def __init__(self) -> None:
        """Создает счетчик очисток."""

        self.clear_count = 0

    def clear_state(self) -> None:
        """Запоминает очистку состояния."""

        self.clear_count += 1


class FakeWindow:
    """Минимальное окно для вызова методов AppWindow без полного UI."""

    def __init__(self) -> None:
        """Создает зависимости, которые нужны tested methods."""

        self._scan_target = ""
        self._main_screen = object()
        self._stack = FakeStack(self._main_screen)
        self._suppress_next_screen_refresh = False
        self._refreshes: list[str] = []
        self._cleared: list[str] = []

    def _set_scan_target(self, screen_name: str) -> None:
        """Запоминает активный экран."""

        self._scan_target = screen_name

    def _refresh_screen_data(self, screen_name: str) -> None:
        """Запоминает запрос обновления экрана."""

        self._refreshes.append(screen_name)

    def _clear_inactive_screen_data(self, screen_name: str) -> None:
        """Запоминает очистку покинутого экрана."""

        if screen_name in {"boxes", "box_lookup", "defect"}:
            self._cleared.append(screen_name)


def test_screen_change_refreshes_selected_screen() -> None:
    """Проверяет автообновление при обычном переходе."""

    window = FakeWindow()

    AppWindow._handle_screen_changed(window, "boxes")  # type: ignore[arg-type]

    assert window._scan_target == "boxes"
    assert window._refreshes == ["boxes"]
    assert window._cleared == []


def test_screen_change_clears_previous_heavy_screen() -> None:
    """Проверяет очистку данных при уходе с тяжелого экрана."""

    window = FakeWindow()
    window._scan_target = "box_lookup"

    AppWindow._handle_screen_changed(window, "packing")  # type: ignore[arg-type]

    assert window._scan_target == "packing"
    assert window._cleared == ["box_lookup"]


def test_screen_change_can_suppress_refresh_for_service_actions() -> None:
    """Проверяет подавление refresh перед быстрыми сервисными действиями."""

    window = FakeWindow()
    window._suppress_next_screen_refresh = True

    AppWindow._handle_screen_changed(window, "packing")  # type: ignore[arg-type]

    assert window._scan_target == "packing"
    assert window._refreshes == []
    assert window._suppress_next_screen_refresh is False


def test_boxes_screen_refreshes_list_and_selected_detail() -> None:
    """Проверяет обновление списка коробок и текущей детали."""

    window = SimpleNamespace(
        _packing_controller=Counter(),
        _boxes_controller=FakeBoxesController(),
        _diagnostics_controller=Counter(),
        _settings_controller=Counter(),
        _printer_controller=Counter(),
        _scanner_controller=Counter(),
    )

    AppWindow._refresh_screen_data(window, "boxes")  # type: ignore[arg-type]

    assert window._boxes_controller.refresh_count == 1
    assert window._boxes_controller.loaded_details == [29]


def test_box_changed_refreshes_list_and_detail() -> None:
    """Проверяет обновление списка и карточки после редактирования."""

    boxes_controller = FakeBoxesController()
    window = SimpleNamespace(_boxes_controller=boxes_controller)

    AppWindow._handle_box_changed(window, 42)  # type: ignore[arg-type]

    assert boxes_controller.refresh_count == 1
    assert boxes_controller.loaded_details == [42]


def test_box_deleted_clears_detail_and_refreshes_list() -> None:
    """Проверяет сброс карточки и обновление списка после удаления."""

    boxes_controller = FakeBoxesController()
    window = SimpleNamespace(_boxes_controller=boxes_controller)

    AppWindow._handle_box_deleted(window, 42)  # type: ignore[arg-type]

    assert boxes_controller.clear_messages == ["Коробка удалена"]
    assert boxes_controller.refresh_count == 1


def test_clear_inactive_screen_data_clears_screen_controllers() -> None:
    """Проверяет очистку контроллеров при уходе с экранов."""

    boxes_controller = FakeBoxesController()
    lookup_controller = FakeClearableController()
    defect_controller = FakeClearableController()
    window = SimpleNamespace(
        _boxes_controller=boxes_controller,
        _box_lookup_controller=lookup_controller,
        _defect_controller=defect_controller,
    )

    AppWindow._clear_inactive_screen_data(window, "boxes")  # type: ignore[arg-type]
    AppWindow._clear_inactive_screen_data(window, "box_lookup")  # type: ignore[arg-type]
    AppWindow._clear_inactive_screen_data(window, "defect")  # type: ignore[arg-type]

    assert boxes_controller.clear_loaded_count == 1
    assert lookup_controller.clear_count == 1
    assert defect_controller.clear_count == 1


def test_settings_screen_refreshes_device_sources() -> None:
    """Проверяет обновление настроек, принтеров и портов сканера."""

    settings = Counter()
    printer = Counter()
    scanner = Counter()
    window = SimpleNamespace(
        _packing_controller=Counter(),
        _boxes_controller=FakeBoxesController(),
        _diagnostics_controller=Counter(),
        _settings_controller=settings,
        _printer_controller=printer,
        _scanner_controller=scanner,
    )

    AppWindow._refresh_screen_data(window, "settings")  # type: ignore[arg-type]

    assert settings.count == 1
    assert printer.count == 1
    assert scanner.count == 1
