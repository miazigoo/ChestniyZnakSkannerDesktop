"""Главный рабочий экран desktop-клиента."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.i18n import tr
from chestniy_znak_desktop.runtime.state_models import RuntimeSnapshot
from chestniy_znak_desktop.ui.screens.auto_packing_screen import AutoPackingScreen
from chestniy_znak_desktop.ui.screens.box_lookup_screen import BoxLookupScreen
from chestniy_znak_desktop.ui.screens.boxes_screen import BoxesScreen
from chestniy_znak_desktop.ui.screens.defect_screen import DefectScreen
from chestniy_znak_desktop.ui.screens.diagnostics_screen import DiagnosticsScreen
from chestniy_znak_desktop.ui.screens.packing_screen import PackingScreen
from chestniy_znak_desktop.ui.screens.settings_screen import SettingsScreen
from chestniy_znak_desktop.ui.screens.verify_screen import VerifyScreen
from chestniy_znak_desktop.ui.i18n_widgets import retranslate_widget_tree
from chestniy_znak_desktop.ui.widgets.adaptive_scroll_area import AdaptiveScrollArea
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
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self._stack_effect = QGraphicsOpacityEffect(self._stack)
        self._stack.setGraphicsEffect(self._stack_effect)
        self._stack_animation = QPropertyAnimation(self._stack_effect, b"opacity", self)
        self._stack_animation.setDuration(180)
        self._stack_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_items: list[NavItem] = []
        self._workspace_title: QLabel | None = None
        self._workspace_subtitle: QLabel | None = None
        self._workplace_section: QLabel | None = None
        self._service_section: QLabel | None = None
        self._is_compact = False
        self._sidebar: MainSidebar | None = None
        self._root_layout: QHBoxLayout | None = None
        self._workspace_layout: QVBoxLayout | None = None
        self._session_panel = UserSessionPanel()
        self._packing_screen = PackingScreen()
        self._auto_packing_screen = AutoPackingScreen()
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
    def auto_packing_screen(self) -> AutoPackingScreen:
        """Возвращает экран автоупаковки для подключения контроллера."""

        return self._auto_packing_screen

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
        self._auto_packing_screen.apply_runtime_snapshot(snapshot)
        self._box_lookup_screen.apply_runtime_snapshot(snapshot)
        self._verify_screen.apply_runtime_snapshot(snapshot)
        self._defect_screen.apply_runtime_snapshot(snapshot)
        self._diagnostics_screen.apply_runtime_snapshot(snapshot)

    def retranslate(self) -> None:
        """Обновляет статические тексты рабочего экрана после смены языка."""

        retranslate_widget_tree(self)
        self._session_panel.retranslate()
        if self._workspace_title is not None:
            self._workspace_title.setText(tr("main.title"))
        if self._workspace_subtitle is not None:
            self._workspace_subtitle.setText(tr("main.subtitle"))
        if self._workplace_section is not None:
            self._workplace_section.setText(tr("main.workplace"))
        if self._service_section is not None:
            self._service_section.setText(tr("main.service"))
        for item, (title_key, subtitle_key) in zip(self._nav_items, self._nav_translation_keys()):
            item.set_texts(tr(title_key), tr(subtitle_key))

    def show_boxes(self) -> None:
        """Переключает рабочую область на список коробок."""

        self._show_screen(2, "boxes")

    def show_packing(self) -> None:
        """Переключает рабочую область на экран упаковки."""

        self._show_screen(0, "packing")

    def _register_work_screens(self) -> None:
        """Добавляет рабочие экраны в стек."""

        for screen in (
            self._packing_screen,
            self._auto_packing_screen,
            self._boxes_screen,
            self._box_lookup_screen,
            self._verify_screen,
            self._defect_screen,
            self._settings_screen,
            self._diagnostics_screen,
        ):
            wrapper = AdaptiveScrollArea(screen, f"{screen.objectName()}Scroll")
            self._stack.addWidget(wrapper)

    def _build_layout(self) -> None:
        """Собирает боковую панель и рабочую область."""

        sidebar = self._build_sidebar()
        workspace = MainWorkspace()
        workspace_layout = QVBoxLayout(workspace)
        self._workspace_layout = workspace_layout
        workspace_layout.setContentsMargins(20, 18, 22, 20)
        workspace_layout.setSpacing(12)
        workspace_layout.addLayout(self._workspace_header())
        workspace_layout.addWidget(self._stack, stretch=1)

        layout = QHBoxLayout(self)
        self._root_layout = layout
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)
        layout.addWidget(sidebar)
        layout.addWidget(workspace, stretch=1)
        self._apply_responsive_mode()

    def _build_sidebar(self) -> MainSidebar:
        """Создает боковую навигационную панель."""

        sidebar = MainSidebar()
        self._sidebar = sidebar
        shell_layout = QVBoxLayout(sidebar)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("mainSidebarScroll")
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("mainSidebarContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        brand = QLabel("CZ Desktop")
        brand.setObjectName("mainBrand")
        self._workplace_section = QLabel(tr("main.workplace"))
        self._workplace_section.setObjectName("mainSection")
        layout.addWidget(brand)
        layout.addWidget(self._workplace_section)
        layout.addWidget(self._session_panel)
        layout.addSpacing(6)
        for item in self._main_nav_items():
            layout.addWidget(item)
        layout.addStretch(1)
        self._service_section = QLabel(tr("main.service"))
        self._service_section.setObjectName("mainSection")
        layout.addWidget(self._service_section)
        for item in self._utility_nav_items():
            layout.addWidget(item)
        scroll_area.setWidget(content)
        shell_layout.addWidget(scroll_area)
        return sidebar

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Обновляет плотность интерфейса при изменении размера окна."""

        super().resizeEvent(event)
        self._apply_responsive_mode()

    def _apply_responsive_mode(self) -> None:
        """Подбирает отступы и ширину сайдбара под доступный размер."""

        is_compact = self.width() < 1060 or self.height() < 700
        if is_compact == self._is_compact:
            return
        self._is_compact = is_compact
        if self._sidebar is not None:
            self._sidebar.set_compact(is_compact)
        if self._root_layout is not None:
            margin = 8 if is_compact else 14
            spacing = 10 if is_compact else 14
            self._root_layout.setContentsMargins(margin, margin, margin, margin)
            self._root_layout.setSpacing(spacing)
        if self._workspace_layout is not None:
            if is_compact:
                self._workspace_layout.setContentsMargins(14, 12, 14, 14)
                self._workspace_layout.setSpacing(10)
            else:
                self._workspace_layout.setContentsMargins(20, 18, 22, 20)
                self._workspace_layout.setSpacing(12)

    def _workspace_header(self) -> QHBoxLayout:
        """Создает шапку рабочей области."""

        self._workspace_title = QLabel(tr("main.title"))
        self._workspace_title.setObjectName("workspaceTitle")
        self._workspace_subtitle = QLabel(tr("main.subtitle"))
        self._workspace_subtitle.setObjectName("workspaceSubtitle")
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(self._workspace_title)
        title_box.addWidget(self._workspace_subtitle)

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
            self._nav_item(
                tr("main.nav.packing"),
                tr("main.nav.packingHint"),
                VectorIconName.BOX,
                0,
                "packing",
            ),
            self._nav_item(
                tr("main.nav.autoPacking"),
                tr("main.nav.autoPackingHint"),
                VectorIconName.SCANNER,
                1,
                "auto_packing",
            ),
            self._nav_item(
                tr("main.nav.boxes"),
                tr("main.nav.boxesHint"),
                VectorIconName.BOX,
                2,
                "boxes",
            ),
            self._nav_item(
                tr("main.nav.lookup"),
                tr("main.nav.lookupHint"),
                VectorIconName.SCANNER,
                3,
                "box_lookup",
            ),
            self._nav_item(
                tr("main.nav.verify"),
                tr("main.nav.verifyHint"),
                VectorIconName.TOKEN,
                4,
                "verify",
            ),
            self._nav_item(
                tr("main.nav.defect"),
                tr("main.nav.defectHint"),
                VectorIconName.WARNING,
                5,
                "defect",
            ),
        ]

    @staticmethod
    def _nav_translation_keys() -> list[tuple[str, str]]:
        """Возвращает ключи переводов пунктов навигации в порядке их создания."""

        return [
            ("main.nav.packing", "main.nav.packingHint"),
            ("main.nav.autoPacking", "main.nav.autoPackingHint"),
            ("main.nav.boxes", "main.nav.boxesHint"),
            ("main.nav.lookup", "main.nav.lookupHint"),
            ("main.nav.verify", "main.nav.verifyHint"),
            ("main.nav.defect", "main.nav.defectHint"),
            ("main.nav.settings", "main.nav.settingsHint"),
            ("main.nav.diagnostics", "main.nav.diagnosticsHint"),
        ]

    def _utility_nav_items(self) -> list[NavItem]:
        """Создает сервисные пункты навигации."""

        return [
            self._nav_item(
                tr("main.nav.settings"),
                tr("main.nav.settingsHint"),
                VectorIconName.SETTINGS,
                6,
                "settings",
            ),
            self._nav_item(
                tr("main.nav.diagnostics"),
                tr("main.nav.diagnosticsHint"),
                VectorIconName.DIAGNOSTICS,
                7,
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
