"""
Виджет превью аватара в главном окне.
С рамкой, индикатором громкости и состояния.
Рисует через paintEvent — никаких margin.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PIL.ImageQt import ImageQt

from core.config import config
from core.effects import EffectManager, AvatarState
from core.sprite_manager import SpriteManager


class AvatarPreview(QWidget):
    """Превью аватара с рамкой и индикаторами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 350)
        self.setMaximumSize(450, 500)

        self.sprite_manager = SpriteManager()
        self.effect_manager = EffectManager()

        self.current_volume = 0.0
        self.is_talking = False

        self.fps = config.get("avatar", "fps")
        self._current_sprite = None

        self._setup_ui()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_frame)
        self.update_timer.setInterval(int(1000 / self.fps))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.title_label = QLabel("Превью аватара")
        self.title_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)

        # Область аватара — QWidget для кастомной отрисовки
        self.avatar_container = _AvatarCanvas()
        self.avatar_container.setMinimumHeight(250)
        layout.addWidget(self.avatar_container)

        # Индикатор громкости
        vol_layout = QVBoxLayout()
        vol_label = QLabel("Громкость:")
        vol_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        vol_layout.addWidget(vol_label)

        self.volume_bar = QProgressBar()
        self.volume_bar.setRange(0, 100)
        self.volume_bar.setValue(0)
        self.volume_bar.setTextVisible(False)
        self.volume_bar.setFixedHeight(6)
        self.volume_bar.setStyleSheet("""
            QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #a6e3a1; border-radius: 3px; }
        """)
        vol_layout.addWidget(self.volume_bar)
        layout.addLayout(vol_layout)

        self.state_label = QLabel("Состояние: Ожидание")
        self.state_label.setStyleSheet("color: #89b4fa; font-size: 11px;")
        layout.addWidget(self.state_label)

    def load_sprites_from_config(self):
        import os
        sprites = config.get("sprites")
        if sprites:
            for key, path in sprites.items():
                if path and os.path.exists(path):
                    self.sprite_manager.load_sprite(key, path)

    def set_talking(self, talking: bool):
        self.is_talking = talking
        self.effect_manager.set_talking(talking)

    def set_volume(self, volume: float):
        self.current_volume = volume
        self.effect_manager.set_volume(volume)

    def _update_frame(self):
        self.effect_manager.update(fps=self.fps)

        self.volume_bar.setValue(int(self.current_volume * 100))

        # Цвет полоски
        if self.current_volume > 0.6:
            self.volume_bar.setStyleSheet("""
                QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #f38ba8; border-radius: 3px; }
            """)
        elif self.current_volume > 0.3:
            self.volume_bar.setStyleSheet("""
                QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #f9e2af; border-radius: 3px; }
            """)
        else:
            self.volume_bar.setStyleSheet("""
                QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
                QProgressBar::chunk { background-color: #a6e3a1; border-radius: 3px; }
            """)

        # Состояние
        state = self.effect_manager.get_state()
        state_names = {
            AvatarState.IDLE: "Ожидание",
            AvatarState.TALKING: "Разговор",
            AvatarState.TALK_END: "Завершение",
            AvatarState.BLINK: "Моргание",
        }
        self.state_label.setText(f"Состояние: {state_names.get(state, 'Неизвестно')}")

        # Спрайт
        eyes = self.effect_manager.get_eyes_state()
        mouth = self.effect_manager.get_mouth_open_amount()

        sprite = self.sprite_manager.get_combined_sprite(
            eyes, mouth, size=(self.avatar_container.width() - 4, 240)
        )

        if sprite:
            qimage = ImageQt(sprite)
            pixmap = QPixmap.fromImage(qimage)
            self._current_sprite = pixmap
        else:
            self._current_sprite = None

        # Передаём эффекты на canvas
        lev_y = self.effect_manager.get_levitation_offset()
        shake_x, shake_y = self.effect_manager.get_shake_offset()
        self.avatar_container.set_transform(shake_x, lev_y + shake_y)

        self.avatar_container.set_sprite(self._current_sprite)
        self.avatar_container.update()

    def start(self):
        self.update_timer.start(int(1000 / self.fps))

    def stop(self):
        self.update_timer.stop()


class _AvatarCanvas(QWidget):
    """Canvas для отрисовки аватара с transform."""

    def __init__(self):
        super().__init__()
        self._sprite = None
        self._offset_x = 0.0
        self._offset_y = 0.0
        self.setStyleSheet(
            "background-color: #181825; border: 2px solid #45475a; border-radius: 8px;"
        )

    def set_sprite(self, pixmap):
        self._sprite = pixmap

    def set_transform(self, dx, dy):
        self._offset_x = dx
        self._offset_y = dy

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._sprite is None:
            painter.setPen(QColor(108, 112, 134))
            font = QFont("Arial", 13)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Загрузите спрайты"
            )
            return

        painter.translate(self._offset_x, self._offset_y)

        x = (self.width() - self._sprite.width()) // 2
        y = (self.height() - self._sprite.height()) // 2
        painter.drawPixmap(x, y, self._sprite)
