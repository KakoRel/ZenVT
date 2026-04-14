"""
Главное окно приложения.
Слева: превью аватара + кнопка запуска
Справа: настройки (скролл, без вкладок)
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QScrollArea,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QSlider,
    QCheckBox, QFileDialog, QGroupBox, QFormLayout, QMessageBox,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.config import config
from core.audio_detector import AudioDetector
from ui.avatar_window import AvatarWindow
from ui.preview_widget import AvatarPreview


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self._setup_window()

        # Компоненты
        self.audio_detector = AudioDetector()
        self.avatar_window = AvatarWindow()
        self.avatar_window.load_sprites_from_config()

        # Связь аудио → аватар
        self.audio_detector.on_talk_start = lambda: (
            self.avatar_window.set_talking(True),
            self.preview.set_talking(True),
        )
        self.audio_detector.on_talk_end = lambda: (
            self.avatar_window.set_talking(False),
            self.preview.set_talking(False),
        )
        self.audio_detector.on_volume_change = lambda v: (
            self.avatar_window.set_volume(v),
            self.preview.set_volume(v),
        )

        self._setup_ui()
        self._setup_tray()
        self._apply_theme()

    def _setup_window(self):
        self.setWindowTitle("ZenVT - Studio")
        self.resize(1100, 750)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === ЛЕВАЯ ПАНЕЛЬ: Превью + Кнопка запуска ===
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        self.preview = AvatarPreview()
        self.preview.load_sprites_from_config()
        left_panel.addWidget(self.preview)

        # Кнопка запуска
        self.launch_btn = QPushButton("▶ Запустить аватар")
        self.launch_btn.setFixedHeight(50)
        self.launch_btn.clicked.connect(self._toggle_avatar)
        left_panel.addWidget(self.launch_btn)

        # Статус
        self.status_label = QLabel("Аватар: Остановлен")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        left_panel.addWidget(self.status_label)

        left_panel.addStretch()
        main_layout.addLayout(left_panel, stretch=1)

        # === ПРАВАЯ ПАНЕЛЬ: Настройки ===
        right_panel = self._create_settings_panel()
        main_layout.addLayout(right_panel, stretch=1)
        
    def _setup_tray(self):
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
        self.tray_icon = QSystemTrayIcon(self)
        
        # Устанавливаем стандартно-системную иконку, пока нет своей
        icon = QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("ZenVT")
        
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Показать настройки")
        show_action.triggered.connect(self.showNormal)
        
        self.tray_launch_action = tray_menu.addAction("Запустить аватар")
        self.tray_launch_action.triggered.connect(self._toggle_avatar)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
    def _on_tray_activated(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def _create_settings_panel(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)

        # Заголовок
        header = QLabel("Настройки")
        header.setStyleSheet("color: #cdd6f4; font-size: 18px; font-weight: bold; padding: 5px 0 15px 0;")
        layout.addWidget(header)

        # Скролл
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        # --- Группа: Аватар ---
        scroll_layout.addWidget(self._create_avatar_group())

        # --- Группа: Левитация ---
        scroll_layout.addWidget(self._create_levitation_group())

        # --- Группа: Аудио ---
        scroll_layout.addWidget(self._create_audio_group())

        # --- Группа: Эффекты разговора ---
        scroll_layout.addWidget(self._create_talking_group())

        # --- Группа: Эффекты ожидания ---
        scroll_layout.addWidget(self._create_idle_group())

        # --- Группа: OBS (Хромакей) ---
        scroll_layout.addWidget(self._create_obs_group())

        # --- Группа: Спрайты ---
        scroll_layout.addWidget(self._create_sprites_group())

        # Привязка динамического сохранения
        self._bind_settings()

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return layout

    def _create_group(self, title):
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
                margin-top: 8px;
                color: #cdd6f4;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #89b4fa;
            }
        """)
        return group

    def _create_avatar_group(self):
        group = self._create_group("Аватар")
        layout = QFormLayout()

        self.width_spin = self._spin(100, 1920, config.get("avatar", "width"))
        layout.addRow("Ширина:", self.width_spin)

        self.height_spin = self._spin(100, 1080, config.get("avatar", "height"))
        layout.addRow("Высота:", self.height_spin)

        self.fps_spin = self._spin(10, 120, config.get("avatar", "fps"))
        layout.addRow("FPS:", self.fps_spin)

        self.pos_x_spin = self._spin(0, 3840, config.get("avatar", "position_x"))
        layout.addRow("Позиция X:", self.pos_x_spin)

        self.pos_y_spin = self._spin(0, 2160, config.get("avatar", "position_y"))
        layout.addRow("Позиция Y:", self.pos_y_spin)
        
        self.always_on_top_check = QCheckBox("Поверх всех окон")
        self.always_on_top_check.setChecked(config.get("avatar", "always_on_top"))
        self.always_on_top_check.setToolTip("Уберите галочку, чтобы аватар ушел на задний план под игру (для захвата OBS).")
        layout.addRow(self.always_on_top_check)

        group.setLayout(layout)
        return group

    def _create_levitation_group(self):
        group = self._create_group("Левитация")
        layout = QFormLayout()

        self.lev_check = QCheckBox("Включить")
        self.lev_check.setChecked(config.get("levitation", "enabled"))
        layout.addRow(self.lev_check)

        self.lev_speed_spin = self._dspin(0.1, 10.0, 0.1, config.get("levitation", "speed"))
        layout.addRow("Скорость:", self.lev_speed_spin)

        self.lev_amp_spin = self._spin(1, 50, config.get("levitation", "amplitude"))
        layout.addRow("Амплитуда (px):", self.lev_amp_spin)

        group.setLayout(layout)
        return group

    def _create_audio_group(self):
        group = self._create_group("Аудио")
        layout = QFormLayout()

        self.device_combo = QComboBox()
        devices = self._get_audio_devices()
        current_dev = config.get("audio", "device_index")
        idx_to_select = 0
        for i, dev in enumerate(devices):
            self.device_combo.addItem(f"{dev['name']}")
            self.device_combo.setItemData(self.device_combo.count() - 1, dev['index'])
            if dev['index'] == current_dev:
                idx_to_select = i
                
        self.device_combo.setCurrentIndex(idx_to_select)
        layout.addRow("Микрофон:", self.device_combo)

        self.sens_slider = self._slider(1, 100, config.get("audio", "sensitivity"))
        self.sens_label = QLabel(str(config.get("audio", "sensitivity")))
        self.sens_slider.valueChanged.connect(lambda v: self.sens_label.setText(str(v)))
        sens_row = QWidget()
        sens_layout = QHBoxLayout(sens_row)
        sens_layout.setContentsMargins(0, 0, 0, 0)
        sens_layout.addWidget(self.sens_slider)
        sens_layout.addWidget(self.sens_label)
        layout.addRow("Чувствительность:", sens_row)

        self.silence_spin = self._dspin(0.1, 3.0, 0.1, config.get("audio", "silence_delay"))
        layout.addRow("Задержка тишины (с):", self.silence_spin)

        self.pitch_check = QCheckBox("Распознавание 'аааа'")
        self.pitch_check.setChecked(config.get("audio", "pitch_detection"))
        layout.addRow(self.pitch_check)

        group.setLayout(layout)
        return group

    def _create_talking_group(self):
        group = self._create_group("Эффект 'Говорит'")
        layout = QFormLayout()

        self.shake_check = QCheckBox("Дрожь")
        self.shake_check.setChecked(config.get("talking_effect", "shake_enabled"))
        layout.addRow(self.shake_check)

        self.shake_int_spin = self._spin(1, 20, config.get("talking_effect", "shake_intensity"))
        layout.addRow("Интенсивность:", self.shake_int_spin)

        self.shake_freq_spin = self._spin(1, 30, config.get("talking_effect", "shake_frequency"))
        layout.addRow("Частота (Hz):", self.shake_freq_spin)

        self.mouth_check = QCheckBox("Синхронизация рта")
        self.mouth_check.setChecked(config.get("talking_effect", "mouth_sync"))
        layout.addRow(self.mouth_check)

        group.setLayout(layout)
        return group

    def _create_idle_group(self):
        group = self._create_group("Эффект 'Не говорит'")
        layout = QFormLayout()

        self.trans_check = QCheckBox("Плавный переход")
        self.trans_check.setChecked(config.get("idle_effect", "transition_enabled"))
        layout.addRow(self.trans_check)

        self.trans_dur_spin = self._dspin(0.1, 2.0, 0.1, config.get("idle_effect", "transition_duration"))
        layout.addRow("Длительность (с):", self.trans_dur_spin)

        self.blink_check = QCheckBox("Моргание")
        self.blink_check.setChecked(config.get("idle_effect", "blink_enabled"))
        layout.addRow(self.blink_check)

        self.blink_int_spin = self._dspin(1.0, 10.0, 0.5, config.get("idle_effect", "blink_interval"))
        layout.addRow("Интервал (с):", self.blink_int_spin)

        self.blink_dur_spin = self._dspin(0.05, 0.5, 0.05, config.get("idle_effect", "blink_duration"))
        layout.addRow("Длительность (с):", self.blink_dur_spin)

        group.setLayout(layout)
        return group

    def _create_obs_group(self):
        group = self._create_group("Для OBS (Захват окна)")
        layout = QFormLayout()

        info = QLabel("Если в OBS вместо прозрачного фона черный,\nотключите прозрачность ниже и добавьте фильтр\n'Хромакей' (Зеленый цвет) в самом OBS.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addRow(info)

        self.trans_bg_check = QCheckBox("Использовать прозрачный фон")
        self.trans_bg_check.setChecked(config.get("obs", "background_transparency"))
        layout.addRow(self.trans_bg_check)

        group.setLayout(layout)
        return group

    def _create_sprites_group(self):
        group = self._create_group("Спрайты")
        layout = QVBoxLayout()

        info = QLabel("PNG с прозрачным фоном. Минимум 2: глаза × рот")
        info.setWordWrap(True)
        info.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(info)

        self.sprite_buttons = {}
        fields = [
            ("eyes_open_mouth_closed", "Глаза открыты, рот закрыт"),
            ("eyes_open_mouth_open", "Глаза открыты, рот открыт"),
            ("eyes_closed_mouth_closed", "Глаза закрыты, рот закрыт"),
            ("eyes_closed_mouth_open", "Глаза закрыты, рот открыт"),
        ]

        for key, label in fields:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(180)
            lbl.setStyleSheet("color: #cdd6f4;")
            row.addWidget(lbl)

            path_lbl = QLabel("Не выбран")
            path_lbl.setWordWrap(True)
            path_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
            row.addWidget(path_lbl)

            btn = QPushButton("...")
            btn.setFixedWidth(40)
            btn.clicked.connect(lambda _, k=key: self._select_sprite(k))
            row.addWidget(btn)

            layout.addLayout(row)
            self.sprite_buttons[key] = path_lbl

        group.setLayout(layout)
        return group

    # --- Helpers ---

    def _spin(self, min_v, max_v, val):
        s = QSpinBox()
        s.setRange(min_v, max_v)
        s.setValue(val)
        return s

    def _dspin(self, min_v, max_v, step, val):
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setSingleStep(step)
        s.setValue(val)
        return s

    def _slider(self, min_v, max_v, val):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(val)
        return s

    def _get_audio_devices(self):
        try:
            import sounddevice as sd
            devices = []
            seen_names = set()
            devices.append({"index": -1, "name": "По умолчанию"})
            
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    name = dev['name']
                    if name not in seen_names:
                        seen_names.add(name)
                        devices.append({"index": i, "name": name})
            return devices
        except Exception:
            return [{"index": -1, "name": "По умолчанию"}]

    def _select_sprite(self, key):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Спрайт: {key}", "", "PNG (*.png)"
        )
        if path:
            self.sprite_buttons[key].setText(path[-30:] if len(path) > 30 else path)
            self.sprite_buttons[key].setToolTip(path)
            config.set("sprites", key, path)
            self.preview.sprite_manager.load_sprite(key, path)
            self.avatar_window.sprite_manager.load_sprite(key, path)

    def _toggle_avatar(self):
        """Запуск/остановка аватара."""
        if self.avatar_window.is_running():
            self.avatar_window.stop()
            self.audio_detector.stop()
            self.preview.stop()
            self.launch_btn.setText("▶ Запустить аватар")
            self.launch_btn.setStyleSheet("")
            self.status_label.setText("Аватар: Остановлен")
            if hasattr(self, 'tray_launch_action'):
                self.tray_launch_action.setText("Запустить аватар")
        else:
            self.avatar_window.update_size()
            self.avatar_window.update_position()
            self.avatar_window.update_flags()
            self.avatar_window.start()
            self.audio_detector.start()
            self.preview.start()
            self.launch_btn.setText("⏹ Остановить")
            self.launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f38ba8;
                    color: #1e1e2e;
                    font-weight: bold;
                    border: none;
                    padding: 10px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #eba0ac;
                }
            """)
            self.status_label.setText("Аватар: Работает")
            if hasattr(self, 'tray_launch_action'):
                self.tray_launch_action.setText("Остановить аватар")

    def _bind_settings(self):
        # Аватар
        for w in [self.width_spin, self.height_spin, self.fps_spin, self.pos_x_spin, self.pos_y_spin]:
            w.valueChanged.connect(self._on_setting_changed)
        self.always_on_top_check.toggled.connect(self._on_setting_changed)
        
        # Левитация
        self.lev_check.toggled.connect(self._on_setting_changed)
        self.lev_speed_spin.valueChanged.connect(self._on_setting_changed)
        self.lev_amp_spin.valueChanged.connect(self._on_setting_changed)
        
        # Аудио
        self.device_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.sens_slider.valueChanged.connect(self._on_setting_changed)
        self.silence_spin.valueChanged.connect(self._on_setting_changed)
        self.pitch_check.toggled.connect(self._on_setting_changed)
        
        # Разговор
        self.shake_check.toggled.connect(self._on_setting_changed)
        self.shake_int_spin.valueChanged.connect(self._on_setting_changed)
        self.shake_freq_spin.valueChanged.connect(self._on_setting_changed)
        self.mouth_check.toggled.connect(self._on_setting_changed)
        
        # Ожидание
        self.trans_check.toggled.connect(self._on_setting_changed)
        self.trans_dur_spin.valueChanged.connect(self._on_setting_changed)
        self.blink_check.toggled.connect(self._on_setting_changed)
        self.blink_int_spin.valueChanged.connect(self._on_setting_changed)
        self.blink_dur_spin.valueChanged.connect(self._on_setting_changed)
        
        # OBS
        self.trans_bg_check.toggled.connect(self._on_setting_changed)

    def _on_setting_changed(self):
        old_device = config.get("audio", "device_index")

        config.set("avatar", "width", self.width_spin.value())
        config.set("avatar", "height", self.height_spin.value())
        config.set("avatar", "fps", self.fps_spin.value())
        config.set("avatar", "position_x", self.pos_x_spin.value())
        config.set("avatar", "position_y", self.pos_y_spin.value())
        config.set("avatar", "always_on_top", self.always_on_top_check.isChecked())

        config.set("levitation", "enabled", self.lev_check.isChecked())
        config.set("levitation", "speed", self.lev_speed_spin.value())
        config.set("levitation", "amplitude", self.lev_amp_spin.value())

        if self.device_combo.count() > 0:
            idx = self.device_combo.currentIndex()
            if idx >= 0:
                dev_idx = self.device_combo.itemData(idx)
                config.set("audio", "device_index", dev_idx if dev_idx is not None else -1)
                
        config.set("audio", "sensitivity", self.sens_slider.value())
        config.set("audio", "silence_delay", self.silence_spin.value())
        config.set("audio", "pitch_detection", self.pitch_check.isChecked())

        config.set("talking_effect", "shake_enabled", self.shake_check.isChecked())
        config.set("talking_effect", "shake_intensity", self.shake_int_spin.value())
        config.set("talking_effect", "shake_frequency", self.shake_freq_spin.value())
        config.set("talking_effect", "mouth_sync", self.mouth_check.isChecked())

        config.set("idle_effect", "transition_enabled", self.trans_check.isChecked())
        config.set("idle_effect", "transition_duration", self.trans_dur_spin.value())
        config.set("idle_effect", "blink_enabled", self.blink_check.isChecked())
        config.set("idle_effect", "blink_interval", self.blink_int_spin.value())
        config.set("idle_effect", "blink_duration", self.blink_dur_spin.value())
        
        config.set("obs", "background_transparency", self.trans_bg_check.isChecked())

        config.save()

        # Обновить превью
        self.preview.fps = config.get("avatar", "fps")
        self.preview.update_timer.setInterval(int(1000 / self.preview.fps))

        # Обновить аудио-детектор если он запущен
        if self.audio_detector._running:
            self.audio_detector.update_config()
            new_device = config.get("audio", "device_index")
            if old_device != new_device:
                self.audio_detector.stop()
                self.audio_detector.start()
                
        # Обновить аватар если запущен
        if self.avatar_window.is_running():
            self.avatar_window.update_size()
            self.avatar_window.update_position()
            self.avatar_window.update_flags()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QWidget { background-color: #1e1e2e; color: #cdd6f4; font-size: 13px; }
            QLabel { color: #cdd6f4; }
            QPushButton {
                background-color: #45475a; border: none; padding: 8px 16px;
                border-radius: 6px; color: #cdd6f4;
            }
            QPushButton:hover { background-color: #585b70; }
            QPushButton:pressed { background-color: #6c7086; }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #313244; border: 1px solid #45475a;
                padding: 4px 8px; border-radius: 4px; color: #cdd6f4;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {
                background-color: #45475a; width: 16px; border-radius: 2px;
            }
            QSlider::groove:horizontal {
                border: none; height: 6px; background: #313244; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #89b4fa; width: 14px; margin: -4px 0; border-radius: 7px;
            }
            QCheckBox::indicator {
                border: 2px solid #45475a; background: #313244;
                width: 16px; height: 16px; border-radius: 3px;
            }
            QCheckBox::indicator:checked { background: #89b4fa; }
            QScrollArea { border: none; }
            QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; }
            QMenu::item:selected { background-color: #313244; }
        """)

    def closeEvent(self, event):
        # Скрываем в трей, если не нажали "Выход"
        if not hasattr(self, '_is_quitting'):
            event.ignore()
            self.hide()
            from PyQt6.QtWidgets import QSystemTrayIcon
            self.tray_icon.showMessage(
                "ZenVT",
                "Программа свернута в трей.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            if self.avatar_window.is_running():
                self.avatar_window.stop()
            self.audio_detector.cleanup()
            config.save()
            super().closeEvent(event)

    def quit_app(self):
        self._is_quitting = True
        self.close()
