"""Страница настройки звуков."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState
from chestniy_znak_desktop.ui.screens.settings_pages.common import (
    apply_combo_popup_style,
    create_back_button,
    create_card,
    create_form_row,
    create_page_header,
)
from chestniy_znak_desktop.ui.widgets.vector_icon import VectorIconName


class SoundSettingsPage(QWidget):
    """Редактирует звуки событий и позволяет их прослушать."""

    back_requested = Signal()
    save_requested = Signal(bool, float, str, str, str, str)
    preview_requested = Signal(str)

    def __init__(self) -> None:
        """Создает форму звуковых настроек."""

        super().__init__()
        self.setObjectName("settingsPage")
        self._sound_enabled = QCheckBox("Звуки включены")
        self._sound_enabled.setObjectName("settingsCheckBox")
        self._sound_enabled.setChecked(True)
        self._sound_volume = QSlider(Qt.Orientation.Horizontal)
        self._sound_volume.setObjectName("settingsSlider")
        self._sound_volume.setRange(0, 100)
        self._sound_volume.setValue(85)
        self._sound_ok = QComboBox()
        self._sound_warning = QComboBox()
        self._sound_error = QComboBox()
        self._sound_victory = QComboBox()
        for combo in (
            self._sound_ok,
            self._sound_warning,
            self._sound_error,
            self._sound_victory,
        ):
            combo.setObjectName("settingsCombo")
            apply_combo_popup_style(combo)
        self._save_button = QPushButton("Сохранить")
        self._save_button.setObjectName("settingsPrimaryButton")
        self._back_button = create_back_button()
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        header = create_page_header(
            title="Звук",
            subtitle="Файлы звуковых событий, громкость и быстрый предпросмотр.",
            icon_name=VectorIconName.TOKEN,
            icon_color="#f3c969",
        )
        card, card_layout = create_card(
            title="События",
            subtitle="Звуки берутся из ресурсов приложения и применяются после сохранения.",
            icon_name=VectorIconName.LINK,
            icon_color="#66d2c7",
        )
        card_layout.addWidget(self._sound_enabled)
        card_layout.addWidget(create_form_row("Громкость", self._sound_volume))
        card_layout.addWidget(self._sound_row("Успех", self._sound_ok))
        card_layout.addWidget(self._sound_row("Предупреждение", self._sound_warning))
        card_layout.addWidget(self._sound_row("Ошибка", self._sound_error))
        card_layout.addWidget(self._sound_row("Закрытие коробки", self._sound_victory))
        actions = QHBoxLayout()
        actions.addWidget(self._save_button)
        actions.addWidget(self._back_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(18)
        layout.addWidget(header)
        layout.addWidget(card)
        layout.addStretch(1)

    def apply_state(self, state: SettingsUiState) -> None:
        """Заполняет форму сохраненными звуковыми настройками."""

        self._sound_enabled.setChecked(state.sound_enabled)
        self._sound_volume.setValue(int(state.sound_volume * 100))
        self._apply_sound_combo(self._sound_ok, state.available_sound_files, state.sound_ok_file)
        self._apply_sound_combo(
            self._sound_warning,
            state.available_sound_files,
            state.sound_warning_file,
        )
        self._apply_sound_combo(
            self._sound_error,
            state.available_sound_files,
            state.sound_error_file,
        )
        self._apply_sound_combo(
            self._sound_victory,
            state.available_sound_files,
            state.sound_victory_file,
        )

    def values(self) -> tuple[bool, float, str, str, str, str]:
        """Возвращает выбранные звуковые настройки."""

        return (
            self._sound_enabled.isChecked(),
            self._sound_volume.value() / 100,
            self._sound_ok.currentText(),
            self._sound_warning.currentText(),
            self._sound_error.currentText(),
            self._sound_victory.currentText(),
        )

    def _sound_row(self, label: str, combo: QComboBox) -> QFrame:
        """Создает строку выбора и прослушивания звука."""

        preview_button = QPushButton("Прослушать")
        preview_button.setObjectName("settingsSecondaryButton")
        preview_button.clicked.connect(lambda: self.preview_requested.emit(combo.currentText()))
        picker = QFrame()
        picker.setObjectName("settingsInlinePicker")
        picker_layout = QHBoxLayout(picker)
        picker_layout.setContentsMargins(0, 0, 0, 0)
        picker_layout.setSpacing(10)
        picker_layout.addWidget(combo, 1)
        picker_layout.addWidget(preview_button)
        return create_form_row(label, picker)

    def _emit_save(self) -> None:
        """Публикует запрос сохранения звуков."""

        enabled, volume, ok_file, warning_file, error_file, victory_file = self.values()
        self.save_requested.emit(
            enabled,
            volume,
            ok_file,
            warning_file,
            error_file,
            victory_file,
        )

    @staticmethod
    def _apply_sound_combo(combo: QComboBox, files: list[str], selected_file: str) -> None:
        """Заполняет combo доступными файлами звуков."""

        combo.blockSignals(True)
        combo.clear()
        combo.addItems(files)
        index = combo.findText(selected_file)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)
