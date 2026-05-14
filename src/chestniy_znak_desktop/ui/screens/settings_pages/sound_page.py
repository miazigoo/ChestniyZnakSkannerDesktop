"""Страница настройки звуков."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from chestniy_znak_desktop.controllers.settings_controller import SettingsUiState


class SoundSettingsPage(QWidget):
    """Редактирует звуки событий и позволяет их прослушать."""

    back_requested = Signal()
    save_requested = Signal(bool, float, str, str, str, str)
    preview_requested = Signal(str)

    def __init__(self) -> None:
        """Создает форму звуковых настроек."""

        super().__init__()
        self._sound_enabled = QCheckBox("Звуки включены")
        self._sound_enabled.setChecked(True)
        self._sound_volume = QSlider(Qt.Orientation.Horizontal)
        self._sound_volume.setRange(0, 100)
        self._sound_volume.setValue(85)
        self._sound_ok = QComboBox()
        self._sound_warning = QComboBox()
        self._sound_error = QComboBox()
        self._sound_victory = QComboBox()
        self._save_button = QPushButton("Сохранить звуки")
        self._back_button = QPushButton("Назад к настройкам")
        self._save_button.clicked.connect(self._emit_save)
        self._back_button.clicked.connect(self.back_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Звук"))
        layout.addWidget(self._sound_enabled)
        layout.addWidget(QLabel("Громкость звуков"))
        layout.addWidget(self._sound_volume)
        layout.addLayout(self._sound_row("Звук успеха", self._sound_ok))
        layout.addLayout(self._sound_row("Звук предупреждения", self._sound_warning))
        layout.addLayout(self._sound_row("Звук ошибки", self._sound_error))
        layout.addLayout(self._sound_row("Звук закрытия коробки", self._sound_victory))
        layout.addWidget(self._save_button)
        layout.addWidget(self._back_button)
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

    def _sound_row(self, label: str, combo: QComboBox) -> QHBoxLayout:
        """Создает строку выбора и прослушивания звука."""

        preview_button = QPushButton("Прослушать")
        preview_button.clicked.connect(lambda: self.preview_requested.emit(combo.currentText()))
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(combo, stretch=1)
        row.addWidget(preview_button)
        return row

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
