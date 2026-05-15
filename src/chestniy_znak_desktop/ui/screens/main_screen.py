"""Главный рабочий экран desktop-клиента."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.screens.box_lookup_screen import BoxLookupScreen
from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen
from chestniy_znak_desktop.ui.screens.defect_screen import DefectScreen
from chestniy_znak_desktop.ui.screens.diagnostics_screen import DiagnosticsScreen
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen
from chestniy_znak_desktop.ui.screens.verify_screen import VerifyScreen
from chestniy_znak_desktop.ui.widgets.main_navigation import MainSidebar, MainWorkspace, NavItem
from chestniy_znak_desktop.ui.widgets.user_session_panel import UserSessionPanel
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class MainScreen(QWidget):
    """Содержит рабочую навигацию после авторизации."""

    logout_requested = Signal()
    screen_changed = Signal(str)

    def __init__(self) -> None:
        """Создает современную навигацию и регистрирует рабочие экраны."""

        super().__init__()
        self.setObjectName("mainScreen")
        self._stack = QStackedWidget()
        self._stack.setObjectName("mainContentStack")
        self._stack_effect = QGraphicsOpacityEffect(self._stack)
        self._stack.setGraphicsEffect(self._stack_effect)
        self._stack_animation = QPropertyAnimation(self._stack_effect, b"opacity", self)
        self._stack_animation.setDuration(180)
        self._stack_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_items: list[NavItem] = []
        self._session_panel = UserSessionPanel()
        self._packing_screen = PackingScreen()
        self._boxes_screen = BoxesScreen()
        self._box_lookup_screen = BoxLookupScreen()
        self._verify_screen = VerifyScreen()
        self._defect_screen = DefectScreen()
        self._settings_screen = SettingsScreen()
        self._diagnostics_screen = DiagnosticsScreen()
        self._register_work_screens()
        self._session_panel.logout_requested.connect(self.logout_requested.emit)
        self._build_layout()
        self._set_active_nav("packing")

    @property
    def packing_screen(self) -> PackingScreen:
        """Возвращает экран упаковки для подключения контроллера."""

        return self._packing_screen

    @property
    def boxes_screen(self) -> BoxesScreen:
        """Возвращает экран коробок для подключения контроллера."""

        return self._boxes_screen

    @property
    def box_lookup_screen(self) -> BoxLookupScreen:
        """Возвращает экран поиска коробки для подключения контроллера."""

        return self._box_lookup_screen

    @property
    def defect_screen(self) -> DefectScreen:
        """Возвращает экран брака для подключения контроллера."""

        return self._defect_screen

    @property
    def verify_screen(self) -> VerifyScreen:
        """Возвращает экран проверки для подключения контроллера."""

        return self._verify_screen

    @property
    def settings_screen(self) -> SettingsScreen:
        """Возвращает экран настроек для подключения контроллеров."""

        return self._settings_screen

    @property
    def diagnostics_screen(self) -> DiagnosticsScreen:
        """Возвращает экран диагностики для подключения контроллера."""

        return self._diagnostics_screen

    def apply_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Обновляет рабочий экран из общего runtime snapshot."""

        self._session_panel.apply_snapshot(snapshot)
        self._packing_screen.apply_runtime_snapshot(snapshot)
        self._box_lookup_screen.apply_runtime_snapshot(snapshot)
        self._verify_screen.apply_runtime_snapshot(snapshot)
        self._defect_screen.apply_runtime_snapshot(snapshot)
        self._diagnostics_screen.apply_runtime_snapshot(snapshot)

    def show_boxes(self) -> None:
        """Переключает рабочую область на список коробок."""

        self._show_screen(1, "boxes")

    def _register_work_screens(self) -> None:
        """Добавляет рабочие экраны в стек."""

        for screen in (
            self._packing_screen,
            self._boxes_screen,
            self._box_lookup_screen,
            self._verify_screen,
            self._defect_screen,
            self._settings_screen,
            self._diagnostics_screen,
        ):
            self._stack.addWidget(screen)

    def _build_layout(self) -> None:
        """Собирает боковую панель и рабочую область."""

        sidebar = self._build_sidebar()
        workspace = MainWorkspace()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(20, 18, 22, 20)
        workspace_layout.setSpacing(12)
        workspace_layout.addLayout(self._workspace_header())
        workspace_layout.addWidget(self._stack, stretch=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        layout.addWidget(sidebar)
        layout.addWidget(workspace, stretch=1)

    def _build_sidebar(self) -> MainSidebar:
        """Создает боковую навигационную панель."""

        sidebar = MainSidebar()
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(10)

        brand = QLabel("CZ Desktop")
        brand.setObjectName("mainBrand")
        section = QLabel("Рабочее место")
        section.setObjectName("mainSection")
        layout.addWidget(brand)
        layout.addWidget(section)
        layout.addWidget(self._session_panel)
        layout.addSpacing(6)
        for item in self._main_nav_items():
            layout.addWidget(item)
        layout.addStretch(1)
        utility = QLabel("Сервис")
        utility.setObjectName("mainSection")
        layout.addWidget(utility)
        for item in self._utility_nav_items():
            layout.addWidget(item)
        return sidebar

    def _workspace_header(self) -> QHBoxLayout:
        """Создает шапку рабочей области."""

        title = QLabel("Операционный центр")
        title.setObjectName("workspaceTitle")
        subtitle = QLabel("Сканер, упаковка, проверка и сервисные действия")
        subtitle.setObjectName("workspaceSubtitle")
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        accent = QFrame()
        accent.setObjectName("workspaceAccent")
        accent.setFixedSize(148, 6)

        header = QHBoxLayout()
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(accent)
        return header

    def _main_nav_items(self) -> list[NavItem]:
        """Создает основные пункты навигации."""

        return [
            self._nav_item("Упаковка", "Текущая коробка", VectorIconName.BOX, 0, "packing"),
            self._nav_item("Коробки", "Список и детали", VectorIconName.BOX, 1, "boxes"),
            self._nav_item("Поиск коробки", "SSCC или ID", VectorIconName.SCANNER, 2, "box_lookup"),
            self._nav_item("Проверка", "DataMatrix", VectorIconName.TOKEN, 3, "verify"),
            self._nav_item("Брак", "Отметка кодов", VectorIconName.WARNING, 4, "defect"),
        ]

    def _utility_nav_items(self) -> list[NavItem]:
        """Создает сервисные пункты навигации."""

        return [
            self._nav_item("Настройки", "Устройство", VectorIconName.SETTINGS, 5, "settings"),
            self._nav_item(
                "Диагностика",
                "Логи и статус",
                VectorIconName.DIAGNOSTICS,
                6,
                "diagnostics",
            ),
        ]

    def _nav_item(
        self,
        title: str,
        subtitle: str,
        icon_name: VectorIconName,
        index: int,
        screen_name: str,
    ) -> NavItem:
        """Создает пункт навигации и подключает переход."""

        item = NavItem(title, subtitle, icon_name, index, screen_name)
        item.clicked.connect(self._show_screen)
        self._nav_items.append(item)
        return item

    def _show_screen(self, index: int, screen_name: str) -> None:
        """Переключает рабочий экран и публикует выбранный сценарий."""

        if self._stack.currentIndex() != index:
            self._stack.setCurrentIndex(index)
            self._animate_stack()
        self._set_active_nav(screen_name)
        self.screen_changed.emit(screen_name)

    def _set_active_nav(self, screen_name: str) -> None:
        """Подсвечивает активный пункт навигации."""

        for item in self._nav_items:
            item.set_active(item.property("screen_name") == screen_name)

    def _animate_stack(self) -> None:
        """Запускает мягкую анимацию появления рабочего экрана."""

        self._stack_animation.stop()
        self._stack_animation.setStartValue(0.55)
        self._stack_animation.setEndValue(1.0)
        self._stack_animation.start()
